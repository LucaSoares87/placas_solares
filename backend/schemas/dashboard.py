from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
    coordinates: Optional[dict[str, Any]] = None


class SnapshotResponse(BaseModel):
    id: int
    transformer_id: str
    reference_period: str
    total_ucs: int
    total_ucs_fv: int
    cobertura_fv_pct: Optional[float] = None
    kwp_total_estimado: Optional[float] = None
    area_total_m2: Optional[float] = None
    geracao_total_kwh: Optional[float] = None
    consumo_total_kwh: Optional[float] = None
    injecao_total_kwh: Optional[float] = None
    balanco_estimado_kwh: Optional[float] = None
    balanco_real_kwh: Optional[float] = None
    erro_balanco_pct: Optional[float] = None
    kwp_factor_atual: Optional[float] = None
    loss_factor_atual: Optional[float] = None
    modelo_convergido: bool = False
    score_operacional: str = "baixo_risco"
    total_anomalias_ativas: int = 0
    total_inspecoes_pendentes: int = 0
    confianca_media_deteccao: Optional[float] = None
    gerado_em: datetime = Field(default_factory=utc_now)

    model_config = {"from_attributes": True}


class GlobalKPIResponse(BaseModel):
    total_transformers: int = 0
    total_consumer_units: int = 0
    total_ucs: int = 0
    total_gd_units: int = 0
    total_ucs_fv: int = 0
    total_ucs_with_gd: int = 0
    gd_penetration_rate: float = 0.0
    telemetry_coverage_rate: float = 0.0
    telemetry_coverage_pct: float = 0.0
    estimated_generation_kwh: float = 0.0
    estimated_consumption_kwh: float = 0.0
    estimated_injection_kwh: float = 0.0
    active_anomalies: int = 0
    critical_transformers: int = 0
    transformers_balanced: int = 0
    generated_at: datetime = Field(default_factory=utc_now)


class GlobalKPIsResponse(BaseModel):
    total_transformadores: int = 0
    total_ucs: int = 0
    total_ucs_fv: int = 0
    cobertura_fv_pct: float = 0.0
    kwp_total: float = 0.0
    geracao_total_kwh: float = 0.0
    consumo_total_kwh: float = 0.0
    erro_medio_balanco_pct: float = 0.0
    total_anomalias_ativas: int = 0
    transformadores_criticos: int = 0
    gerado_em: datetime = Field(default_factory=utc_now)


class TransformerSummaryResponse(BaseModel):
    transformer_id: str
    substation: Optional[str] = None
    feeder: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rated_kva: float = 0.0
    load_factor: float = 0.0
    load_factor_pct: float = 0.0
    is_overloaded: bool = False
    uc_count: int = 0
    gd_count: int = 0
    telemetered_count: int = 0
    total_consumer_units: int = 0
    total_gd_units: int = 0
    gd_penetration_rate: float = 0.0
    telemetry_coverage_rate: float = 0.0
    estimated_generation_kwh: float = 0.0
    estimated_consumption_kwh: float = 0.0
    estimated_injection_kwh: float = 0.0
    measured_kwh: float = 0.0
    technical_losses_kwh: float = 0.0
    residual_kwh: float = 0.0
    percentage_error: float = 0.0
    balance_error_pct: Optional[float] = None
    balance_status: str = "unknown"
    operational_score: str = "low"
    open_anomalies_count: int = 0
    last_balance_computed_at: Optional[datetime] = None
    last_inference_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RankingItemResponse(BaseModel):
    rank: int
    transformer_id: str
    score_operacional: str
    erro_balanco_pct: Optional[float] = None
    total_anomalias_ativas: int = 0
    kwp_total_estimado: Optional[float] = None
    total_ucs_fv: int = 0
    confianca_media: Optional[float] = None
    reference_period: str = ""


class RankingResponse(BaseModel):
    total: int = 0
    gerado_em: datetime = Field(default_factory=utc_now)
    items: list[RankingItemResponse] = Field(default_factory=list)


class GDRankingItem(BaseModel):
    rank: int
    uc_code: str
    transformer_id: str
    address: Optional[str] = None
    profile: Optional[str] = None
    gd_installed_kwp: Optional[float] = None
    kwp_estimated: Optional[float] = None
    estimated_kwp: float = 0.0
    generation_kw: Optional[float] = None
    estimated_generation_kwh: float = 0.0
    injection_kw_min: Optional[float] = None
    injection_kw_max: Optional[float] = None
    injection_kw_mid: Optional[float] = None
    injection_probability: float = 0.0
    status: Optional[str] = None
    confidence: float = 0.0
    operational_score: str = "low"
    inference_method: Optional[str] = None
    last_computed_at: Optional[datetime] = None


