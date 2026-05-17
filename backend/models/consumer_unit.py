from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin


class ConsumerUnit(Base, TimestampMixin):
    __tablename__ = "consumer_units"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uc_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    transformer_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("transformers.transformer_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    profile: Mapped[str] = mapped_column(String(30), nullable=False, default="residential")
    is_telemetered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_gd: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    gd_installed_kwp: Mapped[float | None] = mapped_column(Float, nullable=True)
    inverter_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    panel_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)

    def __repr__(self) -> str:
        return f"<ConsumerUnit uc_code={self.uc_code} transformer={self.transformer_id}>"