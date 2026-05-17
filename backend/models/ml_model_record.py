"""
Model SQLAlchemy para versionamento de modelos ML.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class MlModelRecord(Base):
    __tablename__ = "ml_model_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    model_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Configuração e métricas (JSON)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Artefato binário (pickle do modelo)
    artifact: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
