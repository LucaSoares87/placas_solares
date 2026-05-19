import pytest
from datetime import datetime, timedelta, timezone

from backend.workers.validators.telemetry_validator import (
    TelemetryValidationError,
    TelemetryValidator,
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


def test_validate_ok(validator: TelemetryValidator):
    result = validator.validate(_base_payload())

    assert result["source_id"] == "UC001"
    assert isinstance(result["measured_at"], datetime)
    assert result["active_power_kw"] == 1.5


def test_validate_missing_source_id(validator: TelemetryValidator):
    with pytest.raises(TelemetryValidationError, match="source_id"):
        validator.validate(
            {
                "measured_at": datetime.now(timezone.utc).isoformat(),
            }
        )


def test_validate_missing_measured_at(validator: TelemetryValidator):
    with pytest.raises(TelemetryValidationError, match="measured_at"):
        validator.validate(
            {
                "source_id": "UC001",
            }
        )


def test_validate_future_timestamp(validator: TelemetryValidator):
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    with pytest.raises(TelemetryValidationError, match="futuro"):
        validator.validate(_base_payload(measured_at=future))


def test_quality_flag_ok(validator: TelemetryValidator):
    validated = validator.validate(_base_payload())

    assert validator.quality_flag(validated) == "ok"


def test_quality_flag_suspect_power_factor(validator: TelemetryValidator):
    payload = _base_payload(power_factor=1.5)
    validated = validator.validate(payload)

    assert validator.quality_flag(validated) == "suspect"


def test_quality_flag_invalid_voltage(validator: TelemetryValidator):
    payload = _base_payload(voltage_v=10.0)
    validated = validator.validate(payload)

    assert validator.quality_flag(validated) == "invalid"


def test_quality_flag_out_of_range_power(validator: TelemetryValidator):
    payload = _base_payload(active_power_kw=99_999.0)
    validated = validator.validate(payload)

    assert validator.quality_flag(validated) == "suspect"


def test_safe_float_none(validator: TelemetryValidator):
    assert validator._safe_float(None) is None


def test_safe_float_invalid_string(validator: TelemetryValidator):
    assert validator._safe_float("abc") is None


def test_safe_float_valid(validator: TelemetryValidator):
    assert validator._safe_float("3.14") == pytest.approx(3.14)