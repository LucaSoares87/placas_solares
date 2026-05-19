"""
Treinador de modelos ML.

Responsabilidades:
  1. Dividir dataset temporal ou aleatório
  2. Treinar modelo escolhido: GBM, RF, LR ou XGBoost
  3. Executar validação cruzada quando houver dados suficientes
  4. Calcular métricas completas e feature importances
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
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, train_test_split

from backend.domain.ml_model import (
    FEATURE_NAMES,
    DataSplitStrategy,
    ModelMetrics,
    ModelType,
    TrainingConfig,
    is_model_acceptable,
)

logger = structlog.get_logger(__name__)

try:
    from xgboost import XGBRegressor

    _XGBOOST_AVAILABLE = True
except ImportError:
    XGBRegressor = None
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
        self._validate_dataframe(df)

        log = logger.bind(
            model_type=self._config.model_type.value,
            target=self._config.target.value,
        )

        feature_cols = [column for column in FEATURE_NAMES if column in df.columns]

        if not feature_cols:
            raise ValueError("Nenhuma feature válida encontrada no dataframe.")

        x_values = df[feature_cols].values.astype(np.float64)
        y_values = df["target"].values.astype(np.float64)

        log.info(
            "trainer.starting",
            n_samples=len(x_values),
            n_features=len(feature_cols),
        )

        x_train, x_test, y_train, y_test = self._split(x_values, y_values)

        model = self._build_model()
        model.fit(x_train, y_train)

        y_pred = model.predict(x_test)

        metrics = self._compute_metrics(
            model=model,
            x_train=x_train,
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

    def _split(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        sample_count = len(x_values)

        if sample_count < 4:
            raise ValueError("O dataset precisa ter pelo menos 4 amostras para treino.")

        if self._config.split_strategy == DataSplitStrategy.TEMPORAL:
            split_index = int(sample_count * (1.0 - self._config.test_size))
            split_index = max(1, min(split_index, sample_count - 1))

            return (
                x_values[:split_index],
                x_values[split_index:],
                y_values[:split_index],
                y_values[split_index:],
            )

        return train_test_split(
            x_values,
            y_values,
            test_size=self._config.test_size,
            random_state=self._config.random_state,
        )

    def _build_model(self) -> Any:
        config = self._config

        if config.model_type == ModelType.GRADIENT_BOOSTING:
            return GradientBoostingRegressor(
                n_estimators=config.n_estimators,
                max_depth=config.max_depth,
                learning_rate=config.learning_rate,
                min_samples_leaf=config.min_samples_leaf,
                random_state=config.random_state,
            )

        if config.model_type == ModelType.RANDOM_FOREST:
            return RandomForestRegressor(
                n_estimators=config.n_estimators,
                max_depth=config.max_depth,
                min_samples_leaf=config.min_samples_leaf,
                random_state=config.random_state,
                n_jobs=-1,
            )

        if config.model_type == ModelType.LINEAR_REGRESSION:
            return LinearRegression()

        if config.model_type == ModelType.XGBOOST:
            if not _XGBOOST_AVAILABLE or XGBRegressor is None:
                logger.warning("trainer.xgboost_unavailable_fallback_gbm")
                return GradientBoostingRegressor(
                    n_estimators=config.n_estimators,
                    max_depth=config.max_depth,
                    learning_rate=config.learning_rate,
                    random_state=config.random_state,
                )

            return XGBRegressor(
                n_estimators=config.n_estimators,
                max_depth=config.max_depth,
                learning_rate=config.learning_rate,
                random_state=config.random_state,
                n_jobs=-1,
                verbosity=0,
            )

        raise ValueError(f"ModelType desconhecido: {config.model_type}")

    def _compute_metrics(
        self,
        model: Any,
        x_train: np.ndarray,
        y_train: np.ndarray,
        y_test: np.ndarray,
        y_pred: np.ndarray,
        feature_cols: list[str],
    ) -> ModelMetrics:
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        mape = _mape(y_test, y_pred)

        cv_scores_list = self._compute_cv_scores(
            model=model,
            x_train=x_train,
            y_train=y_train,
        )

        importances = self._extract_feature_importances(
            model=model,
            feature_cols=feature_cols,
        )

        return ModelMetrics(
            mae=round(mae, 4),
            rmse=round(rmse, 4),
            r2=round(r2, 4),
            mape=round(mape, 4),
            cv_scores=cv_scores_list,
            cv_mean=round(float(np.mean(cv_scores_list)), 4)
            if cv_scores_list
            else 0.0,
            cv_std=round(float(np.std(cv_scores_list)), 4)
            if cv_scores_list
            else 0.0,
            n_train=len(y_train),
            n_test=len(y_test),
            feature_importances=importances,
        )

    def _compute_cv_scores(
        self,
        model: Any,
        x_train: np.ndarray,
        y_train: np.ndarray,
    ) -> list[float]:
        if len(x_train) <= self._config.cv_folds:
            return []

        n_splits = min(self._config.cv_folds, len(x_train) - 1)

        if n_splits < 2:
            return []

        splitter = TimeSeriesSplit(n_splits=n_splits)

        try:
            scores = cross_val_score(
                model,
                x_train,
                y_train,
                cv=splitter,
                scoring="r2",
                n_jobs=-1,
            )
            return [round(float(score), 6) for score in scores]
        except ValueError as exc:
            logger.warning("trainer.cross_validation_skipped", error=str(exc))
            return []

    def _extract_feature_importances(
        self,
        model: Any,
        feature_cols: list[str],
    ) -> dict[str, float]:
        if hasattr(model, "feature_importances_"):
            return {
                column: round(float(importance), 6)
                for column, importance in zip(feature_cols, model.feature_importances_)
            }

        if hasattr(model, "coef_"):
            return {
                column: round(float(abs(coefficient)), 6)
                for column, coefficient in zip(feature_cols, model.coef_)
            }

        return {}

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        if df.empty:
            raise ValueError("O dataframe de treino não pode estar vazio.")

        if "target" not in df.columns:
            raise ValueError("O dataframe de treino precisa conter a coluna 'target'.")

        if len(df) < 4:
            raise ValueError("O dataframe precisa ter pelo menos 4 linhas.")

    @staticmethod
    def _generate_version() -> str:
        now = datetime.now(timezone.utc)
        return f"v{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"