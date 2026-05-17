import structlog
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import Polygon
from shapely.validation import make_valid

logger = structlog.get_logger(__name__)


@dataclass
class SegmentedPanel:
    polygon: Polygon
    area_pixels: float
    centroid_x: float
    centroid_y: float
    confidence: float
    is_valid: bool = True
    rejection_reason: str = ""


class SegmentationProcessor:
    """
    Processa polígonos de segmentação retornados pelo detector YOLO,
    calcula área em pixels e filtra detecções inválidas.
    """

    MIN_AREA_PIXELS = 100
    MAX_ASPECT_RATIO = 10.0

    def process(self, detections: list[dict]) -> list[SegmentedPanel]:
        panels = []

        for detection in detections:
            polygon_coords = detection.get("mask_polygon", [])
            confidence = detection.get("confidence", 0.0)

            if not polygon_coords or len(polygon_coords) < 3:
                polygon_coords = self._bbox_to_polygon(detection.get("bbox_xyxy", []))

            panel = self._process_single(polygon_coords, confidence)
            panels.append(panel)

        valid = [p for p in panels if p.is_valid]
        invalid = [p for p in panels if not p.is_valid]

        logger.info(
            "segmentation.processed",
            total=len(panels),
            valid=len(valid),
            invalid=len(invalid),
        )

        return valid

    def _process_single(
        self, polygon_coords: list, confidence: float
    ) -> SegmentedPanel:
        try:
            polygon = Polygon(polygon_coords)
            polygon = make_valid(polygon)

            if not polygon.is_valid or polygon.is_empty:
                return self._invalid_panel(reason="polygon_invalid")

            area_pixels = polygon.area
            if area_pixels < self.MIN_AREA_PIXELS:
                return self._invalid_panel(reason="area_too_small")

            bounds = polygon.bounds
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]

            if height > 0 and (width / height) > self.MAX_ASPECT_RATIO:
                return self._invalid_panel(reason="aspect_ratio_exceeded")

            centroid = polygon.centroid

            return SegmentedPanel(
                polygon=polygon,
                area_pixels=float(area_pixels),
                centroid_x=float(centroid.x),
                centroid_y=float(centroid.y),
                confidence=confidence,
                is_valid=True,
            )

        except Exception as exc:
            logger.warning("segmentation.error", error=str(exc))
            return self._invalid_panel(reason=f"exception:{exc}")

    def _bbox_to_polygon(self, bbox: list) -> list[list[float]]:
        if len(bbox) < 4:
            return []
        x1, y1, x2, y2 = bbox[:4]
        return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    def _invalid_panel(self, reason: str) -> SegmentedPanel:
        return SegmentedPanel(
            polygon=Polygon(),
            area_pixels=0.0,
            centroid_x=0.0,
            centroid_y=0.0,
            confidence=0.0,
            is_valid=False,
            rejection_reason=reason,
        )

    def total_area_pixels(self, panels: list[SegmentedPanel]) -> float:
        return sum(p.area_pixels for p in panels if p.is_valid)
