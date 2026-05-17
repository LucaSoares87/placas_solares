from typing import Optional

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models.base_model import TimestampMixin


class Transformer(Base, TimestampMixin):
    __tablename__ = "transformers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transformer_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    rated_kva: Mapped[float] = mapped_column(Float, nullable=False)
    uc_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gd_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    substation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    feeder: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    def __repr__(self) -> str:
        return f"<Transformer id={self.transformer_id} rated_kva={self.rated_kva}>"