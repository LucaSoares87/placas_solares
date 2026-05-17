from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.entities import EnergyStatus, InferenceMethod, RiskScore
from backend.models.base import Base


class EnergyInference(Base):
    """
    Resultado de uma inferência energética pontual para uma UC.
    Gerado pelo motor de inferência a cada ciclo de processamento.
    """

    __tablename__ = "energy_inferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Identificação ─────────────────────────────────────────────────────────
    uc_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("consumer_units.uc_code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transformer_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # ── Resultado da detecção FV ──────────────────────────────────────────────
    has_fv: Mapped[bool] = mapped_column(default=False, nullable=False)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    kwp_estimated: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Estimativas energéticas ───────────────────────────────────────────────
    generation_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    consumption_estimated_kw: Mapped[float] = mapped_column(Float, nullable=False)
    injection_kw_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    injection_kw_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Classificação e confiança ─────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=EnergyStatus.NORMAL.value
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    operational_score: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RiskScore.LOW.value
    )
    inference_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default=InferenceMethod.DEFAULT.value
    )

    # ── Metadados ─────────────────────────────────────────────────────────────
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<EnergyInference uc={self.uc_code} "
            f"status={self.status} confidence={self.confidence:.2f}>"
        )

    @property
    def injection_kw_mid(self) -> float | None:
        if self.injection_kw_min is not None and self.injection_kw_max is not None:
            return round((self.injection_kw_min + self.injection_kw_max) / 2, 4)
        return None

    @property
    def net_kw(self) -> float:
        """Potência líquida: consumo − geração."""
        gen = self.generation_kw or 0.0
        return round(self.consumption_estimated_kw - gen, 4)
