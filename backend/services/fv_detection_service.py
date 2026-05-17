import structlog
from typing import Optional

import numpy as np

from ml_engine.fv_detection import (
    FVDetector,
    SegmentationProcessor,
    PixelToAreaConverter,
    KWpEstimator,
)
from ml_engine.fv_detection.pixel_to_area import GeoReferenceParams
from backend.schemas.fv_detection import (
    FVDetectionRequest,
    FVDetectionResponse,
    DetectedPanelOutput,
    GeoReferenceInput,
    InjectionStatus,
    OperationalScore,
)
from backend.core.config import settings

logger = structlog.get_logger(__name__)


class FVDetectionService:
    """
    Orquestra o pipeline completo de detecção fotovoltaica:
    imagem → YOLO → segmentação → pixel→m² → kWp → resposta estruturada.
    """

    def __init__(self):
        self._detector = FVDetector(
            model_path=settings.YOLO_MODEL_PATH,
            confidence_threshold=settings.YOLO_CONFIDENCE_THRESHOLD,
        )
        self._segmentation = SegmentationProcessor()

    def run(
        self,
        request: FVDetectionRequest,
        image: np.ndarray,
        transformer_kwp_factor: Optional[float] = None,
        cluster_kwp_factor: Optional[float] = None,
    ) -> FVDetectionResponse:
        logger.info(
            "fv_detection_service.start",
            uc_code=request.uc_code,
            transformer_id=request.transformer_id,
        )

        detection_result = self._detector.detect(image)

        if not detection_result.has_fv:
            return self._empty_response(request, detection_result.model_version)

        panels = self._segmentation.process(detection_result.detections)

        geo_params = self._build_geo_params(request.geo_reference)
        converter = PixelToAreaConverter(geo_params)

        kwp_estimator = KWpEstimator(
            regional_factor=request.regional_kwp_factor,
            transformer_factor=transformer_kwp_factor,
            cluster_factor=cluster_kwp_factor,
        )

        panel_outputs: list[DetectedPanelOutput] = []
        total_area_m2 = 0.0
        total_kwp_raw = 0.0
        total_kwp_adjusted = 0.0

        for i, panel in enumerate(panels):
            area_m2 = converter.convert(panel.area_pixels)
            kwp_result = kwp_estimator.estimate(area_m2, panel.confidence)

            total_area_m2 += area_m2
            total_kwp_raw += kwp_result.kwp_estimated
            total_kwp_adjusted += kwp_result.kwp_adjusted

            panel_outputs.append(
                DetectedPanelOutput(
                    panel_index=i,
                    area_pixels=round(panel.area_pixels, 2),
                    area_m2=round(area_m2, 4),
                    confidence=panel.confidence,
                    centroid_x=round(panel.centroid_x, 2),
                    centroid_y=round(panel.centroid_y, 2),
                )
            )

        kwp_result_final = kwp_estimator.estimate(
            total_area_m2, detection_result.confidence
        )

        score = self._calculate_operational_score(
            detection_result.confidence, total_area_m2, len(panels)
        )

        response = FVDetectionResponse(
            uc_code=request.uc_code,
            transformer_id=request.transformer_id,
            latitude=request.latitude,
            longitude=request.longitude,
            has_fv=True,
            total_panels=len(panels),
            total_area_m2=round(total_area_m2, 4),
            kwp_estimated=kwp_result_final.kwp_estimated,
            kwp_adjusted=kwp_result_final.kwp_adjusted,
            kwp_factor_used=kwp_result_final.factor_used,
            kwp_factor_source=kwp_result_final.factor_source,
            detection_confidence=detection_result.confidence,
            panels=panel_outputs,
            model_version=detection_result.model_version,
            status=InjectionStatus.UNKNOWN,
            score_operacional=score,
        )

        logger.info(
            "fv_detection_service.done",
            uc_code=request.uc_code,
            has_fv=True,
            panels=len(panels),
            kwp_adjusted=kwp_result_final.kwp_adjusted,
            score=score,
        )

        return response

    def _empty_response(
        self, request: FVDetectionRequest, model_version: str
    ) -> FVDetectionResponse:
        return FVDetectionResponse(
            uc_code=request.uc_code,
            transformer_id=request.transformer_id,
            latitude=request.latitude,
            longitude=request.longitude,
            has_fv=False,
            total_panels=0,
            total_area_m2=0.0,
            kwp_estimated=0.0,
            kwp_adjusted=0.0,
            kwp_factor_used=0.0,
            kwp_factor_source="none",
            detection_confidence=0.0,
            panels=[],
            model_version=model_version,
            status=InjectionStatus.CONSUMING,
            score_operacional=OperationalScore.LOW_RISK,
        )

    def _build_geo_params(
        self, geo_input: Optional[GeoReferenceInput]
    ) -> GeoReferenceParams:
        if geo_input is None:
            return GeoReferenceParams()
        return GeoReferenceParams(
            gsd_m_per_pixel=geo_input.gsd_m_per_pixel,
            altitude_m=geo_input.altitude_m,
            focal_length_mm=geo_input.focal_length_mm,
            sensor_width_mm=geo_input.sensor_width_mm,
            image_width_px=geo_input.image_width_px,
            perspective_correction=geo_input.perspective_correction,
            distortion_correction=geo_input.distortion_correction,
        )

    def _calculate_operational_score(
        self,
        confidence: float,
        area_m2: float,
        panel_count: int,
    ) -> OperationalScore:
        if confidence >= 0.85 and area_m2 > 5.0:
            return OperationalScore.LOW_RISK
        if confidence >= 0.65:
            return OperationalScore.MEDIUM_RISK
        if confidence >= 0.45:
            return OperationalScore.HIGH_RISK
        return OperationalScore.INSPECTION_PRIORITY
