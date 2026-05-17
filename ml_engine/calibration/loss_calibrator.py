import structlog
from dataclasses import dataclass
from typing import Optional
import numpy as np

logger = structlog.get_logger(__name__)

DEFAULT_LOSS_FACTOR = 0.05
MIN_LOSS_FACTOR = 0.01
MAX_LOSS_FACTOR = 0.25
MIN_SAMPLES = 3


@dataclass
class LossSample:
    transformer_id: str
    energy_injected_kwh: float
    energy_measured_kwh: float
    period_hours: int = 1


@dataclass
class LossCalibrationResult:
    transformer_id: str
    old_loss_factor: float
    new_loss_factor: float
    delta: float
    samples_used: int
    mean_residual_pct: float


class LossCalibrator:
    """
    Calibra o fator de perdas técnicas por transformador.

    Compara energia injetada estimada com energia efetivamente medida
    no transformador para extrair o fator real de perdas técnicas.

    perda_estimada = (injetado - medido) / injetado
    fator_novo = média_ponderada(perdas_estimadas)
    """

    def __init__(self, current_loss_factor: float = DEFAULT_LOSS_FACTOR):
        self._factor = current_loss_factor
        self._samples: list[LossSample] = []

    def add_sample(self, sample: LossSample) -> None:
        if sample.energy_injected_kwh <= 0:
            logger.warning(
                "loss_calibrator.invalid_sample",
                transformer_id=sample.transformer_id,
            )
            return
        self._samples.append(sample)

    def calibrate(self, transformer_id: str) -> Optional[LossCalibrationResult]:
        samples = [
            s for s in self._samples if s.transformer_id == transformer_id
        ]

        if len(samples) < MIN_SAMPLES:
            logger.info(
                "loss_calibrator.insufficient_samples",
                transformer_id=transformer_id,
                available=len(samples),
            )
            return None

        loss_factors = []
        for s in samples:
            if s.energy_injected_kwh > 0:
                loss = (
                    s.energy_injected_kwh - s.energy_measured_kwh
                ) / s.energy_injected_kwh
                loss_factors.append(max(0.0, loss))

        if not loss_factors:
            return None

        new_factor_raw = float(np.mean(loss_factors))
        new_factor = float(np.clip(new_factor_raw, MIN_LOSS_FACTOR, MAX_LOSS_FACTOR))

        residuals = [
            abs(lf - new_factor) / new_factor * 100 if new_factor > 0 else 0.0
            for lf in loss_factors
        ]
        mean_residual_pct = float(np.mean(residuals))

        old_factor = self._factor
        self._factor = new_factor

        result = LossCalibrationResult(
            transformer_id=transformer_id,
            old_loss_factor=round(old_factor, 6),
            new_loss_factor=round(new_factor, 6),
            delta=round(new_factor - old_factor, 6),
            samples_used=len(samples),
            mean_residual_pct=round(mean_residual_pct, 2),
        )

        logger.info(
            "loss_calibrator.calibrated",
            transformer_id=transformer_id,
            old_factor=old_factor,
            new_factor=new_factor,
        )

        return result

    @property
    def current_loss_factor(self) -> float:
        return self._factor
