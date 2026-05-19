from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from backend.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CalibrationHistory(Base):
    __tablename__ = "calibration_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transformer_id = Column(String(64), nullable=False, index=True)

    kwp_factor_old = Column(Float, nullable=False)
    kwp_factor_new = Column(Float, nullable=False)
    kwp_factor_delta = Column(Float, nullable=False)

    loss_factor_old = Column(Float, nullable=True)
    loss_factor_new = Column(Float, nullable=True)
    loss_factor_delta = Column(Float, nullable=True)

    samples_used = Column(Integer, nullable=False, default=0)
    mean_kwp_error_pct = Column(Float, nullable=True)
    mean_consumo_error_pct = Column(Float, nullable=True)
    converged = Column(Boolean, nullable=False, default=False)

    notes = Column(Text, nullable=True)
    cycle_metadata = Column(JSONB, nullable=True)

    executed_at = Column(DateTime, nullable=False, default=utc_now)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<CalibrationHistory transformer={self.transformer_id} "
            f"kwp_new={self.kwp_factor_new} converged={self.converged}>"
        )