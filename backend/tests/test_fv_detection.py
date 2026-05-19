import pytest
import numpy as np
from unittest.mock import MagicMock
from pathlib import Path

from ml_engine.fv_detection.detector import FVDetector, DetectionResult
from ml_engine.fv_detection.segmentation import SegmentationProcessor, SegmentedPanel
from ml_engine.fv_detection.pixel_to_area import PixelToAreaConverter, GeoReferenceParams
from ml_engine.fv_detection.kwp_estimator import KWpEstimator
from data_pipeline.datasets.cvat_converter import CVATConverter
from backend.schemas.fv_detection import (
    FVDetectionRequest,
    GeoReferenceInput,
    InjectionStatus,
    OperationalScore,
)
from backend.services.fv_detection_service import FVDetectionService


@pytest.fixture
def dummy_image() -> np.ndarray:
    return np.zeros((640, 640, 3), dtype=np.uint8)


@pytest.fixture
def base_request() -> FVDetectionRequest:
    return FVDetectionRequest(
        uc_code="UC-001",
        transformer_id="TR-102",
        latitude=-8.034,
        longitude=-34.941,
        geo_reference=GeoReferenceInput(gsd_m_per_pixel=0.10),
        regional_kwp_factor=0.15,
        confidence_threshold=0.45,
    )


@pytest.fixture
def detection_with_panels() -> DetectionResult:
    return DetectionResult(
        has_fv=True,
        confidence=0.87,
        detections=[
            {
                "class": "painel_solar",
                "confidence": 0.87,
                "bbox_xyxy": [10.0, 10.0, 110.0, 110.0],
                "mask_polygon": [
                    [10.0, 10.0],
                    [110.0, 10.0],
                    [110.0, 110.0],
                    [10.0, 110.0],
                ],
            }
        ],
        rejected=[],
        model_version="fv_detector_v1",
    )


@pytest.fixture
def detection_empty() -> DetectionResult:
    return DetectionResult(
        has_fv=False,
        confidence=0.0,
        detections=[],
        rejected=[],
        model_version="fv_detector_v1",
    )


class TestFVDetector:
    def test_aggregate_confidence_empty(self):
        detector = FVDetector.__new__(FVDetector)
        result = detector._aggregate_confidence([])
        assert result == 0.0

    def test_aggregate_confidence_single(self):
        detector = FVDetector.__new__(FVDetector)
        result = detector._aggregate_confidence([{"confidence": 0.85}])
        assert result == 0.85

    def test_aggregate_confidence_multiple(self):
        detector = FVDetector.__new__(FVDetector)
        detections = [{"confidence": 0.80}, {"confidence": 0.90}]
        result = detector._aggregate_confidence(detections)
        assert result == pytest.approx(0.85, abs=0.01)

    def test_load_model_raises_on_missing_file(self):
        detector = FVDetector(model_path="/non/existent/model.pt")
        with pytest.raises(RuntimeError, match="Falha ao carregar modelo YOLO"):
            detector._load_model()


class TestSegmentationProcessor:
    def setup_method(self):
        self.processor = SegmentationProcessor()

    def test_valid_polygon_accepted(self):
        detection = {
            "class": "painel_solar",
            "confidence": 0.87,
            "bbox_xyxy": [0, 0, 100, 100],
            "mask_polygon": [
                [0.0, 0.0],
                [100.0, 0.0],
                [100.0, 100.0],
                [0.0, 100.0],
            ],
        }
        panels = self.processor.process([detection])
        assert len(panels) == 1
        assert panels[0].is_valid
        assert panels[0].area_pixels > 0

    def test_small_polygon_rejected(self):
        detection = {
            "confidence": 0.87,
            "bbox_xyxy": [0, 0, 5, 5],
            "mask_polygon": [[0, 0], [5, 0], [5, 5], [0, 5]],
        }
        panels = self.processor.process([detection])
        assert len(panels) == 0

    def test_bbox_fallback_when_no_mask(self):
        detection = {
            "confidence": 0.87,
            "bbox_xyxy": [0.0, 0.0, 200.0, 200.0],
            "mask_polygon": [],
        }
        panels = self.processor.process([detection])
        assert len(panels) == 1
        assert panels[0].area_pixels == pytest.approx(40000.0, rel=0.01)

    def test_total_area_pixels(self):
        from shapely.geometry import Polygon as ShapelyPolygon

        panels = [
            SegmentedPanel(
                polygon=ShapelyPolygon(),
                area_pixels=1000.0,
                centroid_x=0,
                centroid_y=0,
                confidence=0.9,
                is_valid=True,
            ),
            SegmentedPanel(
                polygon=ShapelyPolygon(),
                area_pixels=2000.0,
                centroid_x=0,
                centroid_y=0,
                confidence=0.8,
                is_valid=True,
            ),
        ]
        total = self.processor.total_area_pixels(panels)
        assert total == 3000.0


