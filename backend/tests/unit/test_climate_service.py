"""
Testes unitários do ClimateService com dependências mockadas.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.climate_service import ClimateService
from backend.domain.climate import ClimateSource, HourlyClimateData


def _make_hourly_records(n: int = 24) -> list[HourlyClimateData]:
    return [
        HourlyClimateData(
            timestamp_utc=f"2025-01-01T{str(h).zfill(2)}:00:00Z",
            irradiance_wm2=600.0,
            temperature_c=28.0,
            wind_speed_ms=2.0,
            cloud_cover_pct=15.0,
            humidity_pct=70.0,
            source=ClimateSource.NASA_POWER,
            confidence=0.85,
        )
        for h in range(n)
    ]


def _make_service():
    session = MagicMock()
    session.commit = AsyncMock()
    redis = MagicMock()
    service = ClimateService(session, redis)
    service._repo = MagicMock()
    service._cache = MagicMock()
    service._inmet = MagicMock()
    service._nasa = MagicMock()
    service._pvgis = MagicMock()
    return service


@pytest.mark.asyncio
async def test_fetch_with_inmet_success():
    service = _make_service()
    records = _make_hourly_records(24)
    service._inmet.fetch_hourly = AsyncMock(return_value=records)

    result = await service._fetch_with_fallback(
        -8.034, -34.941, date(2025, 1, 1), date(2025, 1, 1)
    )
    assert len(result) == 24
    service._nasa.fetch_hourly.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_to_nasa_when_inmet_empty():
    service = _make_service()
    records = _make_hourly_records(24)
    service._inmet.fetch_hourly = AsyncMock(return_value=[])
    service._nasa.fetch_hourly = AsyncMock(return_value=records)

    result = await service._fetch_with_fallback(
        -8.034, -34.941, date(2025, 1, 1), date(2025, 1, 1)
    )
    assert len(result) == 24
    service._pvgis.fetch_hourly.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_to_pvgis_when_nasa_empty():
    service = _make_service()
    records = _make_hourly_records(24)
    service._inmet.fetch_hourly = AsyncMock(return_value=[])
    service._nasa.fetch_hourly = AsyncMock(return_value=[])
    service._pvgis.fetch_hourly = AsyncMock(return_value=records)

    result = await service._fetch_with_fallback(
        -8.034, -34.941, date(2025, 1, 1), date(2025, 1, 1)
    )
    assert len(result) == 24


@pytest.mark.asyncio
async def test_all_sources_fail():
    service = _make_service()
    service._inmet.fetch_hourly = AsyncMock(return_value=[])
    service._nasa.fetch_hourly = AsyncMock(return_value=[])
    service._pvgis.fetch_hourly = AsyncMock(return_value=[])

    result = await service._fetch_with_fallback(
        -8.034, -34.941, date(2025, 1, 1), date(2025, 1, 1)
    )
    assert result == []


@pytest.mark.asyncio
async def test_aggregate_by_day_groups_correctly():
    records_day1 = _make_hourly_records(24)
    records_day2 = [
        HourlyClimateData(
            timestamp_utc=f"2025-01-02T{str(h).zfill(2)}:00:00Z",
            irradiance_wm2=400.0,
            temperature_c=26.0,
            wind_speed_ms=1.5,
            cloud_cover_pct=30.0,
            humidity_pct=75.0,
            source=ClimateSource.NASA_POWER,
            confidence=0.85,
        )
        for h in range(12)
    ]

    summaries = ClimateService._aggregate_by_day(records_day1 + records_day2)
    assert len(summaries) == 2
    assert summaries[0].date == "2025-01-01"
    assert summaries[1].date == "2025-01-02"
    assert summaries[0].hourly_records == 24
    assert summaries[1].hourly_records == 12


@pytest.mark.asyncio
async def test_fetch_for_transformer_no_location():
    service = _make_service()
    service._repo.get_transformer_location = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="sem coordenadas"):
        await service.fetch_for_transformer(
            transformer_id="TR-FAKE",
            date_start=date(2025, 1, 1),
            date_end=date(2025, 1, 7),
        )


@pytest.mark.asyncio
async def test_cache_hit_returns_daily():
    from backend.schemas.climate import DailyClimateResponse
    from datetime import datetime, timezone

    service = _make_service()
    service._repo.get_transformer_location = AsyncMock(
        return_value=(-8.034, -34.941)
    )
    cached_daily = [
        {
            "date": "2025-01-01",
            "irradiance_daily_kwh_m2": 5.5,
            "temperature_avg_c": 28.0,
            "temperature_max_c": 32.0,
            "temperature_min_c": 24.0,
            "wind_speed_avg_ms": 2.5,
            "cloud_cover_avg_pct": 20.0,
            "humidity_avg_pct": 70.0,
            "source": "nasa_power",
            "hourly_records": 24,
            "confidence": 0.85,
        }
    ]
    service._cache.get_daily = AsyncMock(return_value=cached_daily)
    service._cache.get_correction = AsyncMock(return_value=None)
    service._repo.find_record = AsyncMock(return_value=None)
    service._repo.list_records_for_period = AsyncMock(return_value=[])

    service._inmet.fetch_hourly = AsyncMock(return_value=[])
    service._nasa.fetch_hourly = AsyncMock(return_value=[])
    service._pvgis.fetch_hourly = AsyncMock(return_value=[])

    result = await service.fetch_for_transformer(
        transformer_id="TR-001",
        date_start=date(2025, 1, 1),
        date_end=date(2025, 1, 1),
    )
    assert result.total_days == 1
    service._inmet.fetch_hourly.assert_not_called()
