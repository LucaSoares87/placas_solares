from dataclasses import dataclass
from typing import Any

import structlog

from ml_engine.generation_model.predictor import (
    GenerationInput,
    SolarGenerationPredictor,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class InferenceRequest:
    uc_code: str
    transformer_id: str
    latitude: float
    longitude: float
    area_m2: float
    consumption_estimated_kw: float
    irradiance_wm2: list[float]
    temperature_c: list[float]
    detection_confidence: float = 0.80
    kwp_factor: float = 0.18


@dataclass(frozen=True)
class InferenceResult:
    uc_code: str
    transformer_id: str
    has_fv: bool
    area_m2: float
    kwp_estimated: float
    generation_kw: float
    consumption_estimated_kw: float
    injection_kw_range: tuple[float, float]
    status: str
    confidence: float
    score_operacional: str
    details: dict[str, Any]


class EnergyInferencePipeline:
    def __init__(
        self,
        generation_predictor: SolarGenerationPredictor | None = None,
    ) -> None:
        self._generation_predictor = generation_predictor or SolarGenerationPredictor()

    def run(self, request: InferenceRequest) -> InferenceResult:
        self._validate(request)

        kwp_estimated = self._estimate_kwp(
            area_m2=request.area_m2,
            kwp_factor=request.kwp_factor,
        )

        generation = self._generation_predictor.predict_hourly_generation(
            GenerationInput(
                uc_code=request.uc_code,
                kwp_estimated=kwp_estimated,
                latitude=request.latitude,
                longitude=request.longitude,
                irradiance_wm2=request.irradiance_wm2,
                temperature_c=request.temperature_c,
            )
        )

        generation_kw = generation.peak_generation_kw
        balance_kw = generation_kw - request.consumption_estimated_kw

        injection_range = self._estimate_injection_range(balance_kw)
        status = self._classify_behavior(balance_kw)
        confidence = self._combine_confidence(
            detection_confidence=request.detection_confidence,
            generation_confidence=generation.confidence,
            area_m2=request.area_m2,
        )
        score = self._classify_operational_score(
            confidence=confidence,
            status=status,
            injection_upper_kw=injection_range[1],
        )

        result = InferenceResult(
            uc_code=request.uc_code,
            transformer_id=request.transformer_id,
            has_fv=request.area_m2 > 0,
            area_m2=round(request.area_m2, 4),
            kwp_estimated=round(kwp_estimated, 4),
            generation_kw=round(generation_kw, 4),
            consumption_estimated_kw=round(request.consumption_estimated_kw, 4),
            injection_kw_range=(
                round(injection_range[0], 4),
                round(injection_range[1], 4),
            ),
            status=status,
            confidence=confidence,
            score_operacional=score,
            details={
                "total_generation_kwh": generation.total_generation_kwh,
                "peak_generation_kw": generation.peak_generation_kw,
                "hourly_generation_kw": generation.hourly_generation_kw,
            },
        )

        logger.info(
            "inference.completed",
            uc_code=result.uc_code,
            transformer_id=result.transformer_id,
            status=result.status,
            confidence=result.confidence,
            score_operacional=result.score_operacional,
        )

        return result

    def _estimate_kwp(self, area_m2: float, kwp_factor: float) -> float:
        return max(area_m2 * kwp_factor, 0.0)

    def _estimate_injection_range(self, balance_kw: float) -> tuple[float, float]:
        if balance_kw <= 0:
            return (0.0, 0.0)

        lower = balance_kw * 0.80
        upper = balance_kw * 1.20
        return (lower, upper)

    def _classify_behavior(self, balance_kw: float) -> str:
        if balance_kw > 0.30:
            return "injetando"

        if balance_kw < -0.30:
            return "consumindo"

        return "equilibrado"

    def _combine_confidence(
        self,
        detection_confidence: float,
        generation_confidence: float,
        area_m2: float,
    ) -> float:
        area_confidence = 0.90 if area_m2 > 5 else 0.60

        confidence = (
            0.45 * detection_confidence
            + 0.35 * generation_confidence
            + 0.20 * area_confidence
        )

        return round(max(0.0, min(confidence, 1.0)), 4)

    def _classify_operational_score(
        self,
        confidence: float,
        status: str,
        injection_upper_kw: float,
    ) -> str:
        if confidence < 0.45:
            return "alto_risco"

        if status == "injetando" and injection_upper_kw >= 3.0:
            return "medio_risco"

        return "baixo_risco"

    def _validate(self, request: InferenceRequest) -> None:
        if not request.uc_code:
            raise ValueError("uc_code is required")

        if not request.transformer_id:
            raise ValueError("transformer_id is required")

        if request.area_m2 < 0:
            raise ValueError("area_m2 cannot be negative")

        if request.consumption_estimated_kw < 0:
            raise ValueError("consumption_estimated_kw cannot be negative")

        if request.kwp_factor <= 0:
            raise ValueError("kwp_factor must be greater than zero")

        if not request.irradiance_wm2:
            raise ValueError("irradiance_wm2 cannot be empty")

        if len(request.irradiance_wm2) != len(request.temperature_c):
            raise ValueError("irradiance_wm2 and temperature_c must have the same length")