class GDRankingResponse(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_generation_kw: float = 0.0
    items: list[GDRankingItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class ErrorSeriesPoint(BaseModel):
    period: str
    erro_percentual_pct: Optional[float] = None
    erro_absoluto_kwh: Optional[float] = None
    score_operacional: str = "unknown"
    status_validacao: str = "unknown"
    created_at: str = ""


class ErrorSeriesResponse(BaseModel):
    transformer_id: str
    total_points: int = 0
    series: list[ErrorSeriesPoint] = Field(default_factory=list)


class CalibrationSeriesPoint(BaseModel):
    executed_at: str
    kwp_factor_old: float
    kwp_factor_new: float
    kwp_factor_delta: float
    loss_factor_new: Optional[float] = None
    mean_kwp_error_pct: Optional[float] = None
    converged: bool = False
    samples_used: int = 0


class CalibrationSeriesResponse(BaseModel):
    transformer_id: str
    total_cycles: int = 0
    series: list[CalibrationSeriesPoint] = Field(default_factory=list)


class AnomalySeriesPoint(BaseModel):
    uc_code: str
    is_anomaly: bool
    consensus: bool
    final_score: Optional[float] = None
    recommendation: Optional[str] = None
    detected_at: str
    resolved: bool = False


class AnomalySeriesResponse(BaseModel):
    transformer_id: str
    days: int
    total_events: int = 0
    total_anomalies: int = 0
    series: list[AnomalySeriesPoint] = Field(default_factory=list)


class BalanceTimeSeriesPoint(BaseModel):
    period: str
    period_end: Optional[datetime] = None
    measured_kwh: Optional[float] = None
    consumo_total_kwh: Optional[float] = None
    geracao_total_kwh: Optional[float] = None
    injecao_total_kwh: Optional[float] = None
    estimated_consumption_kwh: Optional[float] = None
    estimated_generation_kwh: Optional[float] = None
    estimated_injection_kwh: Optional[float] = None
    technical_losses_kwh: Optional[float] = None
    residual_kwh: Optional[float] = None
    balanco_estimado_kwh: Optional[float] = None
    balanco_real_kwh: Optional[float] = None
    erro_balanco_pct: Optional[float] = None
    percentage_error: Optional[float] = None
    balance_status: Optional[str] = None
    score_operacional: Optional[str] = None
    operational_score: Optional[str] = None


class BalanceTimeSeriesResponse(BaseModel):
    transformer_id: str
    total_points: int = 0
    mean_percentage_error: float = 0.0
    avg_percentage_error: float = 0.0
    min_percentage_error: float = 0.0
    max_percentage_error: float = 0.0
    series: list[BalanceTimeSeriesPoint] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class MapFeatureProperties(BaseModel):
    transformer_id: str
    score_operacional: str
    kwp_total_estimado: Optional[float] = None
    total_ucs_fv: Optional[int] = None
    erro_balanco_pct: Optional[float] = None
    total_anomalias_ativas: Optional[int] = None
    reference_period: Optional[str] = None


class MapFeature(BaseModel):
    type: str = "Feature"
    geometry: Optional[dict[str, Any]] = None
    properties: MapFeatureProperties


class MapResponse(BaseModel):
    type: str = "FeatureCollection"
    total_features: int = 0
    features: list[MapFeature] = Field(default_factory=list)
    gerado_em: datetime = Field(default_factory=utc_now)


class RiskMapFeature(BaseModel):
    type: str = "Feature"
    geometry: Optional[dict[str, Any]] = None
    properties: dict[str, Any] = Field(default_factory=dict)


class RiskMapResponse(BaseModel):
    type: str = "FeatureCollection"
    total: int = 0
    total_features: int = 0
    critical_count: int = 0
    low_count: int = 0
    high_count: int = 0
    counts_by_score: dict[str, int] = Field(default_factory=dict)
    features: list[RiskMapFeature] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class AlertResponse(BaseModel):
    id: int
    transformer_id: str
    uc_code: Optional[str] = None
    alert_type: str
    severity: str
    title: str
    message: str
    threshold_value: Optional[float] = None
    observed_value: Optional[float] = None
    status: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    total: int = 0
    criticos: int = 0
    altos: int = 0
    medios: int = 0
    alerts: list[AlertResponse] = Field(default_factory=list)

class ExportRequest(BaseModel):
    report_type: str = "transformer_balance"
    format: str = Field("json", pattern="^(json|csv)$")
    transformer_id: Optional[str] = None
    transformer_ids: Optional[list[str]] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    reference_period: Optional[str] = None
    include_anomalies: bool = True
    include_calibration: bool = True
    include_validations: bool = True


class BIPayloadResponse(BaseModel):
    schema_version: str = "1.0"
    generated_at: datetime = Field(default_factory=utc_now)
    kpis: dict[str, Any] = Field(default_factory=dict)
    transformers: list[dict[str, Any]] = Field(default_factory=list)
    anomalies_summary: list[dict[str, Any]] = Field(default_factory=list)
    calibration_summary: list[dict[str, Any]] = Field(default_factory=list)


class SystemHealthResponse(BaseModel):
    status: str
    database: str
    celery: str
    yolo_model: str
    anomaly_models: str
    total_snapshots: int
    total_open_alerts: int
    checked_at: datetime = Field(default_factory=utc_now)


class UCDetailResponse(BaseModel):
    uc_code: str
    transformer_id: str
    has_gd: bool = False
    estimated_kwp: Optional[float] = None
    kwp_estimated: Optional[float] = None
    estimated_generation_kwh: Optional[float] = None
    estimated_consumption_kwh: Optional[float] = None
    estimated_injection_kwh: Optional[float] = None
    confidence: Optional[float] = None
    operational_score: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    updated_at: Optional[datetime] = None