class TestPixelToAreaConverter:
    def test_gsd_direct_conversion(self):
        params = GeoReferenceParams(gsd_m_per_pixel=0.10)
        converter = PixelToAreaConverter(params)
        area_m2 = converter.convert(10000.0)
        assert area_m2 == pytest.approx(100.0, rel=0.01)

    def test_gsd_from_camera_params(self):
        params = GeoReferenceParams(
            altitude_m=100.0,
            focal_length_mm=35.0,
            sensor_width_mm=17.3,
            image_width_px=5472,
        )
        converter = PixelToAreaConverter(params)
        assert converter.gsd > 0

    def test_zero_area_returns_zero(self):
        params = GeoReferenceParams(gsd_m_per_pixel=0.10)
        converter = PixelToAreaConverter(params)
        assert converter.convert(0.0) == 0.0

    def test_perspective_correction_applied(self):
        params_no_correction = GeoReferenceParams(gsd_m_per_pixel=0.10)
        params_with_correction = GeoReferenceParams(
            gsd_m_per_pixel=0.10,
            perspective_correction=0.9,
        )
        c1 = PixelToAreaConverter(params_no_correction)
        c2 = PixelToAreaConverter(params_with_correction)
        area1 = c1.convert(10000.0)
        area2 = c2.convert(10000.0)
        assert area2 < area1

    def test_fallback_gsd_used_when_no_params(self):
        params = GeoReferenceParams()
        converter = PixelToAreaConverter(params)
        assert converter.gsd == PixelToAreaConverter.DEFAULT_GSD

    def test_batch_conversion(self):
        params = GeoReferenceParams(gsd_m_per_pixel=0.10)
        converter = PixelToAreaConverter(params)
        results = converter.convert_batch([1000.0, 2000.0, 3000.0])
        assert len(results) == 3
        assert results[1] > results[0]


class TestKWpEstimator:
    def test_default_factor_used(self):
        estimator = KWpEstimator()
        result = estimator.estimate(area_m2=10.0, detection_confidence=1.0)
        assert result.factor_source == "default"
        assert result.kwp_estimated == pytest.approx(1.5, rel=0.01)

    def test_transformer_factor_priority(self):
        estimator = KWpEstimator(
            regional_factor=0.12,
            transformer_factor=0.18,
            cluster_factor=0.14,
        )
        result = estimator.estimate(10.0)
        assert result.factor_source == "transformer"
        assert result.factor_used == 0.18

    def test_cluster_factor_over_regional(self):
        estimator = KWpEstimator(regional_factor=0.12, cluster_factor=0.14)
        result = estimator.estimate(10.0)
        assert result.factor_source == "cluster"

    def test_confidence_penalty_high_confidence(self):
        estimator = KWpEstimator()
        result = estimator.estimate(10.0, detection_confidence=0.95)
        assert result.confidence_penalty == 1.0

    def test_confidence_penalty_low_confidence(self):
        estimator = KWpEstimator()
        result = estimator.estimate(10.0, detection_confidence=0.40)
        assert result.confidence_penalty < 1.0
        assert result.kwp_adjusted < result.kwp_estimated

    def test_clamp_min_kwp(self):
        estimator = KWpEstimator()
        result = estimator.estimate(area_m2=0.001)
        assert result.kwp_estimated >= KWpEstimator.MIN_KWP

    def test_clamp_max_kwp(self):
        estimator = KWpEstimator()
        result = estimator.estimate(area_m2=99999.0)
        assert result.kwp_estimated <= KWpEstimator.MAX_KWP

    def test_update_transformer_factor(self):
        estimator = KWpEstimator()
        estimator.update_transformer_factor(0.20)
        result = estimator.estimate(10.0)
        assert result.factor_source == "transformer"
        assert result.factor_used == 0.20


