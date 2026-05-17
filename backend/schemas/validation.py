from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class FeedbackRecordInput(BaseModel):
    uc_code: str
    timestamp: datetime
    kwp_estimated: float = Field(..., ge=0)
    kwp_real: Optional[float] = Field(None, ge=0)
    consumo_estimado_kwh: float = Field(..., ge=0)
    consumo_real_kwh: Optional[float] = Field(None, ge=0)
    geracao_estimada_kwh: float = Field(..., ge=0)
    geracao_real_kwh: Optional[float] = Field(None, ge=0)
    area_m2: float = Field(..., gt=0)
    confianca: float = Field(..., ge=0, le=1)
    source: str = "telemedido"


class ValidationRequest(BaseModel):
    transformer_id: str = Field(..., description="ID do transformador")
    reference_period: str = Field(..., description="Ex: 2025-05, 2025-W20")
    consumo_estimado_kwh: float = Field(..., ge=0)
    geracao_estimada_kwh: float = Field(..., ge=0)
    injecao_estimada_kwh: float = Field(..., ge=0)
    balanco_estimado_kwh: float
    consumo_real_kwh: Optional[float] = Field(None, ge=0)
    geracao_real_kwh: Optional[float] = Field(None, ge=0)
    balanco_real_kwh: Optional[float] = None
    balanco_real_kwh_sazonal: Optional[float] = None
    confianca_media: float = Field(0.5, ge=0, le=1)

    @field_validator("transformer_id")
    @classmethod
    def transformer_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("transformer_id não pode ser vazio")
        return v.strip()


class ValidationResponse(BaseModel):
    id: int
    transformer_id: str
    reference_period: str
    consumo_estimado_kwh: float
    geracao_estimada_kwh: float
    balanco_estimado_kwh: float
    balanco_real_kwh: Optional[float]
    erro_absoluto_kwh: Optional[float]
    erro_percentual_pct: Optional[float]
    desvio_sazonal_pct: Optional[float]
    score_operacional: str
    status_validacao: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnomalyDetectionRequest(BaseModel):
    uc_code: str
    transformer_id: str
    consumo_estimado_kwh: float = Field(..., ge=0)
    geracao_estimada_kwh: float = Field(..., ge=0)
    injecao_estimada_kwh: float = Field(..., ge=0)
    erro_balanco_pct: float = Field(..., ge=0)
    kwp_estimado: float = Field(..., ge=0)
    area_m2: float = Field(..., gt=0)
    confianca_deteccao: float = Field(..., ge=0, le=1)


class AnomalyDetectionResponse(BaseModel):
    uc_code: str
    transformer_id: str
    is_anomaly: bool
    consensus: bool
    final_score: float
    recommendation: str
    isolation_forest_score: float
    one_class_svm_score: float


class CalibrationRequest(BaseModel):
    transformer_id: str
    feedback_records: list[FeedbackRecordInput] = Field(..., min_length=1)
    energy_injected_kwh: Optional[float] = Field(None, ge=0)
    energy_measured_kwh: Optional[float] = Field(None, ge=0)


class CalibrationResponse(BaseModel):
    transformer_id: str
    executed_at: datetime
    kwp_factor_old: float
    kwp_factor_new: float
    loss_factor_old: float
    loss_factor_new: float
    samples_used: int
    mean_kwp_error_pct: float
    converged: bool
    notes: list[str]


class ValidationHistoryResponse(BaseModel):
    transformer_id: str
    total_records: int
    records: list[ValidationResponse]


class CalibrationHistoryResponse(BaseModel):
    transformer_id: str
    total_cycles: int
    latest_kwp_factor: Optional[float]
    latest_loss_factor: Optional[float]
    converged: bool
    history: list[dict]
