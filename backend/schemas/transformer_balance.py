from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from backend.domain.entities import BalanceStatus, RiskScore


class TransformerBalanceCreate(BaseModel):
    """Payload de entrada para registrar um balanço calculado."""

    transformer_id: str = Field(..., min_length=2, max_length=30)
    period_start: datetime
    period_end: datetime

    measured_kwh: float = Field(..., ge=0.0)
    estimated_consumption_kwh: float = Field(..., ge=0.0)
    estimated_generation_kwh: float = Field(..., ge=0.0)
    estimated_injection_kwh: float = Field(..., ge=0.0)
    technical_losses_kwh: float = Field(default=0.0, ge=0.0)
    residual_kwh: float

    absolute_error: float = Field(..., ge=0.0)
    percentage_error: float

    balance_status: BalanceStatus = BalanceStatus.UNKNOWN
    operational_score: RiskScore = RiskScore.LOW

    uc_count: int = Field(..., ge=0)
    telemetered_count: int = Field(..., ge=0)
    gd_count: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_start >= self.period_end:
            raise ValueError("period_start deve ser anterior a period_end.")
        if self.telemetered_count > self.uc_count:
            raise ValueError("telemetered_count não pode ser maior que uc_count.")
        if self.gd_count > self.uc_count:
            raise ValueError("gd_count não pode ser maior que uc_count.")
        return self


class TransformerBalanceResponse(BaseModel):
    """Resposta completa de balanço energético."""

    id: int
    transformer_id: str
    period_start: datetime
    period_end: datetime

    measured_kwh: float
    estimated_consumption_kwh: float
    estimated_generation_kwh: float
    estimated_injection_kwh: float
    technical_losses_kwh: float
    residual_kwh: float

    absolute_error: float
    percentage_error: float

    balance_status: BalanceStatus
    operational_score: RiskScore

    uc_count: int
    telemetered_count: int
    gd_count: int
    gd_penetration_rate: Optional[float]

    computed_at: datetime
    is_balanced: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, obj) -> "TransformerBalanceResponse":
        return cls(
            id=obj.id,
            transformer_id=obj.transformer_id,
            period_start=obj.period_start,
            period_end=obj.period_end,
            measured_kwh=obj.measured_kwh,
            estimated_consumption_kwh=obj.estimated_consumption_kwh,
            estimated_generation_kwh=obj.estimated_generation_kwh,
            estimated_injection_kwh=obj.estimated_injection_kwh,
            technical_losses_kwh=obj.technical_losses_kwh,
            residual_kwh=obj.residual_kwh,
            absolute_error=obj.absolute_error,
            percentage_error=obj.percentage_error,
            balance_status=BalanceStatus(obj.balance_status),
            operational_score=RiskScore(obj.operational_score),
            uc_count=obj.uc_count,
            telemetered_count=obj.telemetered_count,
            gd_count=obj.gd_count,
            gd_penetration_rate=obj.gd_penetration_rate,
            computed_at=obj.computed_at,
            is_balanced=obj.is_balanced,
        )


class TransformerBalanceSummary(BaseModel):
    """Versão compacta para dashboards."""

    transformer_id: str
    period_start: datetime
    period_end: datetime
    percentage_error: float
    balance_status: BalanceStatus
    operational_score: RiskScore
    gd_penetration_rate: Optional[float]
    computed_at: datetime

    model_config = {"from_attributes": True}
