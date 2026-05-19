"""
Service climático principal.

Responsabilidades:
  1. Estratégia de fonte: INMET → NASA POWER → PVGIS
  2. Agregação horária → diária
  3. Cálculo do fator de correção
  4. Cache Redis de dupla camada
  5. Persistência no banco
  6. Fornecimento do fator para o balanço energético
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.climate import (
    DailyClimateSummary,
    HourlyClimateData,
    aggregate_hourly_to_daily,
    compute_climate_correction,
)
from backend.repositories.climate_repository import ClimateRepository
from backend.schemas.climate import (
    ClimateCorrectionResponse,
    DailyClimateResponse,
    TransformerClimateResponse,
)
from backend.services.climate.climate_cache import ClimateCache
from backend.services.climate.inmet_client import InmetClient
from backend.services.climate.nasa_power_client import NasaPowerClient
from backend.services.climate.pvgis_client import PvgisClient

logger = structlog.get_logger(__name__)


class ClimateService:
    def __init__(
        self,
        session: AsyncSession,
        redis_client,
    ) -> None:
        self._session = session
        self._repo = ClimateRepository(session)
        self._cache = ClimateCache(redis_client)
        self._inmet = InmetClient()
        self._nasa = NasaPowerClient()
        self._pvgis = PvgisClient()

    # ─────────────────────────────────────────────────────────────────────────
    # Ponto de entrada principal por transformador
    # ─────────────────────────────────────────────────────────────────────────

    async def fetch_for_transformer(
        self,
        transformer_id: str,
        date_start: date,
        date_end: date,
        force_refresh: bool = False,
    ) -> TransformerClimateResponse:
        log = logger.bind(
            transformer_id=transformer_id,
            date_start=str(date_start),
            date_end=str(date_end),
        )

        location = await self._repo.get_transformer_location(transformer_id)
        if not location:
            raise ValueError(
                f"Transformador '{transformer_id}' sem coordenadas cadastradas."
            )

        latitude, longitude = location
        daily_records = await self.fetch_daily_summary(
            latitude=latitude,
            longitude=longitude,
            date_start=date_start,
            date_end=date_end,
            force_refresh=force_refresh,
        )

        correction = await self.get_correction_factor(
            transformer_id=transformer_id,
            latitude=latitude,
            longitude=longitude,
            ref_date=date_end,
            force_refresh=force_refresh,
        )

        avg_irr = (
            sum(r.irradiance_daily_kwh_m2 for r in daily_records) / len(daily_records)
            if daily_records
            else 0.0
        )
        avg_temp = (
            sum(r.temperature_avg_c for r in daily_records) / len(daily_records)
            if daily_records
            else 0.0
        )
        source = daily_records[0].source if daily_records else "unknown"

        log.info(
            "climate.transformer_fetched",
            days=len(daily_records),
            avg_irr=round(avg_irr, 3),
        )

        return TransformerClimateResponse(
            transformer_id=transformer_id,
            latitude=latitude,
            longitude=longitude,
            date_start=str(date_start),
            date_end=str(date_end),
            daily_records=daily_records,
            correction_factor=correction,
            total_days=len(daily_records),
            avg_irradiance_kwh_m2=round(avg_irr, 4),
            avg_temperature_c=round(avg_temp, 4),
            source=source,
            fetched_at=datetime.now(timezone.utc),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Sumário diário com estratégia de fonte
    # ─────────────────────────────────────────────────────────────────────────

    async def fetch_daily_summary(
        self,
        latitude: float,
        longitude: float,
        date_start: date,
        date_end: date,
        force_refresh: bool = False,
    ) -> list[DailyClimateResponse]:
        # Verificar cache
        if not force_refresh:
            cached = await self._cache.get_daily(
                latitude, longitude, date_start, date_end
            )
            if cached:
                return [DailyClimateResponse(**r) for r in cached]

        # Verificar banco
        db_records = await self._repo.list_records_for_period(
            latitude, longitude, date_start, date_end
        )
        expected_days = (date_end - date_start).days + 1
        if not force_refresh and len(db_records) >= expected_days:
            responses = [self._record_to_response(r) for r in db_records]
            await self._cache.set_daily(
                latitude, longitude, date_start, date_end,
                [r.model_dump(mode="json") for r in responses],
            )
            return responses

        # Buscar dados externos com estratégia de fallback
        hourly = await self._fetch_with_fallback(
            latitude, longitude, date_start, date_end
        )

        daily_summaries = self._aggregate_by_day(hourly)
        responses: list[DailyClimateResponse] = []

        for summary in daily_summaries:
            correction = compute_climate_correction(
                irradiance_wm2=summary.irradiance_daily_kwh_m2 * 1000.0 / 24.0,
                temperature_c=summary.temperature_avg_c,
                cloud_cover_pct=summary.cloud_cover_avg_pct,
                source_confidence=summary.confidence,
            )
            ref_date = date.fromisoformat(summary.date)
            await self._repo.upsert_record(
                latitude=latitude,
                longitude=longitude,
                ref_date=ref_date,
                irradiance_daily_kwh_m2=summary.irradiance_daily_kwh_m2,
                temperature_avg_c=summary.temperature_avg_c,
                temperature_max_c=summary.temperature_max_c,
                temperature_min_c=summary.temperature_min_c,
                wind_speed_avg_ms=summary.wind_speed_avg_ms,
                cloud_cover_avg_pct=summary.cloud_cover_avg_pct,
                humidity_avg_pct=summary.humidity_avg_pct,
                source=summary.source.value,
                hourly_records=summary.hourly_records,
                confidence=summary.confidence,
                irradiance_factor=correction.irradiance_factor,
                temperature_factor=correction.temperature_factor,
                cloud_factor=correction.cloud_factor,
                composite_factor=correction.composite_factor,
            )
            responses.append(DailyClimateResponse(
                date=summary.date,
                irradiance_daily_kwh_m2=summary.irradiance_daily_kwh_m2,
                temperature_avg_c=summary.temperature_avg_c,
                temperature_max_c=summary.temperature_max_c,
                temperature_min_c=summary.temperature_min_c,
                wind_speed_avg_ms=summary.wind_speed_avg_ms,
                cloud_cover_avg_pct=summary.cloud_cover_avg_pct,
                humidity_avg_pct=summary.humidity_avg_pct,
                source=summary.source.value,
                hourly_records=summary.hourly_records,
                confidence=summary.confidence,
            ))

        await self._session.commit()

        await self._cache.set_daily(
            latitude, longitude, date_start, date_end,
            [r.model_dump(mode="json") for r in responses],
        )
        return responses

    # ─────────────────────────────────────────────────────────────────────────
    # Fator de correção para transformador
    # ─────────────────────────────────────────────────────────────────────────

    async def get_correction_factor(
        self,
        transformer_id: str,
        latitude: float,
        longitude: float,
        ref_date: date,
        force_refresh: bool = False,
    ) -> Optional[ClimateCorrectionResponse]:
        ref_str = str(ref_date)

        if not force_refresh:
            cached = await self._cache.get_correction(transformer_id, ref_str)
            if cached:
                return ClimateCorrectionResponse(**cached)

        record = await self._repo.find_record(latitude, longitude, ref_date)
        if not record:
            return None

        response = ClimateCorrectionResponse(
            transformer_id=transformer_id,
            date=ref_str,
            irradiance_factor=record.irradiance_factor,
            temperature_factor=record.temperature_factor,
            cloud_factor=record.cloud_factor,
            composite_factor=record.composite_factor,
            confidence=record.confidence,
            source=record.source,
        )

        await self._cache.set_correction(
            transformer_id, ref_str, response.model_dump(mode="json")
        )
        return response

    # ─────────────────────────────────────────────────────────────────────────
    # Estratégia de fonte com fallback
    # ─────────────────────────────────────────────────────────────────────────

    async def _fetch_with_fallback(
        self,
        latitude: float,
        longitude: float,
        date_start: date,
        date_end: date,
    ) -> list[HourlyClimateData]:
        # 1. INMET (dados de estações nacionais — maior precisão local)
        data = await self._inmet.fetch_hourly(latitude, longitude, date_start, date_end)
        if data:
            logger.info("climate.source.inmet_success", records=len(data))
            return data

        # 2. NASA POWER (cobertura global, resolução espacial de 0.5°)
        data = await self._nasa.fetch_hourly(latitude, longitude, date_start, date_end)
        if data:
            logger.info("climate.source.nasa_power_success", records=len(data))
            return data

        # 3. PVGIS (European JRC — alta qualidade para irradiância FV)
        data = await self._pvgis.fetch_hourly(latitude, longitude, date_start, date_end)
        if data:
            logger.info("climate.source.pvgis_success", records=len(data))
            return data

        logger.error(
            "climate.all_sources_failed",
            lat=latitude,
            lon=longitude,
        )
        return []

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _aggregate_by_day(
        hourly: list[HourlyClimateData],
    ) -> list[DailyClimateSummary]:
        by_day: dict[str, list[HourlyClimateData]] = defaultdict(list)
        for record in hourly:
            day = record.timestamp_utc[:10]  # YYYY-MM-DD
            by_day[day].append(record)

        summaries: list[DailyClimateSummary] = []
        for day_str in sorted(by_day.keys()):
            summary = aggregate_hourly_to_daily(by_day[day_str], day_str)
            if summary:
                summaries.append(summary)
        return summaries

    @staticmethod
    def _record_to_response(record) -> DailyClimateResponse:
        return DailyClimateResponse(
            date=str(record.ref_date),
            irradiance_daily_kwh_m2=record.irradiance_daily_kwh_m2,
            temperature_avg_c=record.temperature_avg_c,
            temperature_max_c=record.temperature_max_c,
            temperature_min_c=record.temperature_min_c,
            wind_speed_avg_ms=record.wind_speed_avg_ms,
            cloud_cover_avg_pct=record.cloud_cover_avg_pct,
            humidity_avg_pct=record.humidity_avg_pct,
            source=record.source,
            hourly_records=record.hourly_records,
            confidence=record.confidence,
        )
