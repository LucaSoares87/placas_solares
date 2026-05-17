"""
Cliente HTTP para a NASA POWER API.
Fonte primária de dados de irradiância solar — cobertura global.
Documentação: https://power.larc.nasa.gov/api/
"""

from __future__ import annotations

from datetime import date

import httpx
import structlog

from backend.domain.climate import ClimateSource, HourlyClimateData

logger = structlog.get_logger(__name__)

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"

NASA_PARAMS = ",".join([
    "ALLSKY_SFC_SW_DWN",   # Irradiância global horizontal (W/m²)
    "T2M",                  # Temperatura do ar a 2m (°C)
    "WS2M",                 # Velocidade do vento a 2m (m/s)
    "RH2M",                 # Umidade relativa (%)
    "CLOUD_AMT",            # Cobertura de nuvens (%)
])


class NasaPowerClient:
    """
    Cliente para a NASA POWER Hourly API.
    Cobertura global — usado como fallback quando INMET não tem dados.
    """

    def __init__(self, timeout: float = 60.0) -> None:
        self._timeout = timeout

    async def fetch_hourly(
        self,
        latitude: float,
        longitude: float,
        date_start: date,
        date_end: date,
    ) -> list[HourlyClimateData]:
        params = {
            "parameters": NASA_PARAMS,
            "community": "RE",
            "longitude": longitude,
            "latitude": latitude,
            "start": date_start.strftime("%Y%m%d"),
            "end": date_end.strftime("%Y%m%d"),
            "format": "JSON",
            "header": "false",
            "time-standard": "UTC",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(NASA_POWER_URL, params=params)
                response.raise_for_status()
                data = response.json()

            return self._parse(data)
        except Exception as exc:
            logger.error(
                "nasa_power.fetch_failed",
                error=str(exc),
                lat=latitude,
                lon=longitude,
            )
            return []

    def _parse(self, data: dict) -> list[HourlyClimateData]:
        try:
            props = data["properties"]["parameter"]
            irr_map = props.get("ALLSKY_SFC_SW_DWN", {})
            temp_map = props.get("T2M", {})
            wind_map = props.get("WS2M", {})
            rh_map = props.get("RH2M", {})
            cloud_map = props.get("CLOUD_AMT", {})

            records: list[HourlyClimateData] = []
            for key in irr_map:
                # key: "YYYYMMDDHH"
                if len(key) < 10:
                    continue
                ts = (
                    f"{key[:4]}-{key[4:6]}-{key[6:8]}"
                    f"T{key[8:10]}:00:00Z"
                )
                irr = float(irr_map.get(key, 0.0) or 0.0)
                temp = float(temp_map.get(key, 25.0) or 25.0)
                wind = float(wind_map.get(key, 0.0) or 0.0)
                rh = float(rh_map.get(key, 50.0) or 50.0)
                cloud = float(cloud_map.get(key, 0.0) or 0.0)

                records.append(HourlyClimateData(
                    timestamp_utc=ts,
                    irradiance_wm2=max(0.0, irr),
                    temperature_c=temp,
                    wind_speed_ms=max(0.0, wind),
                    cloud_cover_pct=max(0.0, min(cloud, 100.0)),
                    humidity_pct=max(0.0, min(rh, 100.0)),
                    source=ClimateSource.NASA_POWER,
                    confidence=0.85,
                ))

            return sorted(records, key=lambda r: r.timestamp_utc)
        except (KeyError, TypeError) as exc:
            logger.error("nasa_power.parse_failed", error=str(exc))
            return []
