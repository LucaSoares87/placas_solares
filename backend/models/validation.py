from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from backend.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ValidationRecord(Base):
    __tablename__ = "validation_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transformer_id = Column(String(64), nullable=False, index=True)
    uc_code = Column(String(64), nullable=True, index=True)
    reference_period = Column(String(32), nullable=False)

    consumo_estimado_kwh = Column(Float, nullable=False)
    geracao_estimada_kwh = Column(Float, nullable=False)
    injecao_estimada_kwh = Column(Float, nullable=False)
    balanco_estimado_kwh = Column(Float, nullable=False)

    consumo_real_kwh = Column(Float, nullable=True)
    geracao_real_kwh = Column(Float, nullable=True)
    balanco_real_kwh = Column(Float, nullable=True)

    erro_absoluto_kwh = Column(Float, nullable=True)
    erro_percentual_pct = Column(Float, nullable=True)
    desvio_sazonal_pct = Column(Float, nullable=True)

    score_operacional = Column(String(32), nullable=False, default="baixo_risco")
    status_validacao = Column(String(32), nullable=False, default="pendente")
    observacoes = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_validation_transformer_period", "transformer_id", "reference_period"),
    )

    def __repr__(self) -> str:
        return (
            f"<ValidationRecord transformer={self.transformer_id} "
            f"period={self.reference_period} erro={self.erro_percentual_pct}%>"
        )


class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uc_code = Column(String(64), nullable=False, index=True)
    transformer_id = Column(String(64), nullable=False, index=True)

    is_anomaly = Column(Boolean, nullable=False, default=False)
    consensus = Column(Boolean, nullable=False, default=False)
    isolation_forest_score = Column(Float, nullable=True)
    one_class_svm_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    recommendation = Column(String(64), nullable=True)

    features_json = Column(JSONB, nullable=True)
    detected_at = Column(DateTime, default=utc_now, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(64), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_anomaly_transformer_uc", "transformer_id", "uc_code"),
    )

    def __repr__(self) -> str:
        return (
            f"<AnomalyRecord uc={self.uc_code} "
            f"anomaly={self.is_anomaly} score={self.final_score}>"
        )