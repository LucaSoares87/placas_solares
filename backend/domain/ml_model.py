"""
Regras de domínio puras para o módulo de Machine Learning.
Sem dependências de infraestrutura — apenas tipos, enums e lógica de decisão.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ModelType(str, Enum):
    GRADIENT_BOOSTING = "gradient_boosting"
    RANDOM_FOREST = "random_forest"
    LINEAR_REGRESSION = "linear_regression"
    XGBOOST = "xgboost"


class ModelStatus(str, Enum):
    TRAINING = "training"
    READY = "ready"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class PredictionTarget(str, Enum):
    ENERGY_LOSS_PCT = "energy_loss_pct"
    ADJUSTED_BALANCE = "adjusted_balance"
    FRAUD_SCORE = "fraud_score"


class DataSplitStrategy(str, Enum):
    TEMPORAL = "temporal"
    RANDOM = "random"
    STRATIFIED = "stratified"


@dataclass
class FeatureVector:
    transformer_id: str
    ref_date: str

    measured_energy_kwh: float
    total_consumption_kwh: float
    total_generation_kwh: float
    total_injection_kwh: float
    residual_kwh: float
    error_pct: float
    num_consumer_units: int
    avg_confidence_inference: float

    irradiance_factor: float
    temperature_factor: float
    cloud_factor: float
    composite_climate_factor: float
    irradiance_daily_kwh_m2: float
    temperature_avg_c: float
    cloud_cover_avg_pct: float

    month: int
    day_of_week: int
    is_weekend: bool
    quarter: int

    label_energy_loss_pct: Optional[float] = None
    label_adjusted_balance: Optional[float] = None
    label_fraud_score: Optional[float] = None


@dataclass
class TrainingConfig:
    model_type: ModelType = ModelType.GRADIENT_BOOSTING
    target: PredictionTarget = PredictionTarget.ENERGY_LOSS_PCT
    test_size: float = 0.2
    split_strategy: DataSplitStrategy = DataSplitStrategy.TEMPORAL
    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.05
    min_samples_leaf: int = 5
    random_state: int = 42
    cv_folds: int = 5


@dataclass
class ModelMetrics:
    mae: float
    rmse: float
    r2: float
    mape: float
    cv_scores: list[float] = field(default_factory=list)
    cv_mean: float = 0.0
    cv_std: float = 0.0
    n_train: int = 0
    n_test: int = 0
    feature_importances: dict[str, float] = field(default_factory=dict)


@dataclass
class PredictionResult:
    transformer_id: str
    ref_date: str
    target: PredictionTarget
    predicted_value: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    model_version: str
    feature_contributions: dict[str, float]
    is_anomaly: bool
    anomaly_score: float


FEATURE_NAMES = [
    "measured_energy_kwh",
    "total_consumption_kwh",
    "total_generation_kwh",
    "total_injection_kwh",
    "residual_kwh",
    "error_pct",
    "num_consumer_units",
    "avg_confidence_inference",
    "irradiance_factor",
    "temperature_factor",
    "cloud_factor",
    "composite_climate_factor",
    "irradiance_daily_kwh_m2",
    "temperature_avg_c",
    "cloud_cover_avg_pct",
    "month",
    "day_of_week",
    "is_weekend",
    "quarter",
]


def extract_feature_array(fv: FeatureVector) -> list[float]:
    return [
        fv.measured_energy_kwh,
        fv.total_consumption_kwh,
        fv.total_generation_kwh,
        fv.total_injection_kwh,
        fv.residual_kwh,
        fv.error_pct,
        float(fv.num_consumer_units),
        fv.avg_confidence_inference,
        fv.irradiance_factor,
        fv.temperature_factor,
        fv.cloud_factor,
        fv.composite_climate_factor,
        fv.irradiance_daily_kwh_m2,
        fv.temperature_avg_c,
        fv.cloud_cover_avg_pct,
        float(fv.month),
        float(fv.day_of_week),
        1.0 if fv.is_weekend else 0.0,
        float(fv.quarter),
    ]


def is_model_acceptable(metrics: ModelMetrics, target: PredictionTarget) -> bool:
    if target == PredictionTarget.ENERGY_LOSS_PCT:
        return metrics.r2 >= 0.70 and metrics.mape <= 15.0

    if target == PredictionTarget.ADJUSTED_BALANCE:
        return metrics.r2 >= 0.65 and metrics.mae <= 50.0

    if target == PredictionTarget.FRAUD_SCORE:
        return metrics.r2 >= 0.60

    return False


def compute_anomaly_score(
    predicted: float,
    actual: float,
    model_rmse: Optional[float] = None,
    *,
    rmse: Optional[float] = None,
) -> float:
    effective_rmse = rmse if rmse is not None else model_rmse

    if effective_rmse is None or effective_rmse <= 0:
        return 0.0

    return round(abs(predicted - actual) / effective_rmse, 4)