from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.entities import BalanceStatus, RiskScore
from backend.models.base import Base


class TransformerBalance(Base):
    """
    Balanço energético consolidado de um transformador em um período.
    Calculado após a inferência de todas as UCs vinculadas.
    """

    __tablename__ = "transformer_balances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Identificação do período ──────────────────────────────────────────────
    transformer_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("transformers.transformer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # ── Medições e estimativas ────────────────────────────────────────────────
    measured_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_consumption_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_generation_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_injection_kwh: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Perdas e resíduo ─────────────────────────────────────────────────────
    technical_losses_kwh: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    residual_kwh: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Métricas de erro ─────────────────────────────────────────────────────
    absolute_error: Mapped[float] = mapped_column(Float, nullable=False)
    percentage_error: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Classificação ─────────────────────────────────────────────────────────
    balance_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=BalanceStatus.UNKNOWN.value
    )
    operational_score: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RiskScore.LOW.value
    )

    # ── Contadores ────────────────────────────────────────────────────────────
    uc_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    telemetered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gd_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<TransformerBalance transformer={self.transformer_id} "
            f"error={self.percentage_error:.2f}% status={self.balance_status}>"
        )

    @property
    def is_balanced(self) -> bool:
        from backend.domain.constants import BALANCE_TOLERANCE_PCT
        return abs(self.percentage_error) <= BALANCE_TOLERANCE_PCT

    @property
    def gd_penetration_rate(self) -> float:
        if self.uc_count == 0:
            return 0.0
        return round(self.gd_count / self.uc_count, 4)
