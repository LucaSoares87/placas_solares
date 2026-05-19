"""
Testes unitários do DashboardService.
Todos os repositórios são mockados.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.dashboard_service import DashboardService
from backend.schemas.dashboard import GlobalKPIResponse, RiskMapResponse


def _make_session() -> MagicMock:
    return MagicMock()


def _global_kpis_data() -> dict:
    return {
        "total_transformers": 10,
        "total_ucs": 200,
        "total_ucs_with_gd": 40,
        "total_ucs_telemetered": 80,
        "total_generation_kw": 150.5,
        "total_consumption_kw": 300.0,
        "total_injection_kw": 75.25,
        "gd_penetration_rate": 0.20,
        "telemetry_coverage_rate": 0.40,
        "transformers_balanced": 7,
        "transformers_critical": 1,
        "transformers_high_loss": 2,
        "open_anomalies": 5,
        "critical_anomalies": 1,
        "avg_inference_confidence": 0.87,
        "reference_period_start": None,
        "reference_period_end": None,
        "computed_at": datetime.now(timezone.utc),
    }


@pytest.mark.asyncio
async def test_get_global_kpis_returns_schema():
    session = _make_session()
    service = DashboardService(session)
    service._repo = MagicMock()
    service._repo.get_global_kpis = AsyncMock(return_value=_global_kpis_data())

    result = await service.get_global_kpis()

    assert isinstance(result, GlobalKPIResponse)
    assert result.total_ucs == 200
    assert result.total_ucs_with_gd == 40
    assert result.gd_penetration_rate == 0.20
    assert result.transformers_balanced == 7


@pytest.mark.asyncio
async def test_get_global_kpis_zero_ucs():
    session = _make_session()
    service = DashboardService(session)
    data = _global_kpis_data()
    data.update({"total_ucs": 0, "gd_penetration_rate": 0.0, "telemetry_coverage_rate": 0.0})
    service._repo = MagicMock()
    service._repo.get_global_kpis = AsyncMock(return_value=data)

    result = await service.get_global_kpis()
    assert result.gd_penetration_rate == 0.0
    assert result.telemetry_coverage_rate == 0.0


@pytest.mark.asyncio
async def test_get_transformer_summary_not_found():
    session = _make_session()
    service = DashboardService(session)
    service._repo = MagicMock()
    service._repo.get_transformer_summary = AsyncMock(return_value=None)

    result = await service.get_transformer_summary("TR-INEXISTENTE")
    assert result is None


@pytest.mark.asyncio
async def test_get_transformer_summary_load_factor():
    session = _make_session()
    service = DashboardService(session)
    service._repo = MagicMock()
    service._repo.get_transformer_summary = AsyncMock(
        return_value={
            "transformer_id": "TR-001",
            "substation": "SE-01",
            "feeder": "AL-01",
            "latitude": -8.0,
            "longitude": -34.9,
            "rated_kva": 100.0,
            "uc_count": 50,
            "gd_count": 10,
            "telemetered_count": 20,
            "gd_penetration_rate": 0.20,
            "telemetry_coverage_rate": 0.40,
            "measured_kwh": 120.0,
            "estimated_consumption_kwh": 90.0,
            "estimated_generation_kwh": 15.0,
            "estimated_injection_kwh": 10.0,
            "technical_losses_kwh": 5.0,
            "residual_kwh": 0.5,
            "percentage_error": 3.2,
            "balance_status": "balanced",
            "operational_score": "low",
            "open_anomalies_count": 0,
            "last_balance_computed_at": datetime.now(timezone.utc),
            "last_inference_at": datetime.now(timezone.utc),
        }
    )

    result = await service.get_transformer_summary("TR-001")
    assert result is not None
    assert result.load_factor == pytest.approx(1.2, rel=1e-3)
    assert result.is_overloaded is True


@pytest.mark.asyncio
async def test_get_risk_map_counts_by_score():
    session = _make_session()
    service = DashboardService(session)
    service._repo = MagicMock()
    service._repo.get_risk_map_points = AsyncMock(
        return_value=[
            {
                "transformer_id": "TR-001",
                "latitude": -8.0,
                "longitude": -34.9,
                "operational_score": "critical",
                "balance_status": "critical",
                "open_anomalies_count": 3,
                "gd_count": 5,
                "uc_count": 20,
                "percentage_error": 30.0,
                "last_computed_at": datetime.now(timezone.utc),
            },
            {
                "transformer_id": "TR-002",
                "latitude": -8.1,
                "longitude": -34.8,
                "operational_score": "low",
                "balance_status": "balanced",
                "open_anomalies_count": 0,
                "gd_count": 2,
                "uc_count": 15,
                "percentage_error": 1.0,
                "last_computed_at": datetime.now(timezone.utc),
            },
        ]
    )

    result = await service.get_risk_map()
    assert isinstance(result, RiskMapResponse)
    assert result.total == 2
    assert result.critical_count == 1
    assert result.low_count == 1
    assert result.high_count == 0


@pytest.mark.asyncio
async def test_get_gd_ranking_pagination():
    session = _make_session()
    service = DashboardService(session)
    service._repo = MagicMock()
    service._repo.get_gd_ranking = AsyncMock(
        return_value=(
            [
                {
                    "uc_code": "UC001",
                    "transformer_id": "TR-001",
                    "address": "Rua A, 1",
                    "profile": "residential",
                    "gd_installed_kwp": 5.0,
                    "kwp_estimated": 4.8,
                    "generation_kw": 3.2,
                    "injection_kw_min": 1.0,
                    "injection_kw_max": 2.0,
                    "injection_kw_mid": 1.5,
                    "status": "injection_detected",
                    "confidence": 0.91,
                    "operational_score": "low",
                    "inference_method": "telemetry",
                    "last_computed_at": datetime.now(timezone.utc),
                }
            ],
            1,
        )
    )

    result = await service.get_gd_ranking(page=1, page_size=10)
    assert result.total == 1
    assert result.items[0].rank == 1
    assert result.items[0].uc_code == "UC001"
    assert result.total_generation_kw == pytest.approx(3.2)


@pytest.mark.asyncio
async def test_get_balance_time_series_statistics():
    from unittest.mock import MagicMock as MM

    session = _make_session()
    service = DashboardService(session)

    def _bal(pct_error, start_day):
        b = MM()
        b.period_start = datetime(2025, 1, start_day, tzinfo=timezone.utc)
        b.period_end = datetime(2025, 1, start_day + 1, tzinfo=timezone.utc)
        b.measured_kwh = 100.0
        b.estimated_consumption_kwh = 90.0
        b.estimated_generation_kwh = 5.0
        b.estimated_injection_kwh = 3.0
        b.technical_losses_kwh = 1.0
        b.residual_kwh = 0.5
        b.percentage_error = pct_error
        b.balance_status = "balanced"
        b.operational_score = "low"
        return b

    service._repo = MagicMock()
    service._repo.get_balance_time_series = AsyncMock(
        return_value=[_bal(2.0, 1), _bal(10.0, 2), _bal(5.0, 3)]
    )

    result = await service.get_balance_time_series("TR-001")
    assert result.total_points == 3
    assert result.avg_percentage_error == pytest.approx(17.0 / 3, rel=1e-3)
    assert result.max_percentage_error == pytest.approx(10.0)
    assert result.min_percentage_error == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_get_uc_detail_not_found():
    session = _make_session()
    service = DashboardService(session)
    service._repo = MagicMock()
    service._repo.get_uc_detail = AsyncMock(return_value=None)

    result = await service.get_uc_detail("UC-INEXISTENTE")
    assert result is None
