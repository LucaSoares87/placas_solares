"""
Testes unitários do ModelTrainer com dados sintéticos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.domain.ml_model import (
    FEATURE_NAMES,
    DataSplitStrategy,
    ModelType,
    PredictionTarget,
    TrainingConfig,
)
from backend.services.ml.trainer import ModelTrainer


def _make_synthetic_df(n: int = 100, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        row = {name: rng.uniform(0.1, 10.0) for name in FEATURE_NAMES}
        # Target linear + ruído
        row["target"] = (
            row["error_pct"] * 0.5
            + row["cloud_cover_avg_pct"] * 0.1
            + rng.normal(0, 0.5)
        )
        row["transformer_id"] = f"TR-{i:03d}"
        row["ref_date"] = f"2025-01-{(i % 28) + 1:02d}"
        rows.append(row)
    return pd.DataFrame(rows)


def test_trainer_gbm_basic():
    config = TrainingConfig(
        model_type=ModelType.GRADIENT_BOOSTING,
        target=PredictionTarget.ENERGY_LOSS_PCT,
        n_estimators=50,
        test_size=0.2,
    )
    df = _make_synthetic_df(100)
    trainer = ModelTrainer(config)
    metrics, artifact, version = trainer.train(df)

    assert metrics.r2 is not None
    assert metrics.mae >= 0.0
    assert metrics.rmse >= 0.0
    assert len(artifact) > 0
    assert version.startswith("v")


def test_trainer_random_forest():
    config = TrainingConfig(
        model_type=ModelType.RANDOM_FOREST,
        n_estimators=30,
        test_size=0.2,
    )
    df = _make_synthetic_df(80)
    trainer = ModelTrainer(config)
    metrics, artifact, version = trainer.train(df)
    assert artifact is not None


def test_trainer_linear_regression():
    config = TrainingConfig(model_type=ModelType.LINEAR_REGRESSION)
    df = _make_synthetic_df(60)
    trainer = ModelTrainer(config)
    metrics, artifact, version = trainer.train(df)
    assert metrics.n_train > 0
    assert metrics.n_test > 0


def test_trainer_feature_importances():
    config = TrainingConfig(
        model_type=ModelType.GRADIENT_BOOSTING,
        n_estimators=50,
    )
    df = _make_synthetic_df(100)
    trainer = ModelTrainer(config)
    metrics, _, _ = trainer.train(df)
    assert len(metrics.feature_importances) > 0
    assert sum(metrics.feature_importances.values()) == pytest.approx(1.0, abs=0.01)


def test_trainer_temporal_split():
    config = TrainingConfig(
        split_strategy=DataSplitStrategy.TEMPORAL,
        test_size=0.2,
        n_estimators=30,
    )
    df = _make_synthetic_df(100)
    trainer = ModelTrainer(config)
    metrics, _, _ = trainer.train(df)
    assert metrics.n_train == 80
    assert metrics.n_test == 20


def test_trainer_cv_scores():
    config = TrainingConfig(
        n_estimators=30,
        cv_folds=3,
    )
    df = _make_synthetic_df(80)
    trainer = ModelTrainer(config)
    metrics, _, _ = trainer.train(df)
    assert len(metrics.cv_scores) == 3
    assert metrics.cv_mean is not None
    assert metrics.cv_std >= 0.0
