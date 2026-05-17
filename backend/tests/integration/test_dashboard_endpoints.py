"""
Testes de integração dos endpoints de Dashboard.
Usa AsyncClient com mocks no service para isolar banco de dados.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient

from backend.schemas.dashboard import (
    GlobalKPIResponse,
    RiskMapResponse,
    GDRankingResponse,
)


def _kpis():
    return GlobalKPIResponse(
        total_transformers=5,
        total_ucs=100,
        total_ucs_with_gd=20,
        total_ucs_telemetered=40,
        total_generation_kw=50.0,
        total_consumption_kw=120.0,
        total_injection_kw=25.0,
        gd_penetration_rate=0.20,
        telemetry_coverage_rate=0.40,
        transformers_balanced=4,
        transformers_critical=0,
        transformers_high_loss=1,
        open_anomalies=2,
        critical_anomalies=0,
        avg_inference_confidence=0.85,
        reference_period_start=None,
        reference_period_end=None,
        computed_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_get_kpis_authenticated(auth_client: AsyncClient):
    with patch(
        "backend.api.v1.endpoints.dashboard.DashboardService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_global_kpis = AsyncMock(return_value=_kpis())

        response = await auth_client.get("/api/v1/dashboard/kpis")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_ucs"] == 100
    assert data["data"]["gd_penetration_rate"] == 0.20


@pytest.mark.asyncio
async def test_get_kpis_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/dashboard/kpis")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_transformer_summary_not_found(auth_client: AsyncClient):
    with patch(
        "backend.api.v1.endpoints.dashboard.DashboardService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_transformer_summary = AsyncMock(return_value=None)

        response = await auth_client.get("/api/v1/dashboard/transformers/TR-FAKE")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_risk_map(auth_client: AsyncClient):
    mock_map = MagicMock(spec=RiskMapResponse)
    mock_map.points = []
    mock_map.total = 0
    mock_map.critical_count = 0
    mock_map.high_count = 0
    mock_map.medium_count = 0
    mock_map.low_count = 0
    mock_map.computed_at = datetime.now(timezone.utc)
    mock_map.model_dump = lambda **kw: {
        "points": [],
        "total": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch(
        "backend.api.v1.endpoints.dashboard.DashboardService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_risk_map = AsyncMock(return_value=mock_map)
        response = await auth_client.get("/api/v1/dashboard/risk-map")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_export_requires_engineering_role(readonly_client: AsyncClient):
    """Usuário com perfil consulta não pode exportar."""
    response = await readonly_client.post(
        "/api/v1/dashboard/export",
        json={
            "report_type": "transformer_balance",
            "format": "csv",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_export_transformer_balance_csv(auth_client: AsyncClient):
    with patch(
        "backend.api.v1.endpoints.dashboard.DashboardService"
    ) as MockService:
        instance = MockService.return_value
        instance.export_transformer_balances = AsyncMock(
            return_value=("transformer_id,period_start\nTR-001,2025-01-01", "text/csv")
        )
        response = await auth_client.post(
            "/api/v1/dashboard/export",
            json={
                "report_type": "transformer_balance",
                "format": "csv",
                "transformer_id": "TR-001",
            },
        )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_gd_ranking_pagination(auth_client: AsyncClient):
    mock_ranking = MagicMock(spec=GDRankingResponse)
    mock_ranking.items = []
    mock_ranking.total = 0
    mock_ranking.total_generation_kw = 0.0
    mock_ranking.total_injection_kw = 0.0
    mock_ranking.avg_confidence = 0.0
    mock_ranking.page = 1
    mock_ranking.page_size = 20
    mock_ranking.pages = 1
    mock_ranking.model_dump = lambda **kw: {
        "items": [],
        "total": 0,
        "total_generation_kw": 0.0,
        "total_injection_kw": 0.0,
        "avg_confidence": 0.0,
        "page": 1,
        "page_size": 20,
        "pages": 1,
    }

    with patch(
        "backend.api.v1.endpoints.dashboard.DashboardService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_gd_ranking = AsyncMock(return_value=mock_ranking)

        response = await auth_client.get(
            "/api/v1/dashboard/gd-ranking?page=1&page_size=20"
        )

    assert response.status_code == 200
