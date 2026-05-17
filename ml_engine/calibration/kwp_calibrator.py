import structlog
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

logger = structlog.get_logger(__name__)

DEFAULT_FACTOR = 0.15
MIN_FACTOR = 0.08
MAX_FACTOR = 0.25
MIN_SAMPLES = 3
LEARNING_RATE = 0.15


@dataclass
class CalibrationSample:
    transformer_id: str
    uc_code: str
    area_m2: float
    kwp_estimated: float
    kwp_real: float
    region: Optional[str] = None
    cluster_id: Optional[str] = None


@dataclass
class CalibrationResult:
    transformer_id: str
    old_factor: float
    new_factor: float
    delta: float
    samples_used: int
    mean_error_pct: float
    converged: bool
    region: Optional[str] = None


class KWpCalibrator:
    """
    Atualiza o fator de conversão área→kWp por transformador/região/cluster
    utilizando medições reais como ground truth.

    Estratégia:
        fator_novo = fator_atual + lr * (kWp_real/área - fator_atual)

    Atualização online com média ponderada dos resíduos.
    Garante convergência gradual sem saltos bruscos no fator.
    """

    def __init__(
        self,
        current_factor: float = DEFAULT_FACTOR,
        learning_rate: float = LEARNING_RATE,
    ):
        self._factor = current_factor
        self._lr = learning_rate
        self._history: list[CalibrationSample] = []

    def add_sample(self, sample: CalibrationSample) -> None:
        if sample.area_m2 <= 0 or sample.kwp_real <= 0:
            logger.warning(
                "kwp_calibrator.invalid_sample",
                uc_code=sample.uc_code,
                area_m2=sample.area_m2,
                kwp_real=sample.kwp_real,
            )
            return
        self._history.append(sample)
        logger.debug(
            "kwp_calibrator.sample_added",
            uc_code=sample.uc_code,
            kwp_real=sample.kwp_real,
        )

    def calibrate(self, transformer_id: str) -> Optional[CalibrationResult]:
        samples = [
            s for s in self._history if s.transformer_id == transformer_id
        ]

        if len(samples) < MIN_SAMPLES:
            logger.info(
                "kwp_calibrator.insufficient_samples",
                transformer_id=transformer_id,
                available=len(samples),
                required=MIN_SAMPLES,
            )
            return None

        real_factors = [s.kwp_real / s.area_m2 for s in samples]
        target_factor = float(np.mean(real_factors))

        old_factor = self._factor
        raw_new = old_factor + self._lr * (target_factor - old_factor)
        new_factor = float(np.clip(raw_new, MIN_FACTOR, MAX_FACTOR))

        errors = [
            abs(s.kwp_estimated - s.kwp_real) / s.kwp_real * 100
            for s in samples
            if s.kwp_real > 0
        ]
        mean_error_pct = float(np.mean(errors)) if errors else 0.0
        converged = mean_error_pct <= 10.0

        self._factor = new_factor

        result = CalibrationResult(
            transformer_id=transformer_id,
            old_factor=round(old_factor, 6),
            new_factor=round(new_factor, 6),
            delta=round(new_factor - old_factor, 6),
            samples_used=len(samples),
            mean_error_pct=round(mean_error_pct, 2),
            converged=converged,
            region=samples[0].region if samples else None,
        )

        logger.info(
            "kwp_calibrator.calibrated",
            transformer_id=transformer_id,
            old_factor=result.old_factor,
            new_factor=result.new_factor,
            mean_error_pct=result.mean_error_pct,
            converged=converged,
        )

        return result

    def calibrate_batch(
        self, transformer_ids: list[str]
    ) -> list[CalibrationResult]:
        results = []
        for tid in transformer_ids:
            result = self.calibrate(tid)
            if result:
                results.append(result)
        return results

    @property
    def current_factor(self) -> float:
        return self._factor

    def reset_history(self, transformer_id: Optional[str] = None) -> None:
        if transformer_id:
            self._history = [
                s for s in self._history
                if s.transformer_id != transformer_id
            ]
        else:
            self._history.clear()
        logger.info(
            "kwp_calibrator.history_reset",
            transformer_id=transformer_id or "all",
        )
