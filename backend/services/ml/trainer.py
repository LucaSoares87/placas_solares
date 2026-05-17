"""
Treinador de modelos ML.

Responsabilidades:
  1. Dividir dataset (temporal ou aleatório)
  2. Treinar modelo escolhido (GBM, RF, LR, XGBoost)
  3. Validação cruzada temporal
  4. Calcular métricas completas + feature importances
  5. Serializar o artefato do modelo
"""

from __future__ import annotations

import pickle
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import structlog
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

from backend.domain.ml_model import (
    FEATURE_NAMES,
    DataSplitStrategy,
    ModelMetrics,
    ModelStatus,
    ModelType,
    PredictionTarget,
    TrainingConfig,
    is_model_acceptable,
)

logger = structlog.get_logger(__name__)

# Tenta importar XGBoost — opcional
try:
    from xgboost import XGBRegressor
    _XGBOOST_AVAILABLE = True
except ImportError:
    _XGBOOST_AVAILABLE = False


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    if not mask.any():
        return 0.0
    return float(
        np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0
    )


class ModelTrainer:
    def __init__(self, config: TrainingConfig) -> None:
        self._config = config
        self._model: Any = None
        self._version: str = ""

    def train(self, df: pd.DataFrame) -> tuple[ModelMetrics, bytes, str]:
        """
        Treina o modelo completo.
        Retorna: (métricas, artefato_pkl, versão).
        """
        log = logger.bind(
            model_type=self._config.model_type.value,
            target=self._config.target.value,
        )

        feature_cols = [c for c in FEATURE_NAMES if c in df.columns]
        X = df[feature_cols].values.astype(np.float64)
        y = df["target"].values.astype(np.float64)

        log.info("trainer.starting", n_samples=len(X), n_features=len(feature_cols))

        X_train, X_test, y_train, y_test = self._split(X, y)

        model = self._build_model()
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        metrics = self._compute_metrics(
            model=model,
            X_train=X_train,
            y_train=y_train,
            y_test=y_test,
            y_pred=y_pred,
            feature_cols=feature_cols,
        )

        acceptable = is_model_acceptable(metrics, self._config.target)
        log.info(
            "trainer.finished",
            r2=metrics.r2,
            mae=metrics.mae,
            mape=metrics.mape,
            acceptable=acceptable,
        )

        self._model = model
        self._version = self._generate_version()
        artifact = pickle.dumps(model)

        return metrics, artifact, self._version

    # ─────────────────────────────────────────────────────────────────────────
    # Split de dados
    # ─────────────────────────────────────────────────────────────────────────

    def _split(
        self, X: np.ndarray, y: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        n = len(X)
        if self._config.split_strategy == DataSplitStrategy.TEMPORAL:
            split_idx = int(n * (1.0 - self._config.test_size))
            return X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]

        # Random / Stratified
        from sklearn.model_selection import train_test_split
        return train_test_split(
            X, y,
            test_size=self._config.test_size,
            random_state=self._config.random_state,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Construção do modelo
    # ─────────────────────────────────────────────────────────────────────────

    def _build_model(self) -> Any:
        cfg = self._config

        if cfg.model_type == ModelType.GRADIENT_BOOSTING:
            return GradientBoostingRegressor(
                n_estimators=cfg.n_estimators,
                max_depth=cfg.max_depth,
                learning_rate=cfg.learning_rate,
                min_samples_leaf=cfg.min_samples_leaf,
                random_state=cfg.random_state,
            )

        if cfg.model_type == ModelType.RANDOM_FOREST:
            return RandomForestRegressor(
                n_estimators=cfg.n_estimators,
                max_depth=cfg.max_depth,
                min_samples_leaf=cfg.min_samples_leaf,
                random_state=cfg.random_state,
                n_jobs=-1,
            )

        if cfg.model_type == ModelType.LINEAR_REGRESSION:
            return LinearRegression()

        if cfg.model_type == ModelType.XGBOOST:
            if not _XGBOOST_AVAILABLE:
                logger.warning("trainer.xgboost_unavailable_fallback_gbm")
                return GradientBoostingRegressor(
                    n_estimators=cfg.n_estimators,
                    max_depth=cfg.max_depth,
                    learning_rate=cfg.learning_rate,
                    random_state=cfg.random_state,
                )
            return XGBRegressor(
                n_estimators=cfg.n_estimators,
                max_depth=cfg.max_depth,
                learning_rate=cfg.learning_rate,
                random_state=cfg.random_state,
                n_jobs=-1,
                verbosity=0,
            )

        raise ValueError(f"ModelType desconhecido: {cfg.model_type}")

    # ─────────────────────────────────────────────────────────────────────────
    # Métricas
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_metrics(
        self,
        model: Any,
        X_train: np.ndarray,
        y_train: np.ndarray,
        y_test: np.ndarray,
        y_pred: np.ndarray,
        feature_cols: list[str],
    ) -> ModelMetrics:
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        mape = _mape(y_test, y_pred)

        # Cross-validation temporal
        tscv = TimeSeriesSplit(n_splits=self._config.cv_folds)
        X_all = np.vstack([X_train, y_test.reshape(-1, 1)[:0]])
        cv_scores = cross_val_score(
            model, X_train, y_train,
            cv=tscv, scoring="r2", n_jobs=-1,
        )
        cv_scores_list = cv_scores.tolist()

        # Feature importances
        importances: dict[str, float] = {}
        if hasattr(model, "feature_importances_"):
            importances = {
                col: round(float(imp), 6)
                for col, imp in zip(feature_cols, model.feature_importances_)
            }
        elif hasattr(model, "coef_"):
            importances = {
                col: round(float(abs(coef)), 6)
                for col, coef in zip(feature_cols, model.coef_)
            }

        return ModelMetrics(
            mae=round(mae, 4),
            rmse=round(rmse, 4),
            r2=round(r2, 4),
            mape=round(mape, 4),
            cv_scores=cv_scores_list,
            cv_mean=round(float(np.mean(cv_scores)), 4),
            cv_std=round(float(np.std(cv_scores)), 4),
            n_train=len(y_train),
            n_test=len(y_test),
            feature_importances=importances,
        )

    @staticmethod
    def _generate_version() -> str:
        now = datetime.now(timezone.utc)
        return f"v{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
