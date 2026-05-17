"""
Testes de integração dos endpoints de batch.
Utiliza AsyncClient + banco de teste em memória.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


BATCH_INFERENCE_PAYLOAD = {
    "transformer_id": "TR-001",
    "measured_kwh": 1500.0,
    "period_start": "2025-01-01T00:00:00+00:00",
    "period_end": "2025-01-02T00:00:00+00:00",
}

TELEMETRY_PAYLOAD = {
    "source_type": "uc",
    "payloads": [
        {
            "source_id": "UC001",
            "measured_at": "2025-01-01T12:00:00+00:00",
            "active_power_kw": 1.2,
            "voltage_v": 220.0,
            "power_factor": 0.95,
        }
    ],
}


@pytest.mark.asyncio
async def test_enqueue_batch_inference(auth_client: AsyncClient):
    with patch("backend.api.v1.endpoints.batch.enqueue", new_callable=AsyncMock) as mock_enqueue:
        mock_enqueue.return_value = "mock_job_id"
        response = await auth_client.post("/api/v1/batch/inference", json=BATCH_INFERENCE_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "job_id" in data["data"]


@pytest.mark.asyncio
async def test_enqueue_telemetry(auth_client: AsyncClient):
    with patch("backend.api.v1.endpoints.batch.enqueue", new_callable=AsyncMock) as mock_enqueue:
        mock_enqueue.return_value = "mock_telemetry_job"
        response = await auth_client.post("/api/v1/batch/telemetry", json=TELEMETRY_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_job_status_not_found(auth_client: AsyncClient):
    with patch("backend.api.v1.endpoints.batch.get_job_status", new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {"job_id": "fake_id", "status": "not_found"}
        response = await auth_client.get("/api/v1/batch/jobs/fake_id/status")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "not_found"
