"""
Cliente HTTP para a API do INMET (Instituto Nacional de Meteorologia).
Fornece dados de estações automáticas mais próximas às coordenadas.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Optional

import httpx
import structlog

from backend.core.config import settings
from backend.domain.climate import ClimateSource, HourlyClimateData

logger = structlog.get_logger(__name__)

INMET_BASE_URL = "https://apitempo.inmet.gov.br"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em km entre dois pontos geográficos."""
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class InmetClient:
    """
    Cliente para a API REST do INMET.
    Busca dados de estações automáticas e normaliza para HourlyClimateData.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout
        self._token = getattr(settings, "INMET_TOKEN", "")

    async def fetch_hourly(
        self,
        latitude: float,
        longitude: float,
        date_start: date,
        date_end: date,
    ) -> list[HourlyClimateData]:
        """
        Busca dados horários da estação INMET mais próxima.
        Retorna lista vazia em caso de falha (fallback para NASA POWER).
        """
        try:
            station_id = await self._find_nearest_station(latitude, longitude)
            if not station_id:
                logger.warning(
                    "inmet.no_station_found",
                    lat=latitude,
                    lon=longitude,
                )
                return []

            return await self._fetch_station_data(
                station_id, date_start, date_end
            )
        except Exception as exc:
            logger.error(
                "inmet.fetch_failed",
                error=str(exc),
                lat=latitude,
                lon=longitude,
            )
            return []

    async def _find_nearest_station(
        self, latitude: float, longitude: float
    ) -> Optional[str]:
        url = f"{INMET_BASE_URL}/estacoes/T"
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            stations = response.json()

        if not stations:
            return None

        nearest = min(
            stations,
            key=lambda s: _haversine_km(
                latitude,
                longitude,
                float(s.get("VL_LATITUDE", 0)),
                float(s.get("VL_LONGITUDE", 0)),
            ),
        )
        return nearest.get("CD_ESTACAO")

    async def _fetch_station_data(
        self,
        station_id: str,
        date_start: date,
        date_end: date,
    ) -> list[HourlyClimateData]:
        url = (
            f"{INMET_BASE_URL}/estacao/dados/{station_id}"
            f"/{date_start.strftime('%Y-%m-%d')}"
            f"/{date_end.strftime('%Y-%m-%d')}"
        )
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            records = response.json()

        return [self._normalize(r) for r in records if self._is_valid(r)]

    @staticmethod
    def _is_valid(record: dict) -> bool:
        return (
            record.get("DT_MEDICAO") is not None
            and record.get("HR_MEDICAO") is not None
        )

    @staticmethod
    def _normalize(record: dict) -> HourlyClimateData:
        date_str = record.get("DT_MEDICAO", "")
        hour_str = str(record.get("HR_MEDICAO", "0000")).zfill(4)
        timestamp = f"{date_str}T{hour_str[:2]}:{hour_str[2:]}:00Z"

        irradiance = float(record.get("RAD_GLO", 0.0) or 0.0)
        temp = float(record.get("TEM_INS", 25.0) or 25.0)
        wind = float(record.get("VEN_VEL", 0.0) or 0.0)
        humidity = float(record.get("UMD_INS", 50.0) or 50.0)

        return HourlyClimateData(
            timestamp_utc=timestamp,
            irradiance_wm2=max(0.0, irradiance),
            temperature_c=temp,
            wind_speed_ms=max(0.0, wind),
            cloud_cover_pct=max(0.0, min(100.0 - humidity * 0.5, 100.0)),
            humidity_pct=max(0.0, min(humidity, 100.0)),
            source=ClimateSource.INMET,
            confidence=0.9,
        )
