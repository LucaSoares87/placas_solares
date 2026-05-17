import structlog
from dataclasses import dataclass
from typing import Optional

logger = structlog.get_logger(__name__)


@dataclass
class KWpResult:
    kwp_estimated: float
    area_m2: float
    factor_used: float
    factor_source: str
    confidence_penalty: float
    kwp_adjusted: float


class KWpEstimator:
    """
    Estima potência instalada (kWp) a partir da área detectada em m²,
    utilizando fator de conversão calibrado por região, transformador ou cluster.

    Fórmula base:
        kWp = área_m2 × fator_calibrado

    O fator padrão da indústria é ~0.15 kWp/m² para painéis monocristalinos
    com eficiência ~15%, podendo variar de 0.10 a 0.20 conforme tecnologia e arranjo.
    """

    DEFAULT_FACTOR = 0.15  # kWp/m² — baseline monocristalino padrão
    MIN_KWP = 0.5
    MAX_KWP = 500.0

    def __init__(
        self,
        regional_factor: Optional[float] = None,
        transformer_factor: Optional[float] = None,
        cluster_factor: Optional[float] = None,
    ):
        self._regional_factor = regional_factor
        self._transformer_factor = transformer_factor
        self._cluster_factor = cluster_factor

    def estimate(
        self,
        area_m2: float,
        detection_confidence: float = 1.0,
    ) -> KWpResult:
        factor, source = self._select_factor()
        kwp_raw = area_m2 * factor
        kwp_raw = self._clamp(kwp_raw)

        confidence_penalty = self._calculate_confidence_penalty(detection_confidence)
        kwp_adjusted = round(kwp_raw * confidence_penalty, 3)

        logger.info(
            "kwp_estimator.result",
            area_m2=area_m2,
            factor=factor,
            source=source,
            kwp_raw=kwp_raw,
            confidence_penalty=confidence_penalty,
            kwp_adjusted=kwp_adjusted,
        )

        return KWpResult(
            kwp_estimated=round(kwp_raw, 3),
            area_m2=round(area_m2, 3),
            factor_used=factor,
            factor_source=source,
            confidence_penalty=round(confidence_penalty, 4),
            kwp_adjusted=kwp_adjusted,
        )

    def _select_factor(self) -> tuple[float, str]:
        """
        Hierarquia de seleção do fator:
        transformer > cluster > regional > default
        """
        if self._transformer_factor is not None:
            return self._transformer_factor, "transformer"
        if self._cluster_factor is not None:
            return self._cluster_factor, "cluster"
        if self._regional_factor is not None:
            return self._regional_factor, "regional"
        return self.DEFAULT_FACTOR, "default"

    def _clamp(self, kwp: float) -> float:
        return max(self.MIN_KWP, min(kwp, self.MAX_KWP))

    def _calculate_confidence_penalty(self, confidence: float) -> float:
        """
        Penaliza estimativa proporcionalmente à confiança da detecção.

        confidence >= 0.80 → sem penalidade (fator 1.0)
        confidence < 0.80  → penalidade linear até 0.70 (fator mínimo 0.80)
        """
        confidence = max(0.0, min(confidence, 1.0))
        if confidence >= 0.80:
            return 1.0
        penalty = 0.80 + (confidence / 0.80) * 0.20
        return round(penalty, 4)

    def update_transformer_factor(self, new_factor: float) -> None:
        logger.info("kwp_estimator.factor_updated", source="transformer", factor=new_factor)
        self._transformer_factor = new_factor

    def update_regional_factor(self, new_factor: float) -> None:
        logger.info("kwp_estimator.factor_updated", source="regional", factor=new_factor)
        self._regional_factor = new_factor
