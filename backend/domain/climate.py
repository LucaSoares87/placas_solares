"""
Regras de domínio puras para dados climáticos.
Sem dependências externas — apenas lógica física.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class ClimateSource(str, Enum):
    INMET = "inmet"
    NASA_POWER = "nasa_power"
    PVGIS = "pvgis"
    COMPOSITE = "composite"


class CloudCoverLevel(str, Enum):
    CLEAR = "clear"           # 0–25%
    PARTLY_CLOUDY = "partly_cloudy"  # 25–50%
    MOSTLY_CLOUDY = "mostly_cloudy"  # 50–75%
    OVERCAST = "overcast"     # 75–100%


# ─────────────────────────────────────────────────────────────────────────────
# Dados climáticos horários normalizados
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HourlyClimateData:
    """Dados climáticos normalizados para uma hora específica."""

    timestamp_utc: str                    # ISO 8601
    irradiance_wm2: float                 # Irradiância global horizontal (W/m²)
    temperature_c: float                  # Temperatura do ar (°C)
    wind_speed_ms: float                  # Velocidade do vento (m/s)
    cloud_cover_pct: float                # Cobertura de nuvens (%)
    humidity_pct: float                   # Umidade relativa (%)
    source: ClimateSource
    confidence: float = 1.0              # 0.0 a 1.0


@dataclass
class DailyClimateSummary:
    """Sumário diário de dados climáticos."""

    date: str                             # YYYY-MM-DD
    irradiance_daily_kwh_m2: float        # Irradiação diária (kWh/m²)
    temperature_avg_c: float
    temperature_max_c: float
    temperature_min_c: float
    wind_speed_avg_ms: float
    cloud_cover_avg_pct: float
    humidity_avg_pct: float
    source: ClimateSource
    hourly_records: int = 0
    confidence: float = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Fator de correção climática
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ClimateCorrection:
    """
    Fator de correção climática a ser aplicado ao balanço energético.
    Representa o desvio esperado em relação a condições de referência (STC).
    """

    irradiance_factor: float   # razão irradiância_real / irradiância_stc
    temperature_factor: float  # penalidade térmica dos módulos FV
    cloud_factor: float        # fator de atenuação por nebulosidade
    composite_factor: float    # produto final aplicável ao balanço
    confidence: float


# ─────────────────────────────────────────────────────────────────────────────
# Constantes físicas de referência
# ─────────────────────────────────────────────────────────────────────────────

STC_IRRADIANCE_WM2: float = 1000.0    # Condições STC (W/m²)
STC_TEMPERATURE_C: float = 25.0       # Temperatura de referência (°C)
TEMP_COEFFICIENT: float = -0.004      # Coeficiente de temperatura típico (%/°C)
MIN_IRRADIANCE_WM2: float = 50.0      # Abaixo disso, geração é insignificante


# ─────────────────────────────────────────────────────────────────────────────
# Funções de domínio puras
# ─────────────────────────────────────────────────────────────────────────────

def classify_cloud_cover(cloud_pct: float) -> CloudCoverLevel:
    if cloud_pct <= 25.0:
        return CloudCoverLevel.CLEAR
    if cloud_pct <= 50.0:
        return CloudCoverLevel.PARTLY_CLOUDY
    if cloud_pct <= 75.0:
        return CloudCoverLevel.MOSTLY_CLOUDY
    return CloudCoverLevel.OVERCAST


def compute_irradiance_factor(irradiance_wm2: float) -> float:
    """Razão entre irradiância real e condição STC."""
    if irradiance_wm2 < 0:
        return 0.0
    return round(min(irradiance_wm2 / STC_IRRADIANCE_WM2, 1.2), 4)


def compute_temperature_factor(temperature_c: float) -> float:
    """
    Fator de penalidade térmica para módulos FV.
    Acima de 25°C, a potência cai proporcionalmente ao coeficiente de temperatura.
    """
    delta = temperature_c - STC_TEMPERATURE_C
    factor = 1.0 + (TEMP_COEFFICIENT * delta)
    return round(max(0.5, min(factor, 1.05)), 4)


def compute_cloud_factor(cloud_pct: float) -> float:
    """
    Fator de atenuação por nebulosidade.
    Aplica redução não-linear baseada na cobertura de nuvens.
    """
    fraction = cloud_pct / 100.0
    factor = 1.0 - (fraction * 0.75)
    return round(max(0.1, factor), 4)


def compute_climate_correction(
    irradiance_wm2: float,
    temperature_c: float,
    cloud_cover_pct: float,
    source_confidence: float = 1.0,
) -> ClimateCorrection:
    """
    Calcula o fator de correção climática composto.

    Fórmula:
        composite = irradiance_factor × temperature_factor × cloud_factor
    """
    irr_factor = compute_irradiance_factor(irradiance_wm2)
    temp_factor = compute_temperature_factor(temperature_c)
    cloud_factor = compute_cloud_factor(cloud_cover_pct)

    composite = round(irr_factor * temp_factor * cloud_factor, 4)

    return ClimateCorrection(
        irradiance_factor=irr_factor,
        temperature_factor=temp_factor,
        cloud_factor=cloud_factor,
        composite_factor=composite,
        confidence=round(source_confidence, 4),
    )


def aggregate_hourly_to_daily(
    hourly: list[HourlyClimateData],
    date: str,
) -> Optional[DailyClimateSummary]:
    """Agrega registros horários em sumário diário."""
    if not hourly:
        return None

    n = len(hourly)
    irr_daily = sum(h.irradiance_wm2 for h in hourly) / 1000.0  # Wh → kWh/m²
    temp_avg = sum(h.temperature_c for h in hourly) / n
    temp_max = max(h.temperature_c for h in hourly)
    temp_min = min(h.temperature_c for h in hourly)
    wind_avg = sum(h.wind_speed_ms for h in hourly) / n
    cloud_avg = sum(h.cloud_cover_pct for h in hourly) / n
    humidity_avg = sum(h.humidity_pct for h in hourly) / n
    conf_avg = sum(h.confidence for h in hourly) / n

    sources = {h.source for h in hourly}
    source = ClimateSource.COMPOSITE if len(sources) > 1 else next(iter(sources))

    return DailyClimateSummary(
        date=date,
        irradiance_daily_kwh_m2=round(irr_daily, 4),
        temperature_avg_c=round(temp_avg, 4),
        temperature_max_c=round(temp_max, 4),
        temperature_min_c=round(temp_min, 4),
        wind_speed_avg_ms=round(wind_avg, 4),
        cloud_cover_avg_pct=round(cloud_avg, 4),
        humidity_avg_pct=round(humidity_avg, 4),
        source=source,
        hourly_records=n,
        confidence=round(conf_avg, 4),
    )
