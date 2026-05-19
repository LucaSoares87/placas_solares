from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InjectionStatus(str, Enum):
    INJECTING = "injetando"
    BALANCED = "equilibrado"
    CONSUMING = "consumindo"
    UNKNOWN = "desconhecido"


class OperationalScore(str, Enum):
    LOW_RISK = "baixo_risco"
    MEDIUM_RISK = "medio_risco"
    HIGH_RISK = "alto_risco"
    INSPECTION_PRIORITY = "prioridade_inspecao"


class GeoReferenceInput(BaseModel):
    gsd_m_per_pixel: Optional[float] = Field(None, gt=0, description="GSD em m/pixel")
    altitude_m: Optional[float] = Field(None, gt=0)
    focal_length_mm: Optional[float] = Field(None, gt=0)
    sensor_width_mm: Optional[float] = Field(None, gt=0)
    image_width_px: Optional[int] = Field(None, gt=0)
    perspective_correction: float = Field(1.0, ge=0.5, le=1.0)
    distortion_correction: float = Field(1.0, ge=0.5, le=1.0)


class FVDetectionRequest(BaseModel):
    uc_code: str = Field(..., description="Código da unidade consumidora")
    transformer_id: str = Field(..., description="ID do transformador associado")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    geo_reference: Optional[GeoReferenceInput] = None
    regional_kwp_factor: Optional[float] = Field(None, gt=0, le=1.0)
    confidence_threshold: Optional[float] = Field(0.45, ge=0.1, le=1.0)

    @field_validator("uc_code")
    @classmethod
    def uc_code_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("uc_code não pode ser vazio")
        return value.strip()


class DetectedPanelOutput(BaseModel):
    panel_index: int
    area_pixels: float
    area_m2: float
    confidence: float
    centroid_x: float
    centroid_y: float


class FVDetectionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    uc_code: str
    transformer_id: str
    latitude: float
    longitude: float
    has_fv: bool
    total_panels: int
    total_area_m2: float
    kwp_estimated: float
    kwp_adjusted: float
    kwp_factor_used: float
    kwp_factor_source: str
    detection_confidence: float
    panels: list[DetectedPanelOutput]
    model_version: str
    status: InjectionStatus = InjectionStatus.UNKNOWN
    score_operacional: OperationalScore = OperationalScore.LOW_RISK
    task_id: Optional[str] = None


class FVDetectionAsyncResponse(BaseModel):
    task_id: str
    uc_code: str
    status: str = "queued"
    message: str = "Detecção FV enviada para processamento assíncrono"


class FVTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[FVDetectionResponse] = None
    error: Optional[str] = None