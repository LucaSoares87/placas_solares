"""
Testes unitários do domínio ML — zero I/O.
"""

from __future__ import annotations

import pytest

from backend.domain.ml_model import (
    FEATURE_NAMES,
    FeatureVector,
    ModelMetrics,
    ModelType,
    PredictionTarget,
    TrainingConfig,
    compute_anomaly_score,
    extract_feature_array,
    is_model_acceptable,
)


# ─────────────────────────────────────────────────────────────────────────────
# extract_feature_array
# ─────────────────────────────────────────────────────────────────────────────

def _make_fv(**overrides) -> FeatureVector:
    defaults = dict(
        transformer_id="TR-001",
        ref_date="2025-01-01",
        measured_energy_kwh=1000.0,
        total_consumption_kwh=950.0,
        total_generation_kwh=100.0,
        total_injection_kwh=50.0,
        residual_kwh=50.0,
        error_pct=5.0,
        num_consumer_units=20,
        avg_confidence_inference=0.9,
        irradiance_factor=0.8,
        temperature_factor=0.96,
        cloud_factor=0.7,
        composite_climate_factor=0.54,
        irradiance_daily_kwh_m2=5.5,
        temperature_avg_c=28.0,
        cloud_cover_avg_pct=30.0,
        month=1,
        day_of_week=2,
        is_weekend=False,
        quarter=1,
    )
    defaults.update(overrides)
    return FeatureVector(**defaults)


def test_extract_feature_array_length():
    fv = _make_fv()
    arr = extract_feature_array(fv)
    assert len(arr) == len(FEATURE_NAMES)


def test_extract_feature_array_types():
    fv = _make_fv()
    arr = extract_feature_array(fv)
    assert all(isinstance(v, float) for v in arr)


def test_extract_feature_array_weekend_encoding():
    fv_weekday = _make_fv(is_weekend=False)
    fv_weekend = _make_fv(is_weekend=True)
    arr_wd = extract_feature_array(fv_weekday)
    arr_we = extract_feature_array(fv_weekend)
    idx = FEATURE_NAMES.index("is_weekend")
    assert arr_wd[idx] == 0.0
    assert arr_we[idx] == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# is_model_acceptable
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("r2, mape, target, expected", [
    (0.75, 10.0, PredictionTarget.ENERGY_LOSS_PCT, True),
    (0.65, 10.0, PredictionTarget.ENERGY_LOSS_PCT, False),   # R² abaixo do mínimo
    (0.75, 20.0, PredictionTarget.ENERGY_LOSS_PCT, False),   # MAPE acima do máximo
    (0.70, 15.0, PredictionTarget.ENERGY_LOSS_PCT, True),    # Limite exato
    (0.66, 30.0, PredictionTarget.ADJUSTED_BALANCE, True),   # R² >= 0.65 e MAE dentro
    (0.60, 0.0, PredictionTarget.FRAUD_SCORE, True),
    (0.59, 0.0, PredictionTarget.FRAUD_SCORE, False),
])
def test_is_model_acceptable(r2, mape, target, expected):
    metrics = ModelMetrics(mae=10.0, rmse=15.0, r2=r2, mape=mape)
    assert is_model_acceptable(metrics, target) == expected


# ─────────────────────────────────────────────────────────────────────────────
# compute_anomaly_score
# ─────────────────────────────────────────────────────────────────────────────

def test_anomaly_score_zero_when_perfect():
    assert compute_anomaly_score(100.0, 100.0, rmse=10.0) == 0.0


def test_anomaly_score_one_rmse():
    score = compute_anomaly_score(110.0, 100.0, rmse=10.0)
    assert score == pytest.approx(1.0)


def test_anomaly_score_anomaly_threshold():
    score = compute_anomaly_score(130.0, 100.0, rmse=10.0)
    assert score > 2.0


def test_anomaly_score_zero_rmse():
    assert compute_anomaly_score(999.0, 0.0, rmse=0.0) == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# TrainingConfig defaults
# ─────────────────────────────────────────────────────────────────────────────

def test_training_config_defaults():
    cfg = TrainingConfig()
    assert cfg.model_type == ModelType.GRADIENT_BOOSTING
    assert cfg.target == PredictionTarget.ENERGY_LOSS_PCT
    assert 0.0 < cfg.test_size < 1.0
    assert cfg.n_estimators > 0
