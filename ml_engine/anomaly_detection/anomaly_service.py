import structlog
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from ml_engine.anomaly_detection.isolation_forest import (
    IsolationForestDetector,
    AnomalyResult,
)
from ml_engine.anomaly_detection.one_class_svm import OneClassSVMDetector

logger = structlog.get_logger(__name__)


@dataclass
class EnergyFeatureVector:
    consumo_estimado_kwh: float
    geracao_estimada_kwh: float
    injecao_estimada_kwh: float
    erro_balanco_pct: float
    kwp_estimado: float
    area_m2: float
    confianca_deteccao: float

    def to_array(self) -> np.ndarray:
        return np.array([
            self.consumo_estimado_kwh,
            self.geracao_estimada_kwh,
            self.injecao_estimada_kwh,
            self.erro_balanco_pct,
            self.kwp_estimado,
            self.area_m2,
            self.confianca_deteccao,
        ], dtype=np.float64)


@dataclass
class CombinedAnomalyResult:
    uc_code: str
    is_anomaly: bool
    consensus: bool
    isolation_forest: AnomalyResult
    one_class_svm: AnomalyResult
    final_score: float
    recommendation: str
    features: dict = field(default_factory=dict)


class AnomalyDetectionService:
    """
    Orquestra Isolation Forest e One-Class SVM para detecção de anomalias.

    Estratégia de consenso:
        - Ambos detectam → anomalia confirmada
        - Apenas um detecta → anomalia suspeita
        - Nenhum detecta → normal

    O score final é a média dos scores normalizados dos dois modelos.
    """

    def __init__(self):
        self._if_detector = IsolationForestDetector()
        self._svm_detector = OneClassSVMDetector()

    def fit(self, feature_matrix: np.ndarray) -> None:
        logger.info("anomaly_service.fitting", samples=feature_matrix.shape[0])
        self._if_detector.fit(feature_matrix)
        self._svm_detector.fit(feature_matrix)
        logger.info("anomaly_service.fitted")

    def detect(
        self, uc_code: str, features: EnergyFeatureVector
    ) -> CombinedAnomalyResult:
        vec = features.to_array()

        if_result = self._if_detector.predict(vec)
        svm_result = self._svm_detector.predict(vec)

        consensus = if_result.is_anomaly and svm_result.is_anomaly
        any_anomaly = if_result.is_anomaly or svm_result.is_anomaly

        final_score = round(
            (abs(if_result.score) + abs(svm_result.score)) / 2, 4
        )

        recommendation = self._build_recommendation(
            consensus, any_anomaly, features
        )

        result = CombinedAnomalyResult(
            uc_code=uc_code,
            is_anomaly=any_anomaly,
            consensus=consensus,
            isolation_forest=if_result,
            one_class_svm=svm_result,
            final_score=final_score,
            recommendation=recommendation,
            features=vars(features),
        )

        logger.info(
            "anomaly_service.result",
            uc_code=uc_code,
            is_anomaly=any_anomaly,
            consensus=consensus,
            final_score=final_score,
        )

        return result

    def detect_batch(
        self, records: list[tuple[str, EnergyFeatureVector]]
    ) -> list[CombinedAnomalyResult]:
        return [self.detect(uc, feat) for uc, feat in records]

    def _build_recommendation(
        self,
        consensus: bool,
        any_anomaly: bool,
        features: EnergyFeatureVector,
    ) -> str:
        if consensus:
            if features.erro_balanco_pct > 30:
                return "inspecao_urgente"
            return "inspecao_prioritaria"
        if any_anomaly:
            return "monitoramento_intensivo"
        return "normal"

    @property
    def is_fitted(self) -> bool:
        return self._if_detector.is_fitted and self._svm_detector.is_fitted
