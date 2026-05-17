from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.domain.entities import RiskScore


class TransformerCreate(BaseModel):
    transformer_id: str = Field(..., min_length=2, max_length=30)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    rated_kva: float = Field(..., gt=0.0, le=5000.0)
    substation: Optional[str] = Field(None, max_length=50)
    feeder: Optional[str] = Field(None, max_length=50)


class TransformerBase(BaseModel):
    transformer_id: str = Field(..., min_length=1, max_length=30)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    rated_kva: float = Field(..., gt=0)
    substation: Optional[str] = None
    feeder: Optional[str] = None


class TransformerUpdate(BaseModel):
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    rated_kva: Optional[float] = Field(None, gt=0.0, le=5000.0)
    substation: Optional[str] = Field(None, max_length=50)
    feeder: Optional[str] = Field(None, max_length=50)

class TransformerRead(BaseModel):
    id: int
    transformer_id: str
    latitude: float
    longitude: float
    rated_kva: float
    uc_count: int
    gd_count: int
    substation: Optional[str]
    feeder: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class TransformerSummary(BaseModel):
    """Versão compacta para uso em listagens e mapas."""
    transformer_id: str
    latitude: float
    longitude: float
    rated_kva: float
    uc_count: int
    gd_count: int

    model_config = {"from_attributes": True}

class TransformerBalanceRead(BaseModel):
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
    operational_score: RiskScore
    uc_count: int
    telemetered_count: int
    computed_at: datetime

    model_config = {"from_attributes": True}
