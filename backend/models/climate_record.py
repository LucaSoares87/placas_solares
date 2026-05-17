"""
Model SQLAlchemy para registros climáticos diários.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ClimateRecord(Base):
    __tablename__ = "climate_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Localização (indexada para buscas por proximidade)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    ref_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Dados climáticos diários
    irradiance_daily_kwh_m2: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_avg_c: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_max_c: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_min_c: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed_avg_ms: Mapped[float] = mapped_column(Float, nullable=False)
    cloud_cover_avg_pct: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_avg_pct: Mapped[float] = mapped_column(Float, nullable=False)

    # Fonte e qualidade
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    hourly_records: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Fatores de correção calculados (prontos para Ato 7)
    irradiance_factor: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_factor: Mapped[float] = mapped_column(Float, nullable=False)
    cloud_factor: Mapped[float] = mapped_column(Float, nullable=False)
    composite_factor: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
