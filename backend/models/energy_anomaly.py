from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class EnergyAnomaly(Base):
    """Anomalia energética detectada durante a inferência ou balanço."""

    __tablename__ = "energy_anomalies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uc_code: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("consumer_units.uc_code", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transformer_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<EnergyAnomaly type={self.anomaly_type} "
            f"uc={self.uc_code} resolved={self.resolved}>"
        )
