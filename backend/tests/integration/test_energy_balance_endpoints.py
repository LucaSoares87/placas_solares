"""
Testes de integração dos endpoints de Balanço Energético.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from backend.schemas.energy_balance import (
    BalanceComputeResponse,
    BatchBalanceResponse,
    BalanceSummaryResponse,
)


def _balance_response(transformer_id="TR-001") -> BalanceComputeResponse:
    return BalanceComputeResponse(
        transformer_id=transformer_id,
        period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2025, 1, 31, tzinfo=timezone.utc),
        measured_kwh=103.0,
        estimated_consumption_kwh=100.0,
        estimated_generation_kwh=0.0,
        estimated_injection_kwh=0.0,
        technical_losses_kwh=3.0,
        residual_kwh=0.0,
        absolute_error_kwh=0.0,
        percentage_error=0.0,
        balance_status="balanced",
        operational_score="low",
        uc_count=10,
        telemetered_count=2,
        gd_count=1,
        confidence=0.87,
        insufficient_data=False,
        validation_issues=[],
        computed_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_compute_balance_success(auth_client: AsyncClient):
    with patch(
        "backend.api.v1.endpoints.energy_balance.EnergyBalanceService"
    ) as MockService:
        instance = MockService.return_value
        instance.compute_transformer_balance = AsyncMock(
            return_value=_balance_response()
        )
        response = await auth_client.post(
            "/api/v1/transformer-balance",
            json={
                "transformer_id": "TR-001",
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-31T23:59:59Z",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["balance_status"] == "balanced"
    assert data["data"]["percentage_error"] == 0.0


@pytest.mark.asyncio
async def test_compute_balance_transformer_not_found(auth_client: AsyncClient):
    with patch(
        "backend.api.v1.endpoints.energy_balance.EnergyBalanceService"
    ) as MockService:
        instance = MockService.return_value
        instance.compute_transformer_balance = AsyncMock(
            side_effect=ValueError("Transformador não encontrado.")
        )
        response = await auth_client.post(
            "/api/v1/transformer-balance",
            json={
                "transformer_id": "TR-FAKE",
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-31T23:59:59Z",
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_compute_balance_invalid_period(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/v1/transformer-balance",
        json={
            "transformer_id": "TR-001",
            "period_start": "2025-02-01T00:00:00Z",
            "period_end": "2025-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_compute_batch_balance(auth_client: AsyncClient):
    batch_resp = BatchBalanceResponse(
        total_requested=2,
        total_computed=2,
        total_skipped=0,
        total_failed=0,
        results=[_balance_response("TR-001"), _balance_response("TR-002")],
        failed_transformer_ids=[],
        computed_at=datetime.now(timezone.utc),
    )
    with patch(
        "backend.api.v1.endpoints.energy_balance.EnergyBalanceService"
    ) as MockService:
        instance = MockService.return_value
        instance.compute_batch_balance = AsyncMock(return_value=batch_resp)
        response = await auth_client.post(
            "/api/v1/transformer-balance/batch",
            json={
                "transformer_ids": ["TR-001", "TR-002"],
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-31T23:59:59Z",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["total_computed"] == 2


@pytest.mark.asyncio
async def test_get_balance_summary(auth_client: AsyncClient):
    summary = BalanceSummaryResponse(
        period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2025, 1, 31, tzinfo=timezone.utc),
        transformer_count=10,
        avg_percentage_error=4.5,
        max_percentage_error=18.0,
        min_percentage_error=0.3,
        balanced_count=7,
        acceptable_count=2,
        high_loss_count=1,
        critical_count=0,
        insufficient_data_count=0,
        total_measured_kwh=10000.0,
        total_estimated_consumption_kwh=9500.0,
        total_estimated_generation_kwh=300.0,
        total_technical_losses_kwh=300.0,
        total_residual_kwh=200.0,
    )
    with patch(
        "backend.api.v1.endpoints.energy_balance.EnergyBalanceService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_balance_summary = AsyncMock(return_value=summary)
        response = await auth_client.get(
            "/api/v1/transformer-balance/summary"
            "?period_start=2025-01-01T00:00:00Z"
            "&period_end=2025-01-31T23:59:59Z"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["transformer_count"] == 10
    assert data["data"]["balanced_count"] == 7
