from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.domain.entities import EnergyStatus, InferenceMethod, RiskScore
from backend.services.energy_inference_service import EnergyInferenceService


def _make_uc(uc_code="UC001", has_gd=True, kwp=6.0, profile="residential", transformer_id="TR-001"):
    uc = MagicMock()
    uc.uc_code = uc_code
    uc.has_gd = has_gd
    uc.gd_installed_kwp = kwp
    uc.profile = profile
    uc.transformer_id = transformer_id
    uc.is_telemetered = False
    return uc


def _make_inference(uc_code="UC001", consumption=0.9, generation=1.0, injection_mid=0.5):
    inf = MagicMock()
    inf.uc_code = uc_code
    inf.consumption_estimated_kw = consumption
    inf.generation_kw = generation
    inf.injection_kw_mid = injection_mid
    inf.status = EnergyStatus.GENERATION_DETECTED.value
    inf.confidence = 0.85
    inf.operational_score = RiskScore.LOW.value
    inf.inference_method = InferenceMethod.STATISTICAL.value
    return inf


@pytest.mark.asyncio
async def test_classify_risk_levels():
    service = EnergyInferenceService.__new__(EnergyInferenceService)
    assert service._classify_risk(0.90) == RiskScore.LOW
    assert service._classify_risk(0.70) == RiskScore.MEDIUM
    assert service._classify_risk(0.40) == RiskScore.HIGH
    assert service._classify_risk(0.10) == RiskScore.CRITICAL


@pytest.mark.asyncio
async def test_classify_balance_status():
    service = EnergyInferenceService.__new__(EnergyInferenceService)
    from backend.domain.entities import BalanceStatus
    assert service._classify_balance(2.0) == BalanceStatus.BALANCED
    assert service._classify_balance(-2.0) == BalanceStatus.BALANCED
    assert service._classify_balance(15.0) == BalanceStatus.OVER_INJECTED
    assert service._classify_balance(-15.0) == BalanceStatus.UNDER_GENERATED


@pytest.mark.asyncio
async def test_infer_from_profile_with_gd():
    session = MagicMock()
    service = EnergyInferenceService(session)

    uc = _make_uc(has_gd=True, kwp=6.0)
    service._uc_repo = MagicMock()
    service._uc_repo.get_by_uc_code = AsyncMock(return_value=uc)
    service._inf_repo = MagicMock()

    saved_inf = MagicMock()
    saved_inf.uc_code = "UC001"
    saved_inf.has_fv = True
    saved_inf.kwp_estimated = 6.0
    saved_inf.generation_kw = pytest.approx(1.1, abs=0.5)
    saved_inf.consumption_estimated_kw = 0.9
    saved_inf.status = EnergyStatus.GENERATION_DETECTED.value
    saved_inf.confidence = 0.85
    service._inf_repo.save = AsyncMock(return_value=saved_inf)
    service._uc_repo.exists_by_uc_code = AsyncMock(return_value=True)

    result = await service.infer_from_profile("UC001")
    assert result.has_fv is True
    assert result.kwp_estimated == 6.0


@pytest.mark.asyncio
async def test_infer_from_profile_no_gd():
    session = MagicMock()
    service = EnergyInferenceService(session)

    uc = _make_uc(has_gd=False, kwp=None, profile="commercial")
    service._uc_repo = MagicMock()
    service._uc_repo.get_by_uc_code = AsyncMock(return_value=uc)
    service._inf_repo = MagicMock()

    saved_inf = MagicMock()
    saved_inf.uc_code = "UC001"
    saved_inf.has_fv = False
    saved_inf.generation_kw = None
    saved_inf.consumption_estimated_kw = 4.5
    saved_inf.status = EnergyStatus.NORMAL.value
    saved_inf.confidence = 0.60
    service._inf_repo.save = AsyncMock(return_value=saved_inf)
    service._uc_repo.exists_by_uc_code = AsyncMock(return_value=True)

    result = await service.infer_from_profile("UC001")
    assert result.has_fv is False
    assert result.consumption_estimated_kw == 4.5


@pytest.mark.asyncio
async def test_get_latest_inference_not_found():
    from backend.core.exceptions import EntityNotFoundException

    session = MagicMock()
    service = EnergyInferenceService(session)
    service._inf_repo = MagicMock()
    service._inf_repo.get_latest_by_uc = AsyncMock(return_value=None)

    with pytest.raises(EntityNotFoundException):
        await service.get_latest_inference("UC_INEXISTENTE")


@pytest.mark.asyncio
async def test_compute_balance_aggregation():
    session = MagicMock()
    service = EnergyInferenceService(session)

    transformer = MagicMock()
    transformer.transformer_id = "TR-001"

    uc1 = _make_uc("UC001")
    uc2 = _make_uc("UC002", has_gd=False, kwp=None)

    inf1 = _make_inference("UC001", consumption=0.9, generation=1.0, injection_mid=0.5)
    inf2 = _make_inference("UC002", consumption=4.5, generation=0.0, injection_mid=0.0)

    service._tr_repo = MagicMock()
    service._tr_repo.get_by_transformer_id = AsyncMock(return_value=transformer)
    service._uc_repo = MagicMock()
    service._uc_repo.list_by_transformer = AsyncMock(return_value=[uc1, uc2])
    service._inf_repo = MagicMock()
    service._inf_repo.get_latest_by_uc = AsyncMock(side_effect=[inf1, inf2])

    saved_balance = MagicMock()
    saved_balance.transformer_id = "TR-001"
    saved_balance.percentage_error = pytest.approx(0.0, abs=20.0)
    service._bal_repo = MagicMock()
    service._bal_repo.save = AsyncMock(return_value=saved_balance)

    from datetime import datetime, timezone

    result = await service.compute_transformer_balance(
        transformer_id="TR-001",
        measured_kwh=100.0,
        period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
    assert result.transformer_id == "TR-001"
