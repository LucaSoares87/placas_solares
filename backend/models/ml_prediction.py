"""
Model SQLAlchemy para predições persistidas.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class MlPrediction(Base):
    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transformer_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    ref_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(40), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    ci_lower: Mapped[float] = mapped_column(Float, nullable=False)
    ci_upper: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(60), nullable=False)
    feature_contributions: Mapped[dict] = mapped_column(JSON, nullable=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    actual_value: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
