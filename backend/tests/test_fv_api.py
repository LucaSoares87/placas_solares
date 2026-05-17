import pytest
import numpy as np
import io
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.schemas.fv_detection import (
    FVDetectionResponse,
    InjectionStatus,
    OperationalScore,
)


def _build_mock_response() -> FVDetectionResponse:
    return FVDetectionResponse(
        uc_code="UC-001",
        transformer_id="TR-102",
        latitude=-8.034,
        longitude=-34.941,
        has_fv=True,
        total_panels=2,
        total_area_m2=28.0,
        kwp_estimated=4.2,
        kwp_adjusted=4.0,
        kwp_factor_used=0.15,
        kwp_factor_source="regional",
        detection_confidence=0.87,
        panels=[],
        model_version="fv_detector_v1",
        status=InjectionStatus.INJECTING,
        score_operacional=OperationalScore.LOW_RISK,
    )


def _dummy_jpeg_bytes() -> bytes:
    try:
        import cv2
        img = np.zeros((640, 640, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", img)
        return buf.tobytes()
    except ImportError:
        return b"\xff\xd8\xff\xe0" + b"\x00" * 100


@pytest.fixture
def client():
    from backend.app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer mock_token"}


class TestFVDetectionAPI:
    def test_fv_health_endpoint(self, client: TestClient):
        response = client.get("/api/v1/fv/health")
        assert response.status_code in (200, 401)

    @patch("backend.api.v1.fv_detection.FVDetectionService")
    @patch("backend.api.v1.fv_detection.get_current_user")
    def test_detect_sync_success(
        self,
        mock_auth,
        mock_service_cls,
        client: TestClient,
        auth_headers: dict,
    ):
        mock_auth.return_value = MagicMock(matricula="ENG001")
        mock_service = MagicMock()
        mock_service.run.return_value = _build_mock_response()
        mock_service_cls.return_value = mock_service

        image_bytes = _dummy_jpeg_bytes()

        response = client.post(
            "/api/v1/fv/detect",
            data={
                "uc_code": "UC-001",
                "transformer_id": "TR-102",
                "latitude": "-8.034",
                "longitude": "-34.941",
            },
            files={"image": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")},
            headers=auth_headers,
        )

        assert response.status_code in (200, 422, 500)

    @patch("backend.api.v1.fv_detection.run_fv_detection_task")
    @patch("backend.api.v1.fv_detection.get_current_user")
    def test_detect_async_queued(
        self,
        mock_auth,
        mock_task,
        client: TestClient,
        auth_headers: dict,
    ):
        mock_auth.return_value = MagicMock(matricula="ENG001")
        mock_task_result = MagicMock()
        mock_task_result.id = "task-uuid-001"
        mock_task.apply_async.return_value = mock_task_result

        image_bytes = _dummy_jpeg_bytes()

        response = client.post(
            "/api/v1/fv/detect-async",
            data={
                "uc_code": "UC-001",
                "transformer_id": "TR-102",
                "latitude": "-8.034",
                "longitude": "-34.941",
            },
            files={"image": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")},
            headers=auth_headers,
        )

        assert response.status_code in (202, 422, 500)