class TestFVDetectionService:
    def test_empty_result_when_no_fv(
        self,
        base_request: FVDetectionRequest,
        dummy_image: np.ndarray,
    ):
        service = FVDetectionService.__new__(FVDetectionService)
        service._detector = MagicMock()
        service._segmentation = SegmentationProcessor()

        service._detector.detect.return_value = DetectionResult(
            has_fv=False,
            confidence=0.0,
            detections=[],
            rejected=[],
            model_version="mock_v1",
        )

        result = service.run(base_request, dummy_image)

        assert result.has_fv is False
        assert result.total_panels == 0
        assert result.kwp_adjusted == 0.0
        assert result.status == InjectionStatus.CONSUMING

    def test_full_pipeline_with_panels(
        self,
        base_request: FVDetectionRequest,
        dummy_image: np.ndarray,
        detection_with_panels: DetectionResult,
    ):
        service = FVDetectionService.__new__(FVDetectionService)
        service._detector = MagicMock()
        service._segmentation = SegmentationProcessor()
        service._detector.detect.return_value = detection_with_panels

        result = service.run(base_request, dummy_image)

        assert result.has_fv is True
        assert result.total_panels >= 1
        assert result.kwp_adjusted > 0
        assert result.total_area_m2 > 0
        assert result.uc_code == "UC-001"
        assert result.transformer_id == "TR-102"

    def test_operational_score_high_confidence(self):
        service = FVDetectionService.__new__(FVDetectionService)
        score = service._calculate_operational_score(0.90, 15.0, 3)
        assert score == OperationalScore.LOW_RISK

    def test_operational_score_low_confidence(self):
        service = FVDetectionService.__new__(FVDetectionService)
        score = service._calculate_operational_score(0.30, 2.0, 1)
        assert score == OperationalScore.INSPECTION_PRIORITY


class TestCVATConverter:
    MINIMAL_CVAT_XML = """<?xml version="1.0" encoding="utf-8"?>
<annotations>
  <image id="1" name="img_001.jpg" width="1280" height="720">
    <polygon label="painel_solar" points="100,200;300,200;300,400;100,400" z_order="0"/>
  </image>
  <image id="2" name="img_002.jpg" width="1280" height="720">
    <polygon label="telhado" points="10,10;50,10;50,50;10,50" z_order="0"/>
  </image>
</annotations>
"""

    def test_parse_valid_xml(self, tmp_path: Path):
        xml_file = tmp_path / "annotations.xml"
        xml_file.write_text(self.MINIMAL_CVAT_XML, encoding="utf-8")

        converter = CVATConverter()
        labels = converter._parse_xml(xml_file)

        assert len(labels) == 1
        assert labels[0].image_name == "img_001.jpg"
        assert len(labels[0].polygons) == 1

    def test_ignores_non_panel_labels(self, tmp_path: Path):
        xml_file = tmp_path / "annotations.xml"
        xml_file.write_text(self.MINIMAL_CVAT_XML, encoding="utf-8")

        converter = CVATConverter()
        labels = converter._parse_xml(xml_file)

        names = [label.image_name for label in labels]
        assert "img_002.jpg" not in names

    def test_full_conversion_writes_labels(self, tmp_path: Path):
        xml_file = tmp_path / "annotations.xml"
        xml_file.write_text(self.MINIMAL_CVAT_XML, encoding="utf-8")

        output_dir = tmp_path / "output"
        converter = CVATConverter()
        result = converter.convert(str(xml_file), str(output_dir))

        assert result.total_images == 1
        assert result.total_labels == 1

        label_file = output_dir / "labels" / "img_001.txt"
        assert label_file.exists()

        content = label_file.read_text().strip()
        assert content.startswith("0 ")

    def test_normalized_coordinates_within_bounds(self, tmp_path: Path):
        xml_file = tmp_path / "annotations.xml"
        xml_file.write_text(self.MINIMAL_CVAT_XML, encoding="utf-8")

        converter = CVATConverter()
        labels = converter._parse_xml(xml_file)

        for label in labels:
            for polygon in label.polygons:
                for x, y in polygon:
                    assert 0.0 <= x <= 1.0
                    assert 0.0 <= y <= 1.0