"""
Schemas Pydantic para o módulo climático.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request
# ─────────────────────────────────────────────────────────────────────────────

class ClimateDataRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    date_start: date
    date_end: date
    force_refresh: bool = Field(
        default=False,
        description="Ignora cache e busca dados frescos nas fontes.",
    )


class TransformerClimateRequest(BaseModel):
    transformer_id: str = Field(..., min_length=2, max_length=30)
    date_start: date
    date_end: date
    force_refresh: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Response — horário
# ─────────────────────────────────────────────────────────────────────────────

class HourlyClimateResponse(BaseModel):
    timestamp_utc: str
    irradiance_wm2: float
    temperature_c: float
    wind_speed_ms: float
    cloud_cover_pct: float
    humidity_pct: float
    source: str
    confidence: float

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Response — diário
# ─────────────────────────────────────────────────────────────────────────────

class DailyClimateResponse(BaseModel):
    date: str
    irradiance_daily_kwh_m2: float
    temperature_avg_c: float
    temperature_max_c: float
    temperature_min_c: float
    wind_speed_avg_ms: float
    cloud_cover_avg_pct: float
    humidity_avg_pct: float
    source: str
    hourly_records: int
    confidence: float

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Response — fator de correção
# ─────────────────────────────────────────────────────────────────────────────

class ClimateCorrectionResponse(BaseModel):
    transformer_id: str
    date: str
    irradiance_factor: float
    temperature_factor: float
    cloud_factor: float
    composite_factor: float
    confidence: float
    source: str


# ─────────────────────────────────────────────────────────────────────────────
# Response — consolidado por transformador
# ─────────────────────────────────────────────────────────────────────────────

class TransformerClimateResponse(BaseModel):
    transformer_id: str
    latitude: float
    longitude: float
    date_start: str
    date_end: str
    daily_records: list[DailyClimateResponse]
    correction_factor: Optional[ClimateCorrectionResponse] = None
    total_days: int
    avg_irradiance_kwh_m2: float
    avg_temperature_c: float
    source: str
    fetched_at: datetime

    model_config = {"from_attributes": True}
