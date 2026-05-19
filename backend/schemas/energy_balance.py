"""
Schemas Pydantic para o módulo de Balanço Energético.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Request
# ─────────────────────────────────────────────────────────────────────────────

class BalanceComputeRequest(BaseModel):
    """Solicita o cálculo de balanço para um transformador."""

    transformer_id: str = Field(..., min_length=2, max_length=30)
    period_start: datetime
    period_end: datetime
    force_recalculate: bool = Field(
        default=False,
        description="Recalcula mesmo que já exista balanço para o período.",
    )


class BatchBalanceRequest(BaseModel):
    """Solicita cálculo em lote para múltiplos transformadores."""

    transformer_ids: list[str] = Field(..., min_length=1, max_length=500)
    period_start: datetime
    period_end: datetime
    force_recalculate: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Response
# ─────────────────────────────────────────────────────────────────────────────

class ValidationIssueResponse(BaseModel):
    code: str
    message: str
    severity: str


class BalanceComputeResponse(BaseModel):
    """Resultado do cálculo de balanço de um transformador."""

    transformer_id: str
    period_start: datetime
    period_end: datetime

    measured_kwh: float
    estimated_consumption_kwh: float
    estimated_generation_kwh: float
    estimated_injection_kwh: float
    technical_losses_kwh: float
    residual_kwh: float

    absolute_error_kwh: float
    percentage_error: float

    balance_status: str
    operational_score: str

    uc_count: int
    telemetered_count: int
    gd_count: int

    confidence: float
    insufficient_data: bool

    validation_issues: list[ValidationIssueResponse] = Field(default_factory=list)

    computed_at: datetime

    model_config = {"from_attributes": True}


class BatchBalanceResponse(BaseModel):
    """Resultado do cálculo em lote."""

    total_requested: int
    total_computed: int
    total_skipped: int
    total_failed: int
    results: list[BalanceComputeResponse]
    failed_transformer_ids: list[str] = Field(default_factory=list)
    computed_at: datetime


class BalanceSummaryResponse(BaseModel):
    """Sumário estatístico de balanços em um período."""

    period_start: datetime
    period_end: datetime
    transformer_count: int

    avg_percentage_error: float
    max_percentage_error: float
    min_percentage_error: float

    balanced_count: int
    acceptable_count: int
    high_loss_count: int
    critical_count: int
    insufficient_data_count: int

    total_measured_kwh: float
    total_estimated_consumption_kwh: float
    total_estimated_generation_kwh: float
    total_technical_losses_kwh: float
    total_residual_kwh: float

    model_config = {"from_attributes": True}
