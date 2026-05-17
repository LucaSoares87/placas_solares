from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ── Snapshot ───────────────────────────────────────────────────────────────

class SnapshotRequest(BaseModel):
    transformer_id: str
    reference_period: str = Field(..., description="Ex: 2025-05")
    total_ucs: int = Field(..., ge=0)
    total_ucs_fv: int = Field(..., ge=0)
    kwp_total_estimado: Optional[float] = Field(None, ge=0)
    area_total_m2: Optional[float] = Field(None, ge=0)
    geracao_total_kwh: Optional[float] = Field(None, ge=0)
    consumo_total_kwh: Optional[float] = Field(None, ge=0)
    injecao_total_kwh: Optional[float] = Field(None, ge=0)
    balanco_estimado_kwh: Optional[float] = None
    balanco_real_kwh: Optional[float] = None
    erro_balanco_pct: Optional[float] = Field(None, ge=0)
    kwp_factor_atual: Optional[float] = None
    loss_factor_atual: Optional[float] = None
    modelo_convergido: bool = False
    score_operacional: str = "baixo_risco"
    total_anomalias_ativas: int = Field(0, ge=0)
    total_inspecoes_pendentes: int = Field(0, ge=0)
    confianca_media_deteccao: Optional[float] = Field(None, ge=0, le=1)
    coordinates: Optional[dict] = None


class SnapshotResponse(BaseModel):
    id: int
    transformer_id: str
    reference_period: str
    total_ucs: int
    total_ucs_fv: int
    cobertura_fv_pct: Optional[float]
    kwp_total_estimado: Optional[float]
    area_total_m2: Optional[float]
    geracao_total_kwh: Optional[float]
    consumo_total_kwh: Optional[float]
    balanco_estimado_kwh: Optional[float]
    balanco_real_kwh: Optional[float]
    erro_balanco_pct: Optional[float]
    kwp_factor_atual: Optional[float]
    loss_factor_atual: Optional[float]
    modelo_convergido: bool
    score_operacional: str
    total_anomalias_ativas: int
    total_inspecoes_pendentes: int
    confianca_media_deteccao: Optional[float]
    gerado_em: datetime

    model_config = {"from_attributes": True}


# ── KPIs Globais ───────────────────────────────────────────────────────────

class GlobalKPIsResponse(BaseModel):
    total_transformadores: int
    total_ucs: int
    total_ucs_fv: int
    cobertura_fv_pct: float
    kwp_total: float
    geracao_total_kwh: float
    consumo_total_kwh: float
    erro_medio_balanco_pct: float
    total_anomalias_ativas: int
    transformadores_criticos: int
    gerado_em: datetime = Field(default_factory=datetime.utcnow)


# ── Ranking ────────────────────────────────────────────────────────────────

class RankingItemResponse(BaseModel):
    rank: int
    transformer_id: str
    score_operacional: str
    erro_balanco_pct: Optional[float]
    total_anomalias_ativas: int
    kwp_total_estimado: Optional[float]
    total_ucs_fv: int
    confianca_media: Optional[float]
    reference_period: str


class RankingResponse(BaseModel):
    total: int
    gerado_em: datetime = Field(default_factory=datetime.utcnow)
    items: list[RankingItemResponse]


# ── Séries temporais ───────────────────────────────────────────────────────

class ErrorSeriesPoint(BaseModel):
    period: str
    erro_percentual_pct: Optional[float]
    erro_absoluto_kwh: Optional[float]
    score_operacional: str
    status_validacao: str
    created_at: str


class ErrorSeriesResponse(BaseModel):
    transformer_id: str
    total_points: int
    series: list[ErrorSeriesPoint]


class CalibrationSeriesPoint(BaseModel):
    executed_at: str
    kwp_factor_old: float
    kwp_factor_new: float
    kwp_factor_delta: float
    loss_factor_new: Optional[float]
    mean_kwp_error_pct: Optional[float]
    converged: bool
    samples_used: int


class CalibrationSeriesResponse(BaseModel):
    transformer_id: str
    total_cycles: int
    series: list[CalibrationSeriesPoint]


class AnomalySeriesPoint(BaseModel):
    uc_code: str
    is_anomaly: bool
    consensus: bool
    final_score: Optional[float]
    recommendation: Optional[str]
    detected_at: str
    resolved: bool


class AnomalySeriesResponse(BaseModel):
    transformer_id: str
    days: int
    total_events: int
    total_anomalies: int
    series: list[AnomalySeriesPoint]


# ── Mapa energético ────────────────────────────────────────────────────────

class MapFeatureProperties(BaseModel):
    transformer_id: str
    score_operacional: str
    kwp_total_estimado: Optional[float]
    total_ucs_fv: Optional[int]
    erro_balanco_pct: Optional[float]
    total_anomalias_ativas: Optional[int]
    reference_period: Optional[str]


class MapFeature(BaseModel):
    type: str = "Feature"
    geometry: Optional[dict] = None
    properties: MapFeatureProperties


class MapResponse(BaseModel):
    type: str = "FeatureCollection"
    total_features: int
    features: list[MapFeature]
    gerado_em: datetime = Field(default_factory=datetime.utcnow)


# ── Alertas ────────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    transformer_id: str
    uc_code: Optional[str]
    alert_type: str
    severity: str
    title: str
    message: str
    threshold_value: Optional[float]
    observed_value: Optional[float]
    status: str
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    total: int
    criticos: int
    altos: int
    medios: int
    alerts: list[AlertResponse]


# ── Exportação ─────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    transformer_ids: Optional[list[str]] = None
    reference_period: Optional[str] = None
    include_anomalies: bool = True
    include_calibration: bool = True
    include_validations: bool = True
    format: str = Field("json", pattern="^(json|csv)$")


class BIPayloadResponse(BaseModel):
    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    kpis: dict
    transformers: list[dict]
    anomalies_summary: list[dict]
    calibration_summary: list[dict]


# ── Health ─────────────────────────────────────────────────────────────────

class SystemHealthResponse(BaseModel):
    status: str
    database: str
    celery: str
    yolo_model: str
    anomaly_models: str
    total_snapshots: int
    total_open_alerts: int
    checked_at: datetime = Field(default_factory=datetime.utcnow)
