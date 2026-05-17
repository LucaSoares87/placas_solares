"""
Schemas Pydantic para o módulo ML.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from backend.domain.ml_model import (
    DataSplitStrategy,
    ModelType,
    PredictionTarget,
)


# ─────────────────────────────────────────────────────────────────────────────
# Requests
# ─────────────────────────────────────────────────────────────────────────────

class TrainRequest(BaseModel):
    model_type: ModelType = ModelType.GRADIENT_BOOSTING
    target: PredictionTarget = PredictionTarget.ENERGY_LOSS_PCT
    transformer_ids: Optional[list[str]] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)
    split_strategy: DataSplitStrategy = DataSplitStrategy.TEMPORAL
    n_estimators: int = Field(default=200, ge=50, le=1000)
    max_depth: int = Field(default=6, ge=2, le=15)
    learning_rate: float = Field(default=0.05, ge=0.001, le=0.5)


class PredictRequest(BaseModel):
    transformer_id: str = Field(..., min_length=2, max_length=30)
    ref_date: date
    target: PredictionTarget = PredictionTarget.ENERGY_LOSS_PCT
    actual_value: Optional[float] = None


class BatchPredictRequest(BaseModel):
    transformer_ids: list[str] = Field(..., min_length=1)
    ref_date: date
    target: PredictionTarget = PredictionTarget.ENERGY_LOSS_PCT


# ─────────────────────────────────────────────────────────────────────────────
# Responses
# ─────────────────────────────────────────────────────────────────────────────

class TrainResponse(BaseModel):
    version: str
    status: str
    model_type: str
    target: str
    acceptable: bool
    metrics: dict
    n_samples: int

    model_config = {"from_attributes": True}


class PredictionResponse(BaseModel):
    transformer_id: str
    ref_date: str
    target: str
    predicted_value: float
    ci_lower: float
    ci_upper: float
    model_version: str
    feature_contributions: dict
    is_anomaly: bool
    anomaly_score: float

    model_config = {"from_attributes": True}


class BatchPredictionResponse(BaseModel):
    ref_date: str
    target: str
    total: int
    success: int
    failed: int
    anomalies_detected: int
    predictions: list[PredictionResponse]
    errors: list[dict]

    model_config = {"from_attributes": True}


class ModelVersionResponse(BaseModel):
    version: str
    model_type: str
    status: str
    metrics: dict
    created_at: str

    model_config = {"from_attributes": True}


class AnomalyResponse(BaseModel):
    transformer_id: str
    ref_date: str
    target: str
    predicted_value: float
    actual_value: Optional[float]
    anomaly_score: float
    model_version: str

    model_config = {"from_attributes": True}
