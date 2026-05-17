import structlog
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ml_engine.calibration.kwp_calibrator import KWpCalibrator, CalibrationSample
from ml_engine.calibration.loss_calibrator import LossCalibrator, LossSample
from ml_engine.continuous_learning.feedback_collector import (
    FeedbackCollector,
    FeedbackRecord,
    FeedbackSummary,
)

logger = structlog.get_logger(__name__)


@dataclass
class UpdateCycle:
    transformer_id: str
    executed_at: datetime
    kwp_factor_old: float
    kwp_factor_new: float
    loss_factor_old: float
    loss_factor_new: float
    samples_used: int
    mean_kwp_error_pct: float
    mean_consumo_error_pct: float
    converged: bool
    notes: list[str] = field(default_factory=list)


class ModelUpdater:
    """
    Coordena o ciclo completo de aprendizado contínuo por transformador:

    1. Recebe feedback de UCs telemedidas
    2. Atualiza fator kWp via KWpCalibrator
    3. Atualiza fator de perdas via LossCalibrator
    4. Registra histórico do ciclo de atualização
    5. Avalia convergência do sistema
    """

    def __init__(
        self,
        kwp_calibrator: KWpCalibrator,
        loss_calibrator: LossCalibrator,
        feedback_collector: FeedbackCollector,
    ):
        self._kwp_calibrator = kwp_calibrator
        self._loss_calibrator = loss_calibrator
        self._feedback = feedback_collector
        self._cycles: list[UpdateCycle] = []

    def run_update_cycle(
        self,
        transformer_id: str,
        energy_injected_kwh: Optional[float] = None,
        energy_measured_kwh: Optional[float] = None,
    ) -> Optional[UpdateCycle]:
        logger.info(
            "model_updater.cycle_start",
            transformer_id=transformer_id,
        )

        records = self._feedback.get_by_transformer(transformer_id)
        if not records:
            logger.warning(
                "model_updater.no_feedback",
                transformer_id=transformer_id,
            )
            return None

        self._feed_kwp_calibrator(transformer_id, records)

        if energy_injected_kwh and energy_measured_kwh:
            self._loss_calibrator.add_sample(
                LossSample(
                    transformer_id=transformer_id,
                    energy_injected_kwh=energy_injected_kwh,
                    energy_measured_kwh=energy_measured_kwh,
                )
            )

        old_kwp = self._kwp_calibrator.current_factor
        old_loss = self._loss_calibrator.current_loss_factor

        kwp_result = self._kwp_calibrator.calibrate(transformer_id)
        loss_result = self._loss_calibrator.calibrate(transformer_id)

        summary = self._feedback.summarize(transformer_id)

        cycle = UpdateCycle(
            transformer_id=transformer_id,
            executed_at=datetime.utcnow(),
            kwp_factor_old=old_kwp,
            kwp_factor_new=kwp_result.new_factor if kwp_result else old_kwp,
            loss_factor_old=old_loss,
            loss_factor_new=loss_result.new_loss_factor if loss_result else old_loss,
            samples_used=len(records),
            mean_kwp_error_pct=summary.mean_kwp_error_pct if summary else 0.0,
            mean_consumo_error_pct=summary.mean_consumo_error_pct if summary else 0.0,
            converged=kwp_result.converged if kwp_result else False,
            notes=self._build_notes(kwp_result, loss_result, summary),
        )

        self._cycles.append(cycle)

        logger.info(
            "model_updater.cycle_done",
            transformer_id=transformer_id,
            kwp_old=cycle.kwp_factor_old,
            kwp_new=cycle.kwp_factor_new,
            converged=cycle.converged,
        )

        return cycle

    def _feed_kwp_calibrator(
        self, transformer_id: str, records: list[FeedbackRecord]
    ) -> None:
        for r in records:
            if r.kwp_real and r.area_m2 > 0:
                self._kwp_calibrator.add_sample(
                    CalibrationSample(
                        transformer_id=transformer_id,
                        uc_code=r.uc_code,
                        area_m2=r.area_m2,
                        kwp_estimated=r.kwp_estimated,
                        kwp_real=r.kwp_real,
                    )
                )

    def _build_notes(self, kwp_result, loss_result, summary) -> list[str]:
        notes = []
        if kwp_result and kwp_result.converged:
            notes.append("kWp convergido dentro de ±10%")
        elif kwp_result:
            notes.append(
                f"kWp ainda divergindo: {kwp_result.mean_error_pct:.1f}%"
            )
        if loss_result:
            notes.append(
                f"Perdas técnicas atualizadas: {loss_result.new_loss_factor:.3f}"
            )
        if summary and summary.mean_consumo_error_pct > 20:
            notes.append("Erro de consumo elevado — revisar perfil de UC")
        return notes

    def get_cycles(self, transformer_id: Optional[str] = None) -> list[UpdateCycle]:
        if transformer_id:
            return [c for c in self._cycles if c.transformer_id == transformer_id]
        return list(self._cycles)

    @property
    def current_kwp_factor(self) -> float:
        return self._kwp_calibrator.current_factor

    @property
    def current_loss_factor(self) -> float:
        return self._loss_calibrator.current_loss_factor
