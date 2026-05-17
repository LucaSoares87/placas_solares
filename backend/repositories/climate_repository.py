"""
Repositório para persistência de dados climáticos e fatores de correção.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.climate_record import ClimateRecord
from backend.models.transformer import Transformer

logger = structlog.get_logger(__name__)


class ClimateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_transformer_location(
        self, transformer_id: str
    ) -> Optional[tuple[float, float]]:
        """Retorna (latitude, longitude) do transformador."""
        t = await self._session.scalar(
            select(Transformer).where(
                Transformer.transformer_id == transformer_id
            )
        )
        if not t:
            return None
        lat = getattr(t, "latitude", None)
        lon = getattr(t, "longitude", None)
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)

    async def find_record(
        self,
        latitude: float,
        longitude: float,
        ref_date: date,
    ) -> Optional[ClimateRecord]:
        return await self._session.scalar(
            select(ClimateRecord).where(
                and_(
                    ClimateRecord.latitude == round(latitude, 4),
                    ClimateRecord.longitude == round(longitude, 4),
                    ClimateRecord.ref_date == ref_date,
                )
            )
        )

    async def upsert_record(
        self,
        latitude: float,
        longitude: float,
        ref_date: date,
        irradiance_daily_kwh_m2: float,
        temperature_avg_c: float,
        temperature_max_c: float,
        temperature_min_c: float,
        wind_speed_avg_ms: float,
        cloud_cover_avg_pct: float,
        humidity_avg_pct: float,
        source: str,
        hourly_records: int,
        confidence: float,
        irradiance_factor: float,
        temperature_factor: float,
        cloud_factor: float,
        composite_factor: float,
    ) -> ClimateRecord:
        existing = await self.find_record(latitude, longitude, ref_date)
        now = datetime.now(timezone.utc)

        if existing:
            existing.irradiance_daily_kwh_m2 = irradiance_daily_kwh_m2
            existing.temperature_avg_c = temperature_avg_c
            existing.temperature_max_c = temperature_max_c
            existing.temperature_min_c = temperature_min_c
            existing.wind_speed_avg_ms = wind_speed_avg_ms
            existing.cloud_cover_avg_pct = cloud_cover_avg_pct
            existing.humidity_avg_pct = humidity_avg_pct
            existing.source = source
            existing.hourly_records = hourly_records
            existing.confidence = confidence
            existing.irradiance_factor = irradiance_factor
            existing.temperature_factor = temperature_factor
            existing.cloud_factor = cloud_factor
            existing.composite_factor = composite_factor
            existing.updated_at = now
            await self._session.flush()
            return existing

        record = ClimateRecord(
            latitude=round(latitude, 4),
            longitude=round(longitude, 4),
            ref_date=ref_date,
            irradiance_daily_kwh_m2=irradiance_daily_kwh_m2,
            temperature_avg_c=temperature_avg_c,
            temperature_max_c=temperature_max_c,
            temperature_min_c=temperature_min_c,
            wind_speed_avg_ms=wind_speed_avg_ms,
            cloud_cover_avg_pct=cloud_cover_avg_pct,
            humidity_avg_pct=humidity_avg_pct,
            source=source,
            hourly_records=hourly_records,
            confidence=confidence,
            irradiance_factor=irradiance_factor,
            temperature_factor=temperature_factor,
            cloud_factor=cloud_factor,
            composite_factor=composite_factor,
            created_at=now,
            updated_at=now,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_records_for_period(
        self,
        latitude: float,
        longitude: float,
        date_start: date,
        date_end: date,
    ) -> list[ClimateRecord]:
        result = await self._session.execute(
            select(ClimateRecord)
            .where(
                and_(
                    ClimateRecord.latitude == round(latitude, 4),
                    ClimateRecord.longitude == round(longitude, 4),
                    ClimateRecord.ref_date >= date_start,
                    ClimateRecord.ref_date <= date_end,
                )
            )
            .order_by(ClimateRecord.ref_date)
        )
        return list(result.scalars().all())
