"""
Predictor: carrega o modelo em memória e executa predições.
Suporta cálculo de intervalo de confiança via bootstrap (GBM/RF).
"""

from __future__ import annotations

import pickle
from typing import Any, Optional

import numpy as np
import structlog

from backend.domain.ml_model import (
    FEATURE_NAMES,
    PredictionResult,
    PredictionTarget,
    compute_anomaly_score,
)

logger = structlog.get_logger(__name__)


class Predictor:
    def __init__(
        self,
        artifact: bytes,
        model_version: str,
        model_rmse: float,
        target: PredictionTarget,
    ) -> None:
        self._model: Any = pickle.loads(artifact)
        self._version = model_version
        self._rmse = model_rmse
        self._target = target

    def predict(
        self,
        transformer_id: str,
        ref_date: str,
        feature_vector: list[float],
        actual_value: Optional[float] = None,
    ) -> PredictionResult:
        x = np.array(feature_vector, dtype=np.float64).reshape(1, -1)
        predicted = float(self._model.predict(x)[0])

        lower, upper = self._confidence_interval(x, predicted)
        lower = min(lower, predicted)
        upper = max(upper, predicted)

        contributions = self._feature_contributions(feature_vector)

        anomaly_score = 0.0
        is_anomaly = False
        if actual_value is not None:
            anomaly_score = compute_anomaly_score(
                predicted=predicted,
                actual=actual_value,
                model_rmse=self._rmse,
            )
            is_anomaly = anomaly_score > 2.0

        logger.debug(
            "predictor.predict",
            transformer_id=transformer_id,
            predicted=round(predicted, 4),
            anomaly=is_anomaly,
        )

        return PredictionResult(
            transformer_id=transformer_id,
            ref_date=ref_date,
            target=self._target,
            predicted_value=round(predicted, 4),
            confidence_interval_lower=round(lower, 4),
            confidence_interval_upper=round(upper, 4),
            model_version=self._version,
            feature_contributions=contributions,
            is_anomaly=is_anomaly,
            anomaly_score=round(anomaly_score, 4),
        )

    def _confidence_interval(
        self,
        x: np.ndarray,
        predicted: float,
    ) -> tuple[float, float]:
        try:
            if hasattr(self._model, "estimators_"):
                preds = np.array(
                    [
                        est.predict(x)[0]
                        for est in self._model.estimators_.flat
                        if hasattr(est, "predict")
                    ]
                )
                if len(preds) > 10:
                    lower = float(np.percentile(preds, 2.5))
                    upper = float(np.percentile(preds, 97.5))
                    return min(lower, predicted), max(upper, predicted)
        except Exception:
            pass

        margin = abs(1.96 * self._rmse)
        return predicted - margin, predicted + margin

    def _feature_contributions(
        self, feature_vector: list[float]
    ) -> dict[str, float]:
        if not hasattr(self._model, "feature_importances_"):
            return {}

        importances = self._model.feature_importances_
        n = min(len(FEATURE_NAMES), len(importances), len(feature_vector))
        total = sum(abs(feature_vector[i]) * importances[i] for i in range(n))
        if total == 0:
            return {}

        return {
            FEATURE_NAMES[i]: round(
                abs(feature_vector[i]) * importances[i] / total, 4
            )
            for i in range(n)
        }