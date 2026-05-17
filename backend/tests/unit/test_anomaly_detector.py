from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.domain.entities import AnomalyType, RiskScore
from backend.worker.anomaly_detector import AnomalyDetector


def _make_balance(
    transformer_id="TR-001",
    percentage_error=0.0,
    measured_kwh=100.0,
    estimated_generation_kwh=10.0,
    estimated_consumption_kwh=90.0,
    gd_count=2,
    uc_count=10,
):
    b = MagicMock()
    b.transformer_id = transformer_id
    b.percentage_error = percentage_error
    b.measured_kwh = measured_kwh
    b.estimated_generation_kwh = estimated_generation_kwh
    b.estimated_consumption_kwh = estimated_consumption_kwh
    b.gd_count = gd_count
    b.uc_count = uc_count
    b.gd_penetration_rate = gd_count / uc_count if uc_count else 0.0
    b.period_start = MagicMock(date=lambda: "2025-01-01")
    b.period_end = MagicMock(date=lambda: "2025-01-02")
    return b


def _make_transformer(rated_kva=100.0):
    tr = MagicMock()
    tr.rated_kva = rated_kva
    return tr


@pytest.mark.asyncio
async def test_no_anomalies_when_balanced():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    detector = AnomalyDetector(session)
    detector._tr_repo = MagicMock()
    detector._tr_repo.get_by_transformer_id = AsyncMock(
        return_value=_make_transformer(rated_kva=500.0)
    )

    balance = _make_balance(percentage_error=2.0, measured_kwh=100.0)
    count = await detector.analyze_balance(balance)
    assert count == 0


@pytest.mark.asyncio
async def test_detects_high_balance_error():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    detector = AnomalyDetector(session)
    detector._tr_repo = MagicMock()
    detector._tr_repo.get_by_transformer_id = AsyncMock(
        return_value=_make_transformer(rated_kva=500.0)
    )

    balance = _make_balance(percentage_error=30.0, measured_kwh=100.0)
    count = await detector.analyze_balance(balance)
    assert count >= 1
    session.add.assert_called()


@pytest.mark.asyncio
async def test_detects_generation_over_consumption():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    detector = AnomalyDetector(session)
    detector._tr_repo = MagicMock()
    detector._tr_repo.get_by_transformer_id = AsyncMock(
        return_value=_make_transformer(rated_kva=500.0)
    )

    balance = _make_balance(
        estimated_generation_kwh=200.0,
        estimated_consumption_kwh=50.0,
    )
    count = await detector.analyze_balance(balance)
    assert count >= 1


@pytest.mark.asyncio
async def test_detects_transformer_overload():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    detector = AnomalyDetector(session)
    detector._tr_repo = MagicMock()
    detector._tr_repo.get_by_transformer_id = AsyncMock(
        return_value=_make_transformer(rated_kva=50.0)   # pequeno
    )

    balance = _make_balance(measured_kwh=5000.0)   # muito acima da nominal
    count = await detector.analyze_balance(balance)
    assert count >= 1


@pytest.mark.asyncio
async def test_detects_high_gd_penetration():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    detector = AnomalyDetector(session)
    detector._tr_repo = MagicMock()
    detector._tr_repo.get_by_transformer_id = AsyncMock(
        return_value=_make_transformer(rated_kva=500.0)
    )

    balance = _make_balance(gd_count=9, uc_count=10)   # 90% GD
    count = await detector.analyze_balance(balance)
    assert count >= 1


def test_error_severity_thresholds():
    assert AnomalyDetector._error_severity(30.0) == RiskScore.CRITICAL
    assert AnomalyDetector._error_severity(20.0) == RiskScore.HIGH
    assert AnomalyDetector._error_severity(10.0) == RiskScore.MEDIUM
    assert AnomalyDetector._error_severity(2.0) == RiskScore.LOW
