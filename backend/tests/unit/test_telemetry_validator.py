import pytest
from datetime import datetime, timezone, timedelta

from backend.worker.validators.telemetry_validator import (
    TelemetryValidator,
    TelemetryValidationError,
)


def _base_payload(**kwargs) -> dict:
    base = {
        "source_id": "UC001",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "active_power_kw": 1.5,
        "voltage_v": 220.0,
        "power_factor": 0.92,
        "energy_kwh_import": 120.0,
    }
    base.update(kwargs)
    return base


@pytest.fixture
def validator() -> TelemetryValidator:
    return TelemetryValidator()


def test_validate_ok(validator):
    result = validator.validate(_base_payload())
    assert result["source_id"] == "UC001"
    assert isinstance(result["measured_at"], datetime)
    assert result["active_power_kw"] == 1.5


def test_validate_missing_source_id(validator):
    with pytest.raises(TelemetryValidationError, match="source_id"):
        validator.validate({"measured_at": datetime.now(timezone.utc).isoformat()})


def test_validate_missing_measured_at(validator):
    with pytest.raises(TelemetryValidationError, match="measured_at"):
        validator.validate({"source_id": "UC001"})


def test_validate_future_timestamp(validator):
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    with pytest.raises(TelemetryValidationError, match="futuro"):
        validator.validate(_base_payload(measured_at=future))


def test_quality_flag_ok(validator):
    validated = validator.validate(_base_payload())
    assert validator.quality_flag(validated) == "ok"


def test_quality_flag_suspect_power_factor(validator):
    payload = _base_payload(power_factor=1.5)
    validated = validator.validate(payload)
    assert validator.quality_flag(validated) == "suspect"


def test_quality_flag_invalid_voltage(validator):
    payload = _base_payload(voltage_v=10.0)     # muito abaixo → inválido
    validated = validator.validate(payload)
    assert validator.quality_flag(validated) == "invalid"


def test_quality_flag_out_of_range_power(validator):
    payload = _base_payload(active_power_kw=99_999.0)
    validated = validator.validate(payload)
    assert validator.quality_flag(validated) == "suspect"


def test_safe_float_none(validator):
    assert validator._safe_float(None) is None


def test_safe_float_invalid_string(validator):
    assert validator._safe_float("abc") is None


def test_safe_float_valid(validator):
    assert validator._safe_float("3.14") == pytest.approx(3.14)
