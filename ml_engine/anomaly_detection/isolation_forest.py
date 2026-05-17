import structlog
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

logger = structlog.get_logger(__name__)


@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float
    features_used: list[str]
    model_type: str
    details: dict = field(default_factory=dict)


class IsolationForestDetector:
    """
    Detecta anomalias em vetores de features energéticas usando Isolation Forest.

    Features esperadas:
        - consumo_estimado_kwh
        - geracao_estimada_kwh
        - injecao_estimada_kwh
        - erro_balanco_pct
        - kwp_estimado
        - area_m2
        - confianca_deteccao

    Treinado com dados históricos normais do transformador.
    Scores negativos elevados indicam anomalia.
    """

    FEATURE_NAMES = [
        "consumo_estimado_kwh",
        "geracao_estimada_kwh",
        "injecao_estimada_kwh",
        "erro_balanco_pct",
        "kwp_estimado",
        "area_m2",
        "confianca_deteccao",
    ]

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42,
    ):
        self._contamination = contamination
        self._n_estimators = n_estimators
        self._random_state = random_state
        self._model = None
        self._is_fitted = False

    def fit(self, feature_matrix: np.ndarray) -> None:
        from sklearn.ensemble import IsolationForest

        if feature_matrix.shape[0] < 10:
            logger.warning(
                "isolation_forest.insufficient_data",
                samples=feature_matrix.shape[0],
            )
            return

        self._model = IsolationForest(
            contamination=self._contamination,
            n_estimators=self._n_estimators,
            random_state=self._random_state,
            n_jobs=-1,
        )
        self._model.fit(feature_matrix)
        self._is_fitted = True

        logger.info(
            "isolation_forest.fitted",
            samples=feature_matrix.shape[0],
            features=feature_matrix.shape[1],
        )

    def predict(self, features: np.ndarray) -> AnomalyResult:
        if not self._is_fitted or self._model is None:
            logger.warning("isolation_forest.not_fitted")
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                features_used=self.FEATURE_NAMES,
                model_type="isolation_forest",
                details={"reason": "model_not_fitted"},
            )

        features_2d = features.reshape(1, -1)
        prediction = int(self._model.predict(features_2d)[0])
        score = float(self._model.score_samples(features_2d)[0])
        is_anomaly = prediction == -1

        logger.debug(
            "isolation_forest.prediction",
            is_anomaly=is_anomaly,
            score=round(score, 4),
        )

        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=round(score, 4),
            features_used=self.FEATURE_NAMES,
            model_type="isolation_forest",
            details={
                "raw_prediction": prediction,
                "anomaly_score": round(score, 4),
            },
        )

    def predict_batch(self, feature_matrix: np.ndarray) -> list[AnomalyResult]:
        return [self.predict(row) for row in feature_matrix]

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted
