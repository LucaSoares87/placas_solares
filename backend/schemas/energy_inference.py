from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.domain.entities import EnergyStatus, InferenceMethod, RiskScore


# ── Schemas de Entrada ────────────────────────────────────────────────────────

class EnergyInferenceCreate(BaseModel):
    """Payload para registrar resultado de uma inferência energética."""

    uc_code: str = Field(..., min_length=2, max_length=20)
    transformer_id: str = Field(..., min_length=2, max_length=30)

    # Detecção FV
    has_fv: bool = False
    area_m2: Optional[float] = Field(None, ge=0.0, le=50_000.0)
    kwp_estimated: Optional[float] = Field(None, ge=0.0, le=10_000.0)

    # Estimativas energéticas
    generation_kw: Optional[float] = Field(None, ge=0.0, le=10_000.0)
    consumption_estimated_kw: float = Field(..., ge=0.0, le=100_000.0)
    injection_kw_min: Optional[float] = Field(None, ge=0.0)
    injection_kw_max: Optional[float] = Field(None, ge=0.0)

    # Classificação
    status: EnergyStatus = EnergyStatus.NORMAL
    confidence: float = Field(..., ge=0.0, le=1.0)
    operational_score: RiskScore = RiskScore.LOW
    inference_method: InferenceMethod = InferenceMethod.DEFAULT

    @field_validator("kwp_estimated", mode="before")
    @classmethod
    def kwp_requires_fv(cls, v, info):
        return v

    @model_validator(mode="after")
    def validate_fv_consistency(self):
        if self.has_fv:
            if self.kwp_estimated is None:
                raise ValueError("kwp_estimated é obrigatório quando has_fv=True.")
            if self.generation_kw is None:
                raise ValueError("generation_kw é obrigatório quando has_fv=True.")
        if self.injection_kw_min is not None and self.injection_kw_max is not None:
            if self.injection_kw_min > self.injection_kw_max:
                raise ValueError("injection_kw_min não pode ser maior que injection_kw_max.")
        return self


class EnergyInferenceUpdate(BaseModel):
    """Atualização parcial de inferência — usada em reprocessamentos."""

    has_fv: Optional[bool] = None
    area_m2: Optional[float] = Field(None, ge=0.0, le=50_000.0)
    kwp_estimated: Optional[float] = Field(None, ge=0.0, le=10_000.0)
    generation_kw: Optional[float] = Field(None, ge=0.0, le=10_000.0)
    consumption_estimated_kw: Optional[float] = Field(None, ge=0.0, le=100_000.0)
    injection_kw_min: Optional[float] = Field(None, ge=0.0)
    injection_kw_max: Optional[float] = Field(None, ge=0.0)
    status: Optional[EnergyStatus] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    operational_score: Optional[RiskScore] = None
    inference_method: Optional[InferenceMethod] = None


# ── Schemas de Saída ──────────────────────────────────────────────────────────

class EnergyInferenceResponse(BaseModel):
    """Resposta completa de uma inferência energética."""

    id: int
    uc_code: str
    transformer_id: str

    has_fv: bool
    area_m2: Optional[float]
    kwp_estimated: Optional[float]

    generation_kw: Optional[float]
    consumption_estimated_kw: float
    injection_kw_min: Optional[float]
    injection_kw_max: Optional[float]
    injection_kw_mid: Optional[float]   # Calculado pelo model property
    net_kw: float                        # Consumo líquido (consumo − geração)

    status: EnergyStatus
    confidence: float
    operational_score: RiskScore
    inference_method: InferenceMethod
    computed_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, obj) -> "EnergyInferenceResponse":
        return cls(
            id=obj.id,
            uc_code=obj.uc_code,
            transformer_id=obj.transformer_id,
            has_fv=obj.has_fv,
            area_m2=obj.area_m2,
            kwp_estimated=obj.kwp_estimated,
            generation_kw=obj.generation_kw,
            consumption_estimated_kw=obj.consumption_estimated_kw,
            injection_kw_min=obj.injection_kw_min,
            injection_kw_max=obj.injection_kw_max,
            injection_kw_mid=obj.injection_kw_mid,
            net_kw=obj.net_kw,
            status=EnergyStatus(obj.status),
            confidence=obj.confidence,
            operational_score=RiskScore(obj.operational_score),
            inference_method=InferenceMethod(obj.inference_method),
            computed_at=obj.computed_at,
        )


class EnergyInferenceSummary(BaseModel):
    """Versão compacta para exibição em painéis e listas."""

    uc_code: str
    has_fv: bool
    kwp_estimated: Optional[float]
    generation_kw: Optional[float]
    consumption_estimated_kw: float
    status: EnergyStatus
    confidence: float
    operational_score: RiskScore
    computed_at: datetime

    model_config = {"from_attributes": True}
