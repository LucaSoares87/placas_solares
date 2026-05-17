from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Boolean, Integer,
    DateTime, Text, Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from backend.models.base import Base


class DashboardSnapshot(Base):
    """
    Snapshot consolidado por transformador, gerado periodicamente.
    Serve como cache materializado para o dashboard executivo,
    evitando queries pesadas em tempo real.
    """
    __tablename__ = "dashboard_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transformer_id = Column(String(64), nullable=False, index=True)
    reference_period = Column(String(32), nullable=False)

    # KPIs energéticos
    total_ucs = Column(Integer, nullable=False, default=0)
    total_ucs_fv = Column(Integer, nullable=False, default=0)
    cobertura_fv_pct = Column(Float, nullable=True)
    kwp_total_estimado = Column(Float, nullable=True)
    area_total_m2 = Column(Float, nullable=True)
    geracao_total_kwh = Column(Float, nullable=True)
    consumo_total_kwh = Column(Float, nullable=True)
    injecao_total_kwh = Column(Float, nullable=True)
    balanco_estimado_kwh = Column(Float, nullable=True)
    balanco_real_kwh = Column(Float, nullable=True)
    erro_balanco_pct = Column(Float, nullable=True)

    # Calibração
    kwp_factor_atual = Column(Float, nullable=True)
    loss_factor_atual = Column(Float, nullable=True)
    modelo_convergido = Column(Boolean, nullable=False, default=False)

    # Risco e anomalias
    score_operacional = Column(String(32), nullable=False, default="baixo_risco")
    total_anomalias_ativas = Column(Integer, nullable=False, default=0)
    total_inspecoes_pendentes = Column(Integer, nullable=False, default=0)
    confianca_media_deteccao = Column(Float, nullable=True)

    # Metadados
    gerado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    valido_ate = Column(DateTime, nullable=True)
    snapshot_metadata = Column(JSONB, nullable=True)

    __table_args__ = (
        Index(
            "ix_snapshot_transformer_period",
            "transformer_id",
            "reference_period",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DashboardSnapshot transformer={self.transformer_id} "
            f"period={self.reference_period} score={self.score_operacional}>"
        )


class AlertRecord(Base):
    """
    Registro de alertas operacionais disparados por thresholds.
    Permite rastreabilidade, resolução e histórico de notificações.
    """
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transformer_id = Column(String(64), nullable=False, index=True)
    uc_code = Column(String(64), nullable=True, index=True)

    alert_type = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=False, default="medio")
    title = Column(String(256), nullable=False)
    message = Column(Text, nullable=False)
    threshold_value = Column(Float, nullable=True)
    observed_value = Column(Float, nullable=True)

    status = Column(String(32), nullable=False, default="aberto")
    acknowledged_by = Column(String(64), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    alert_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_alert_transformer_status", "transformer_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<AlertRecord transformer={self.transformer_id} "
            f"type={self.alert_type} severity={self.severity}>"
        )
