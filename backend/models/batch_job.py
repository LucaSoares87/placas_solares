"""
Rastreamento de execuções de jobs em lote para auditoria e reprocessamento.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Identificação do job
    job_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="batch_inference | telemetry_ingest | reprocess | alert_dispatch",
    )
    transformer_id: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    # Estado
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="pending | running | success | failed | cancelled",
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Métricas
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Resultado e erros
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<BatchJob id={self.job_id} type={self.job_type} "
            f"status={self.status} items={self.processed_items}/{self.total_items}>"
        )

    @property
    def success_rate(self) -> float:
        if self.total_items == 0:
            return 0.0
        return round(self.processed_items / self.total_items, 4)
