import pytest
from pydantic import ValidationError

from backend.domain.entities import EnergyStatus, InferenceMethod, RiskScore
from backend.schemas.energy_inference import EnergyInferenceCreate
from backend.schemas.transformer_balance import TransformerBalanceCreate
from datetime import datetime, timezone


def _valid_inference(**kwargs) -> dict:
    base = dict(
        uc_code="UC001",
        transformer_id="TR-001",
        has_fv=False,
        consumption_estimated_kw=1.2,
        confidence=0.75,
        status=EnergyStatus.NORMAL,
        operational_score=RiskScore.LOW,
        inference_method=InferenceMethod.STATISTICAL,
    )
    base.update(kwargs)
    return base


def test_inference_create_valid():
    obj = EnergyInferenceCreate(**_valid_inference())
    assert obj.uc_code == "UC001"
    assert obj.has_fv is False


def test_inference_create_with_fv():
    obj = EnergyInferenceCreate(
        **_valid_inference(
            has_fv=True,
            kwp_estimated=6.0,
            generation_kw=1.1,
            injection_kw_min=0.1,
            injection_kw_max=0.9,
        )
    )
    assert obj.has_fv is True
    assert obj.kwp_estimated == 6.0


def test_inference_create_fv_missing_kwp():
    with pytest.raises(ValidationError, match="kwp_estimated"):
        EnergyInferenceCreate(
            **_valid_inference(has_fv=True, generation_kw=1.0)
        )


def test_inference_create_injection_inverted():
    with pytest.raises(ValidationError, match="injection_kw_min"):
        EnergyInferenceCreate(
            **_valid_inference(
                has_fv=True,
                kwp_estimated=6.0,
                generation_kw=1.0,
                injection_kw_min=0.9,
                injection_kw_max=0.1,
            )
        )


def test_inference_confidence_out_of_range():
    with pytest.raises(ValidationError):
        EnergyInferenceCreate(**_valid_inference(confidence=1.5))


def _now():
    return datetime.now(timezone.utc)


def test_balance_create_valid():
    obj = TransformerBalanceCreate(
        transformer_id="TR-001",
        period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2025, 1, 2, tzinfo=timezone.utc),
        measured_kwh=100.0,
        estimated_consumption_kwh=90.0,
        estimated_generation_kwh=20.0,
        estimated_injection_kwh=10.0,
        residual_kwh=0.5,
        absolute_error=0.5,
        percentage_error=0.5,
        uc_count=10,
        telemetered_count=3,
        gd_count=4,
    )
    assert obj.transformer_id == "TR-001"
    assert obj.uc_count == 10


def test_balance_create_inverted_period():
    with pytest.raises(ValidationError, match="period_start"):
        TransformerBalanceCreate(
            transformer_id="TR-001",
            period_start=datetime(2025, 1, 2, tzinfo=timezone.utc),
            period_end=datetime(2025, 1, 1, tzinfo=timezone.utc),
            measured_kwh=100.0,
            estimated_consumption_kwh=90.0,
            estimated_generation_kwh=20.0,
            estimated_injection_kwh=10.0,
            residual_kwh=0.5,
            absolute_error=0.5,
            percentage_error=0.5,
            uc_count=10,
            telemetered_count=3,
            gd_count=4,
        )


def test_balance_telemetered_exceeds_uc_count():
    with pytest.raises(ValidationError, match="telemetered_count"):
        TransformerBalanceCreate(
            transformer_id="TR-001",
            period_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2025, 1, 2, tzinfo=timezone.utc),
            measured_kwh=100.0,
            estimated_consumption_kwh=90.0,
            estimated_generation_kwh=20.0,
            estimated_injection_kwh=10.0,
            residual_kwh=0.5,
            absolute_error=0.5,
            percentage_error=0.5,
            uc_count=5,
            telemetered_count=10,
            gd_count=2,
        )
