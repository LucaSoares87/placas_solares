"""
Testes unitários do Predictor.
"""

from __future__ import annotations

import pickle

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import GradientBoostingRegressor

from backend.domain.ml_model import FEATURE_NAMES, PredictionTarget
from backend.services.ml.predictor import Predictor


def _make_artifact(n_features: int = 19) -> bytes:
    rng = np.random.default_rng(0)
    X = rng.uniform(0, 10, (200, n_features))
    y = X[:, 0] * 0.5 + rng.normal(0, 0.3, 200)
    model = GradientBoostingRegressor(n_estimators=30, random_state=0)
    model.fit(X, y)
    return pickle.dumps(model)


def _make_predictor() -> Predictor:
    artifact = _make_artifact()
    return Predictor(
        artifact=artifact,
        model_version="v20250101_000000_abc123",
        model_rmse=1.5,
        target=PredictionTarget.ENERGY_LOSS_PCT,
    )


def _make_feature_vector() -> list[float]:
    rng = np.random.default_rng(42)
    return [float(v) for v in rng.uniform(0.1, 5.0, len(FEATURE_NAMES))]


def test_predictor_returns_result():
    predictor = _make_predictor()
    fv = _make_feature_vector()
    result = predictor.predict(
        transformer_id="TR-001",
        ref_date="2025-01-01",
        feature_vector=fv,
    )
    assert result.transformer_id == "TR-001"
    assert result.ref_date == "2025-01-01"
    assert isinstance(result.predicted_value, float)


def test_predictor_confidence_interval_order():
    predictor = _make_predictor()
    fv = _make_feature_vector()
    result = predictor.predict("TR-001", "2025-01-01", fv)
    assert result.confidence_interval_lower <= result.predicted_value
    assert result.predicted_value <= result.confidence_interval_upper


def test_predictor_no_anomaly_with_close_actual():
    predictor = _make_predictor()
    fv = _make_feature_vector()
    result_base = predictor.predict("TR-001", "2025-01-01", fv)
    result = predictor.predict(
        "TR-001", "2025-01-01", fv,
        actual_value=result_base.predicted_value + 0.1,
    )
    assert result.anomaly_score < 2.0
    assert not result.is_anomaly


def test_predictor_anomaly_with_distant_actual():
    predictor = _make_predictor()
    fv = _make_feature_vector()
    result = predictor.predict(
        "TR-001", "2025-01-01", fv,
        actual_value=9999.0,
    )
    assert result.is_anomaly
    assert result.anomaly_score > 2.0


def test_predictor_feature_contributions_sum():
    predictor = _make_predictor()
    fv = _make_feature_vector()
    result = predictor.predict("TR-001", "2025-01-01", fv)
    if result.feature_contributions:
        total = sum(result.feature_contributions.values())
        assert abs(total - 1.0) < 0.01


def test_predictor_version_propagated():
    predictor = _make_predictor()
    fv = _make_feature_vector()
    result = predictor.predict("TR-001", "2025-01-01", fv)
    assert result.model_version == "v20250101_000000_abc123"
