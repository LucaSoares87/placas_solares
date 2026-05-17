"""
Testes unitários do EnergyBalanceService com repositório mockado.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.energy_balance_service import EnergyBalanceService


def _period():
    return (
        datetime(2025, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 1, 31, 23, 59, 59, tzinfo=timezone.utc),
    )


def _mock_transformer(transformer_id="TR-001", rated_kva=100.0):
    t = MagicMock()
    t.transformer_id = transformer_id
    t.rated_kva = rated_kva
    return t


def _mock_inference(uc_code, consumption, generation, inj_min, inj_max, confidence=0.85):
    inf = MagicMock()
    inf.uc_code = uc_code
    inf.consumption_estimated_kw = consumption
    inf.generation_kw = generation
    inf.injection_kw_min = inj_min
    inf.injection_kw_max = inj_max
    inf.confidence = confidence
    return inf


def _mock_balance(transformer_id="TR-001"):
    b = MagicMock()
    b.transformer_id = transformer_id
    b.measured_kwh = 80.0
    b.estimated_consumption_kwh = 75.0
    b.estimated_generation_kwh = 5.0
    b.estimated_injection_kwh = 2.0
    b.technical_losses_kwh = 2.4
    b.residual_kwh = 0.6
    b.absolute_error = 0.6
    b.percentage_error = 0.75
    b.balance_status = "balanced"
    b.operational_score = "low"
    b.uc_count = 10
    b.telemetered_count = 3
    b.gd_count = 2
    b.confidence = 0.85
    b.computed_at = datetime.now(timezone.utc)
    return b


def _make_service():
    session = MagicMock()
    session.scalar = AsyncMock(return_value=0)
    service = EnergyBalanceService(session)
    service._repo = MagicMock()
    return service


@pytest.mark.asyncio
async def test_compute_balance_transformer_not_found():
    service = _make_service()
    service._repo.get_transformer = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="não encontrado"):
        await service.compute_transformer_balance("TR-FAKE", *_period())


@pytest.mark.asyncio
async def test_compute_balance_cache_hit():
    service = _make_service()
    service._repo.get_transformer = AsyncMock(
        return_value=_mock_transformer()
    )
    cached = _mock_balance()
    service._repo.find_existing_balance = AsyncMock(return_value=cached)

    result = await service.compute_transformer_balance("TR-001", *_period())
    assert result.balance_status == "balanced"
    service._repo.save_balance.assert_not_called()


@pytest.mark.asyncio
async def test_compute_balance_full_pipeline():
    service = _make_service()
    service._repo.get_transformer = AsyncMock(
        return_value=_mock_transformer(rated_kva=100.0)
    )
    service._repo.find_existing_balance = AsyncMock(return_value=None)
    service._repo.get_inferences_for_period = AsyncMock(
        return_value=[
            _mock_inference("UC001", 30.0, 10.0, 2.0, 5.0),
            _mock_inference("UC002", 25.0, 0.0, 0.0, 0.0),
        ]
    )
    service._repo.get_uc_counts = AsyncMock(
        return_value={"total": 2, "telemetered": 1, "with_gd": 1}
    )
    service._repo.save_balance = AsyncMock(return_value=_mock_balance())
    service._session.commit = AsyncMock()

    result = await service.compute_transformer_balance(
        "TR-001", *_period(), force_recalculate=True
    )
    assert result.uc_count == 10
    service._repo.save_balance.assert_called_once()


@pytest.mark.asyncio
async def test_compute_batch_partial_failure():
    service = _make_service()

    async def _compute(transformer_id, period_start, period_end, force_recalculate):
        if transformer_id == "TR-FAIL":
            raise ValueError("Transformador não encontrado.")
        return _mock_balance(transformer_id)

    service.compute_transformer_balance = _compute

    result = await service.compute_batch_balance(
        transformer_ids=["TR-001", "TR-FAIL", "TR-002"],
        period_start=_period()[0],
        period_end=_period()[1],
    )

    assert result.total_requested == 3
    assert result.total_failed == 1
    assert "TR-FAIL" in result.failed_transformer_ids


@pytest.mark.asyncio
async def test_get_balance_summary():
    service = _make_service()
    service._repo.get_balance_summary = AsyncMock(
        return_value={
            "transformer_count": 5,
            "avg_percentage_error": 4.5,
            "max_percentage_error": 18.0,
            "min_percentage_error": 0.5,
            "total_measured_kwh": 5000.0,
            "total_estimated_consumption_kwh": 4800.0,
            "total_estimated_generation_kwh": 200.0,
            "total_technical_losses_kwh": 150.0,
            "total_residual_kwh": 50.0,
            "balanced_count": 3,
            "acceptable_count": 1,
            "high_loss_count": 1,
            "critical_count": 0,
            "insufficient_data_count": 0,
        }
    )

    summary = await service.get_balance_summary(*_period())
    assert summary.transformer_count == 5
    assert summary.balanced_count == 3
    assert summary.avg_percentage_error == pytest.approx(4.5)
