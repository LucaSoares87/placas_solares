import structlog
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import numpy as np

logger = structlog.get_logger(__name__)


@dataclass
class FeedbackRecord:
    uc_code: str
    transformer_id: str
    timestamp: datetime
    kwp_estimated: float
    kwp_real: Optional[float]
    consumo_estimado_kwh: float
    consumo_real_kwh: Optional[float]
    geracao_estimada_kwh: float
    geracao_real_kwh: Optional[float]
    area_m2: float
    confianca: float
    source: str = "telemedido"


@dataclass
class FeedbackSummary:
    transformer_id: str
    total_records: int
    mean_kwp_error_pct: float
    mean_consumo_error_pct: float
    mean_geracao_error_pct: float
    coverage_pct: float
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class FeedbackCollector:
    """
    Coleta medições reais de UCs telemedidas para uso como ground truth
    no aprendizado contínuo do sistema.

    Clientes telemedidos funcionam como:
        - supervisão do ML
        - calibração de fatores
        - validação de estimativas
    """

    def __init__(self):
        self._records: list[FeedbackRecord] = []

    def add(self, record: FeedbackRecord) -> None:
        self._records.append(record)
        logger.debug(
            "feedback_collector.added",
            uc_code=record.uc_code,
            source=record.source,
        )

    def add_batch(self, records: list[FeedbackRecord]) -> None:
        for record in records:
            self.add(record)
        logger.info(
            "feedback_collector.batch_added",
            count=len(records),
        )

    def get_by_transformer(self, transformer_id: str) -> list[FeedbackRecord]:
        return [
            r for r in self._records if r.transformer_id == transformer_id
        ]

    def summarize(self, transformer_id: str) -> Optional[FeedbackSummary]:
        records = self.get_by_transformer(transformer_id)
        if not records:
            return None

        kwp_errors = []
        consumo_errors = []
        geracao_errors = []

        for r in records:
            if r.kwp_real and r.kwp_real > 0:
                kwp_errors.append(
                    abs(r.kwp_estimated - r.kwp_real) / r.kwp_real * 100
                )
            if r.consumo_real_kwh and r.consumo_real_kwh > 0:
                consumo_errors.append(
                    abs(r.consumo_estimado_kwh - r.consumo_real_kwh)
                    / r.consumo_real_kwh * 100
                )
            if r.geracao_real_kwh and r.geracao_real_kwh > 0:
                geracao_errors.append(
                    abs(r.geracao_estimada_kwh - r.geracao_real_kwh)
                    / r.geracao_real_kwh * 100
                )

        timestamps = [r.timestamp for r in records]

        return FeedbackSummary(
            transformer_id=transformer_id,
            total_records=len(records),
            mean_kwp_error_pct=round(float(np.mean(kwp_errors)), 2) if kwp_errors else 0.0,
            mean_consumo_error_pct=round(float(np.mean(consumo_errors)), 2) if consumo_errors else 0.0,
            mean_geracao_error_pct=round(float(np.mean(geracao_errors)), 2) if geracao_errors else 0.0,
            coverage_pct=round(len(kwp_errors) / len(records) * 100, 1),
            period_start=min(timestamps),
            period_end=max(timestamps),
        )

    def to_feature_matrix(self, transformer_id: str) -> np.ndarray:
        records = self.get_by_transformer(transformer_id)
        rows = []
        for r in records:
            rows.append([
                r.consumo_estimado_kwh,
                r.geracao_estimada_kwh,
                r.kwp_estimated,
                r.area_m2,
                r.confianca,
            ])
        return np.array(rows, dtype=np.float64) if rows else np.empty((0, 5))

    def clear(self, transformer_id: Optional[str] = None) -> None:
        if transformer_id:
            self._records = [
                r for r in self._records
                if r.transformer_id != transformer_id
            ]
        else:
            self._records.clear()
