"""
Leitura telemetrada bruta enviada por medidores inteligentes ou SCADA.
Cada linha representa um snapshot pontual de uma UC ou transformador.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Identificação da origem
    source_id: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
        comment="uc_code ou transformer_id da origem da leitura",
    )
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uc",
        comment="'uc' ou 'transformer'",
    )

    # Timestamp da medição no campo
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Grandezas elétricas
    active_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    reactive_power_kvar: Mapped[float | None] = mapped_column(Float, nullable=True)
    voltage_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_factor: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Energia acumulada (bip/pulso do medidor)
    energy_kwh_import: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_kwh_export: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Metadados de qualidade
    quality_flag: Mapped[str] = mapped_column(
        String(10), nullable=False, default="ok",
        comment="ok | suspect | invalid",
    )
    raw_payload: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON original recebido para auditoria",
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<TelemetryReading source={self.source_id} "
            f"measured_at={self.measured_at} kw={self.active_power_kw}>"
        )
