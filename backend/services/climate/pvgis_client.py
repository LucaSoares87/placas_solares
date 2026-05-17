"""
Cliente HTTP para o PVGIS (Photovoltaic Geographical Information System).
Fornece irradiância de alta qualidade e dados de geração FV — JRC/EU.
Documentação: https://joint-research-centre.ec.europa.eu/pvgis-photovoltaic-geographical-information-system
"""

from __future__ import annotations

from datetime import date

import httpx
import structlog

from backend.domain.climate import ClimateSource, HourlyClimateData

logger = structlog.get_logger(__name__)

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_2/seriescalc"


class PvgisClient:
    """
    Cliente para a API PVGIS série temporal horária.
    Fonte preferencial para cálculo de geração FV — será intensamente usado no Ato 7.
    """

    def __init__(self, timeout: float = 60.0) -> None:
        self._timeout = timeout

    async def fetch_hourly(
        self,
        latitude: float,
        longitude: float,
        date_start: date,
        date_end: date,
        kwp: float = 1.0,
        loss_pct: float = 14.0,
    ) -> list[HourlyClimateData]:
        """
        Busca série temporal horária do PVGIS.
        kwp e loss_pct são usados para estimar geração — serão aproveitados no Ato 7.
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "startyear": date_start.year,
            "endyear": date_end.year,
            "pvcalculation": 1,
            "peakpower": kwp,
            "loss": loss_pct,
            "outputformat": "json",
            "optimalangles": 1,
            "components": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(PVGIS_URL, params=params)
                response.raise_for_status()
                data = response.json()

            return self._parse(data)
        except Exception as exc:
            logger.error(
                "pvgis.fetch_failed",
                error=str(exc),
                lat=latitude,
                lon=longitude,
            )
            return []

    def _parse(self, data: dict) -> list[HourlyClimateData]:
        try:
            hourly = data["outputs"]["hourly"]
            records: list[HourlyClimateData] = []

            for row in hourly:
                # time: "20160101:0000"
                raw_time = row.get("time", "")
                if len(raw_time) < 13:
                    continue
                ts = (
                    f"{raw_time[:4]}-{raw_time[4:6]}-{raw_time[6:8]}"
                    f"T{raw_time[9:11]}:00:00Z"
                )
                irr = float(row.get("G(i)", 0.0) or 0.0)
                temp = float(row.get("T2m", 25.0) or 25.0)
                wind = float(row.get("WS10m", 0.0) or 0.0)

                records.append(HourlyClimateData(
                    timestamp_utc=ts,
                    irradiance_wm2=max(0.0, irr),
                    temperature_c=temp,
                    wind_speed_ms=max(0.0, wind),
                    cloud_cover_pct=0.0,
                    humidity_pct=50.0,
                    source=ClimateSource.PVGIS,
                    confidence=0.92,
                ))

            return sorted(records, key=lambda r: r.timestamp_utc)
        except (KeyError, TypeError) as exc:
            logger.error("pvgis.parse_failed", error=str(exc))
            return []
