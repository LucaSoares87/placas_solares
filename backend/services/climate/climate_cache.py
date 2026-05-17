"""
Camada de cache Redis para dados climáticos.
TTL configurável por fonte — evita requisições repetidas às APIs externas.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Optional

import structlog

from backend.core.config import settings
from backend.domain.climate import DailyClimateSummary, HourlyClimateData

logger = structlog.get_logger(__name__)

# TTLs em segundos
TTL_HOURLY = 60 * 60 * 6        # 6 horas
TTL_DAILY = 60 * 60 * 24        # 24 horas
TTL_CORRECTION = 60 * 60 * 12   # 12 horas


def _hourly_key(lat: float, lon: float, ds: date, de: date, source: str) -> str:
    return f"climate:hourly:{source}:{lat:.4f}:{lon:.4f}:{ds}:{de}"


def _daily_key(lat: float, lon: float, ds: date, de: date) -> str:
    return f"climate:daily:{lat:.4f}:{lon:.4f}:{ds}:{de}"


def _correction_key(transformer_id: str, ref_date: str) -> str:
    return f"climate:correction:{transformer_id}:{ref_date}"


class ClimateCache:
    def __init__(self, redis_client) -> None:
        self._redis = redis_client

    # ─────────────────────────────────────────────────────────────────────────
    # Dados horários
    # ─────────────────────────────────────────────────────────────────────────

    async def get_hourly(
        self,
        lat: float,
        lon: float,
        date_start: date,
        date_end: date,
        source: str,
    ) -> Optional[list[dict]]:
        key = _hourly_key(lat, lon, date_start, date_end, source)
        try:
            raw = await self._redis.get(key)
            if raw:
                logger.debug("climate.cache.hit", key=key)
                return json.loads(raw)
        except Exception as exc:
            logger.warning("climate.cache.get_failed", error=str(exc))
        return None

    async def set_hourly(
        self,
        lat: float,
        lon: float,
        date_start: date,
        date_end: date,
        source: str,
        records: list[dict],
    ) -> None:
        key = _hourly_key(lat, lon, date_start, date_end, source)
        try:
            await self._redis.setex(key, TTL_HOURLY, json.dumps(records))
            logger.debug("climate.cache.set", key=key, records=len(records))
        except Exception as exc:
            logger.warning("climate.cache.set_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    # Sumário diário
    # ─────────────────────────────────────────────────────────────────────────

    async def get_daily(
        self,
        lat: float,
        lon: float,
        date_start: date,
        date_end: date,
    ) -> Optional[list[dict]]:
        key = _daily_key(lat, lon, date_start, date_end)
        try:
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("climate.cache.get_failed", error=str(exc))
        return None

    async def set_daily(
        self,
        lat: float,
        lon: float,
        date_start: date,
        date_end: date,
        records: list[dict],
    ) -> None:
        key = _daily_key(lat, lon, date_start, date_end)
        try:
            await self._redis.setex(key, TTL_DAILY, json.dumps(records))
        except Exception as exc:
            logger.warning("climate.cache.set_failed", error=str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    # Fator de correção
    # ─────────────────────────────────────────────────────────────────────────

    async def get_correction(
        self, transformer_id: str, ref_date: str
    ) -> Optional[dict]:
        key = _correction_key(transformer_id, ref_date)
        try:
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("climate.cache.get_failed", error=str(exc))
        return None

    async def set_correction(
        self, transformer_id: str, ref_date: str, data: dict
    ) -> None:
        key = _correction_key(transformer_id, ref_date)
        try:
            await self._redis.setex(key, TTL_CORRECTION, json.dumps(data))
        except Exception as exc:
            logger.warning("climate.cache.set_failed", error=str(exc))

    async def invalidate_transformer(self, transformer_id: str) -> None:
        """Remove todos os caches de correção de um transformador."""
        try:
            pattern = f"climate:correction:{transformer_id}:*"
            keys = await self._redis.keys(pattern)
            if keys:
                await self._redis.delete(*keys)
                logger.info(
                    "climate.cache.invalidated",
                    transformer_id=transformer_id,
                    keys_removed=len(keys),
                )
        except Exception as exc:
            logger.warning("climate.cache.invalidate_failed", error=str(exc))
