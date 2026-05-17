from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.domain.entities import EnergyStatus, RiskScore, UCProfile


class ConsumerUnitBase(BaseModel):
    uc_code: str = Field(..., min_length=1, max_length=20)
    transformer_id: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    profile: UCProfile
    is_telemetered: bool = False
    has_gd: bool = False
    gd_installed_kwp: Optional[float] = Field(None, ge=0)
    inverter_model: Optional[str] = None
    panel_count: Optional[int] = Field(None, ge=0)
    address: Optional[str] = None


class ConsumerUnitCreate(BaseModel):
    uc_code: str = Field(..., min_length=2, max_length=20)
    transformer_id: str = Field(..., min_length=2, max_length=30)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    profile: UCProfile = UCProfile.RESIDENTIAL
    is_telemetered: bool = False
    has_gd: bool = False
    gd_installed_kwp: Optional[float] = Field(None, gt=0.0, le=1000.0)
    inverter_model: Optional[str] = Field(None, max_length=100)
    panel_count: Optional[int] = Field(None, ge=1, le=10_000)
    address: Optional[str] = Field(None, max_length=300)

class ConsumerUnitUpdate(BaseModel):
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    profile: Optional[UCProfile] = None
    is_telemetered: Optional[bool] = None
    has_gd: Optional[bool] = None
    gd_installed_kwp: Optional[float] = Field(None, gt=0.0, le=1000.0)
    inverter_model: Optional[str] = Field(None, max_length=100)
    panel_count: Optional[int] = Field(None, ge=1, le=10_000)
    address: Optional[str] = Field(None, max_length=300)
    transformer_id: Optional[str] = Field(None, min_length=2, max_length=30)

class ConsumerUnitRead(BaseModel):
    id: int
    uc_code: str
    transformer_id: str
    latitude: float
    longitude: float
    profile: str
    is_telemetered: bool
    has_gd: bool
    gd_installed_kwp: Optional[float]
    inverter_model: Optional[str]
    panel_count: Optional[int]
    address: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConsumerUnitSummary(BaseModel):
    """Versão compacta para uso em listagens de transformador."""
    uc_code: str
    profile: str
    has_gd: bool
    is_telemetered: bool
    gd_installed_kwp: Optional[float]

    model_config = {"from_attributes": True}

class EnergyInferenceRead(BaseModel):
    uc: str
    tem_fv: bool
    latitude: float
    longitude: float
    area_m2: Optional[float]
    kwp_estimado: Optional[float]
    geracao_kw: Optional[float]
    consumo_estimado_kw: float
    injecao_kw_range: Optional[list[float]]
    status: EnergyStatus
    confianca: float
    transformador: str
    score_operacional: RiskScore
    computed_at: datetime

    model_config = {"from_attributes": True}
