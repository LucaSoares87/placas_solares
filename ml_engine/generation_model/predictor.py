from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class GenerationInput:
    uc_code: str
    kwp_estimated: float
    latitude: float
    longitude: float
    irradiance_wm2: Sequence[float]
    temperature_c: Sequence[float]
    performance_ratio: float = 0.78
    thermal_loss_factor: float = 0.004
    reference_temperature_c: float = 25.0


@dataclass(frozen=True)
class GenerationResult:
    uc_code: str
    hourly_generation_kw: list[float]
    total_generation_kwh: float
    peak_generation_kw: float
    confidence: float


class SolarGenerationPredictor:
    def predict_hourly_generation(self, data: GenerationInput) -> GenerationResult:
        self._validate(data)

        irradiance = np.array(data.irradiance_wm2, dtype=float)
        temperature = np.array(data.temperature_c, dtype=float)

        normalized_irradiance = np.clip(irradiance / 1000.0, 0.0, None)
        thermal_adjustment = 1.0 - data.thermal_loss_factor * (
            temperature - data.reference_temperature_c
        )
        thermal_adjustment = np.clip(thermal_adjustment, 0.70, 1.05)

        generation_kw = (
            data.kwp_estimated
            * normalized_irradiance
            * data.performance_ratio
            * thermal_adjustment
        )

        generation_kw = np.clip(generation_kw, 0.0, data.kwp_estimated)

        confidence = self._estimate_confidence(
            kwp_estimated=data.kwp_estimated,
            irradiance=irradiance,
            temperature=temperature,
        )

        result = GenerationResult(
            uc_code=data.uc_code,
            hourly_generation_kw=[round(float(value), 4) for value in generation_kw],
            total_generation_kwh=round(float(generation_kw.sum()), 4),
            peak_generation_kw=round(float(generation_kw.max(initial=0.0)), 4),
            confidence=confidence,
        )

        logger.info(
            "generation.predicted",
            uc_code=data.uc_code,
            total_generation_kwh=result.total_generation_kwh,
            peak_generation_kw=result.peak_generation_kw,
            confidence=result.confidence,
        )

        return result

    def predict_dataframe(
        self,
        uc_code: str,
        kwp_estimated: float,
        weather_frame: pd.DataFrame,
        latitude: float,
        longitude: float,
    ) -> GenerationResult:
        required_columns = {"irradiance_wm2", "temperature_c"}
        missing = required_columns - set(weather_frame.columns)

        if missing:
            raise ValueError(f"Weather dataframe missing columns: {sorted(missing)}")

        data = GenerationInput(
            uc_code=uc_code,
            kwp_estimated=kwp_estimated,
            latitude=latitude,
            longitude=longitude,
            irradiance_wm2=weather_frame["irradiance_wm2"].tolist(),
            temperature_c=weather_frame["temperature_c"].tolist(),
        )

        return self.predict_hourly_generation(data)

    def _validate(self, data: GenerationInput) -> None:
        if not data.uc_code:
            raise ValueError("uc_code is required")

        if data.kwp_estimated <= 0:
            raise ValueError("kwp_estimated must be greater than zero")

        if len(data.irradiance_wm2) != len(data.temperature_c):
            raise ValueError("irradiance_wm2 and temperature_c must have the same length")

        if not data.irradiance_wm2:
            raise ValueError("irradiance_wm2 cannot be empty")

        if not 0 < data.performance_ratio <= 1:
            raise ValueError("performance_ratio must be between 0 and 1")

    def _estimate_confidence(
        self,
        kwp_estimated: float,
        irradiance: np.ndarray,
        temperature: np.ndarray,
    ) -> float:
        confidence = 0.85

        if kwp_estimated <= 0:
            confidence -= 0.30

        if len(irradiance) < 12:
            confidence -= 0.15

        if np.isnan(irradiance).any() or np.isnan(temperature).any():
            confidence -= 0.25

        if np.nanmax(irradiance) <= 0:
            confidence -= 0.30

        return round(float(np.clip(confidence, 0.0, 1.0)), 4)