from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.domain.entities import RiskScore
from backend.workers.anomaly_detector import AnomalyDetector


def _make_balance(
    transformer_id: str = "TR-001",
    percentage_error: float = 0.0,
    measured_kwh: float = 100.0,
    estimated_generation_kwh: float = 10.0,
    estimated_consumption_kwh: float = 90.0,
    gd_count: int = 2,
    uc_count: int = 10,
):
    balance = MagicMock()
    balance.transformer_id = transformer_id
    balance.percentage_error = percentage_error
    balance.measured_kwh = measured_kwh
    balance.estimated_generation_kwh = estimated_generation_kwh
    balance.estimated_consumption_kwh = estimated_consumption_kwh
    balance.gd_count = gd_count
    balance.uc_count = uc_count
    balance.gd_penetration_rate = gd_count / uc_count if uc_count else 0.0
    balance.period_start = MagicMock(date=lambda: "2025-01-01")
    balance.period_end = MagicMock(date=lambda: "2025-01-02")
    return balance


def _make_transformer(rated_kva: float = 100.0):
    transformer = MagicMock()
    transformer.rated_kva = rated_kva
    return transformer


def _make_session():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_detector(session=None, rated_kva: float = 500.0) -> AnomalyDetector:
    session = session or _make_session()

    detector = AnomalyDetector(session)
    detector._tr_repo = MagicMock()
    detector._tr_repo.get_by_transformer_id = AsyncMock(
        return_value=_make_transformer(rated_kva=rated_kva)
    )

    return detector


@pytest.mark.asyncio
async def test_no_anomalies_when_balanced():
    session = _make_session()
    detector = _make_detector(session=session, rated_kva=500.0)

    balance = _make_balance(percentage_error=2.0, measured_kwh=100.0)

    count = await detector.analyze_balance(balance)

    assert count == 0
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_detects_high_balance_error():
    session = _make_session()
    detector = _make_detector(session=session, rated_kva=500.0)

    balance = _make_balance(percentage_error=30.0, measured_kwh=100.0)

    count = await detector.analyze_balance(balance)

    assert count >= 1
    session.add.assert_called()


@pytest.mark.asyncio
async def test_detects_generation_over_consumption():
    session = _make_session()
    detector = _make_detector(session=session, rated_kva=500.0)

    balance = _make_balance(
        estimated_generation_kwh=200.0,
        estimated_consumption_kwh=50.0,
    )

    count = await detector.analyze_balance(balance)

    assert count >= 1
    session.add.assert_called()


@pytest.mark.asyncio
async def test_detects_transformer_overload():
    session = _make_session()
    detector = _make_detector(session=session, rated_kva=50.0)

    balance = _make_balance(measured_kwh=5000.0)

    count = await detector.analyze_balance(balance)

    assert count >= 1
    session.add.assert_called()


@pytest.mark.asyncio
async def test_detects_high_gd_penetration():
    session = _make_session()
    detector = _make_detector(session=session, rated_kva=500.0)

    balance = _make_balance(gd_count=9, uc_count=10)

    count = await detector.analyze_balance(balance)

    assert count >= 1
    session.add.assert_called()


def test_error_severity_thresholds():
    assert AnomalyDetector._error_severity(30.0) == RiskScore.CRITICAL
    assert AnomalyDetector._error_severity(20.0) == RiskScore.HIGH
    assert AnomalyDetector._error_severity(10.0) == RiskScore.MEDIUM
    assert AnomalyDetector._error_severity(2.0) == RiskScore.LOW