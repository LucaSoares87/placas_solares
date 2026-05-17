import structlog
from dataclasses import dataclass
import numpy as np
from ml_engine.anomaly_detection.isolation_forest import AnomalyResult

logger = structlog.get_logger(__name__)


class OneClassSVMDetector:
    """
    Detector complementar ao Isolation Forest.
    Utilizado para validação cruzada de anomalias em conjuntos menores.

    Kernel RBF — adequado para distribuições energéticas não-lineares.
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

    def __init__(self, nu: float = 0.05, kernel: str = "rbf", gamma: str = "scale"):
        self._nu = nu
        self._kernel = kernel
        self._gamma = gamma
        self._model = None
        self._scaler = None
        self._is_fitted = False

    def fit(self, feature_matrix: np.ndarray) -> None:
        from sklearn.svm import OneClassSVM
        from sklearn.preprocessing import StandardScaler

        if feature_matrix.shape[0] < 10:
            logger.warning(
                "one_class_svm.insufficient_data",
                samples=feature_matrix.shape[0],
            )
            return

        self._scaler = StandardScaler()
        scaled = self._scaler.fit_transform(feature_matrix)

        self._model = OneClassSVM(
            nu=self._nu,
            kernel=self._kernel,
            gamma=self._gamma,
        )
        self._model.fit(scaled)
        self._is_fitted = True

        logger.info(
            "one_class_svm.fitted",
            samples=feature_matrix.shape[0],
            nu=self._nu,
        )

    def predict(self, features: np.ndarray) -> AnomalyResult:
        if not self._is_fitted or self._model is None or self._scaler is None:
            logger.warning("one_class_svm.not_fitted")
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                features_used=self.FEATURE_NAMES,
                model_type="one_class_svm",
                details={"reason": "model_not_fitted"},
            )

        features_2d = features.reshape(1, -1)
        scaled = self._scaler.transform(features_2d)
        prediction = int(self._model.predict(scaled)[0])
        score = float(self._model.score_samples(scaled)[0])
        is_anomaly = prediction == -1

        return AnomalyResult(
            is_anomaly=is_anomaly,
            score=round(score, 4),
            features_used=self.FEATURE_NAMES,
            model_type="one_class_svm",
            details={
                "raw_prediction": prediction,
                "decision_score": round(score, 4),
            },
        )

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted
