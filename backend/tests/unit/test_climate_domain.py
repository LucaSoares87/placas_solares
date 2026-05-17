"""
Testes unitários das funções de domínio climático.
Zero I/O — apenas lógica física pura.
"""

from __future__ import annotations

import pytest

from backend.domain.climate import (
    CloudCoverLevel,
    ClimateSource,
    HourlyClimateData,
    classify_cloud_cover,
    compute_cloud_factor,
    compute_climate_correction,
    compute_irradiance_factor,
    compute_temperature_factor,
    aggregate_hourly_to_daily,
    STC_IRRADIANCE_WM2,
    STC_TEMPERATURE_C,
)


# ─────────────────────────────────────────────────────────────────────────────
# classify_cloud_cover
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("pct, expected", [
    (0.0, CloudCoverLevel.CLEAR),
    (25.0, CloudCoverLevel.CLEAR),
    (25.1, CloudCoverLevel.PARTLY_CLOUDY),
    (50.0, CloudCoverLevel.PARTLY_CLOUDY),
    (50.1, CloudCoverLevel.MOSTLY_CLOUDY),
    (75.0, CloudCoverLevel.MOSTLY_CLOUDY),
    (75.1, CloudCoverLevel.OVERCAST),
    (100.0, CloudCoverLevel.OVERCAST),
])
def test_classify_cloud_cover(pct, expected):
    assert classify_cloud_cover(pct) == expected


# ─────────────────────────────────────────────────────────────────────────────
# compute_irradiance_factor
# ─────────────────────────────────────────────────────────────────────────────

def test_irradiance_factor_stc():
    assert compute_irradiance_factor(STC_IRRADIANCE_WM2) == pytest.approx(1.0)


def test_irradiance_factor_zero():
    assert compute_irradiance_factor(0.0) == pytest.approx(0.0)


def test_irradiance_factor_negative():
    assert compute_irradiance_factor(-100.0) == pytest.approx(0.0)


def test_irradiance_factor_half():
    assert compute_irradiance_factor(500.0) == pytest.approx(0.5)


def test_irradiance_factor_cap():
    # Não deve ultrapassar 1.2
    assert compute_irradiance_factor(2000.0) == pytest.approx(1.2)


# ─────────────────────────────────────────────────────────────────────────────
# compute_temperature_factor
# ─────────────────────────────────────────────────────────────────────────────

def test_temperature_factor_at_stc():
    assert compute_temperature_factor(STC_TEMPERATURE_C) == pytest.approx(1.0)


def test_temperature_factor_hot():
    # A 35°C → penalidade de 4%
    factor = compute_temperature_factor(35.0)
    assert factor == pytest.approx(0.96, abs=0.005)


def test_temperature_factor_cold():
    # Abaixo de STC → fator levemente acima de 1
    factor = compute_temperature_factor(15.0)
    assert factor > 1.0


def test_temperature_factor_floor():
    # Temperatura extrema não deve cair abaixo de 0.5
    assert compute_temperature_factor(200.0) >= 0.5


# ─────────────────────────────────────────────────────────────────────────────
# compute_cloud_factor
# ─────────────────────────────────────────────────────────────────────────────

def test_cloud_factor_clear():
    assert compute_cloud_factor(0.0) == pytest.approx(1.0)


def test_cloud_factor_overcast():
    factor = compute_cloud_factor(100.0)
    assert factor == pytest.approx(0.25, abs=0.01)


def test_cloud_factor_floor():
    assert compute_cloud_factor(100.0) >= 0.1


def test_cloud_factor_partial():
    factor = compute_cloud_factor(50.0)
    assert 0.5 < factor < 1.0


# ─────────────────────────────────────────────────────────────────────────────
# compute_climate_correction — composta
# ─────────────────────────────────────────────────────────────────────────────

def test_climate_correction_stc_conditions():
    correction = compute_climate_correction(
        irradiance_wm2=1000.0,
        temperature_c=25.0,
        cloud_cover_pct=0.0,
        source_confidence=1.0,
    )
    assert correction.irradiance_factor == pytest.approx(1.0)
    assert correction.temperature_factor == pytest.approx(1.0)
    assert correction.cloud_factor == pytest.approx(1.0)
    assert correction.composite_factor == pytest.approx(1.0)


def test_climate_correction_degraded():
    correction = compute_climate_correction(
        irradiance_wm2=400.0,
        temperature_c=35.0,
        cloud_cover_pct=40.0,
    )
    assert correction.composite_factor < 1.0
    assert correction.irradiance_factor == pytest.approx(0.4)


def test_climate_correction_confidence():
    correction = compute_climate_correction(
        irradiance_wm2=800.0,
        temperature_c=28.0,
        cloud_cover_pct=20.0,
        source_confidence=0.85,
    )
    assert correction.confidence == pytest.approx(0.85)


# ─────────────────────────────────────────────────────────────────────────────
# aggregate_hourly_to_daily
# ─────────────────────────────────────────────────────────────────────────────

def _make_hourly(n: int, irr: float = 500.0, temp: float = 28.0) -> list[HourlyClimateData]:
    return [
        HourlyClimateData(
            timestamp_utc=f"2025-01-01T{str(h).zfill(2)}:00:00Z",
            irradiance_wm2=irr,
            temperature_c=temp,
            wind_speed_ms=2.5,
            cloud_cover_pct=20.0,
            humidity_pct=65.0,
            source=ClimateSource.NASA_POWER,
            confidence=0.9,
        )
        for h in range(n)
    ]


def test_aggregate_hourly_basic():
    hourly = _make_hourly(24, irr=500.0)
    summary = aggregate_hourly_to_daily(hourly, "2025-01-01")
    assert summary is not None
    # 24h × 500 W/m² / 1000 = 12 kWh/m²
    assert summary.irradiance_daily_kwh_m2 == pytest.approx(12.0)
    assert summary.hourly_records == 24


def test_aggregate_hourly_empty():
    assert aggregate_hourly_to_daily([], "2025-01-01") is None


def test_aggregate_temperature():
    hourly = _make_hourly(24, temp=30.0)
    summary = aggregate_hourly_to_daily(hourly, "2025-01-01")
    assert summary.temperature_avg_c == pytest.approx(30.0)
    assert summary.temperature_max_c == pytest.approx(30.0)
    assert summary.temperature_min_c == pytest.approx(30.0)
