import structlog
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session

from backend.repositories.dashboard_repository import AlertRepository
from backend.schemas.dashboard import AlertResponse, AlertListResponse

logger = structlog.get_logger(__name__)


@dataclass
class AlertThreshold:
    erro_balanco_pct_alto: float = 20.0
    erro_balanco_pct_critico: float = 35.0
    anomalias_ativas_medio: int = 3
    anomalias_ativas_alto: int = 8
    confianca_minima: float = 0.60
    kwp_delta_suspeito_pct: float = 25.0


class AlertService:
    """
    Avalia thresholds sobre snapshots e registros de validação,
    dispara alertas quando violações são detectadas,
    e gerencia o ciclo de vida dos alertas (aberto → reconhecido → resolvido).
    """

    def __init__(self, db: Session, thresholds: Optional[AlertThreshold] = None):
        self._db = db
        self._repo = AlertRepository(db)
        self._th = thresholds or AlertThreshold()

    def evaluate_snapshot(self, snapshot_data: dict) -> list[AlertResponse]:
        """
        Avalia um snapshot e cria alertas para violações encontradas.
        Retorna lista de alertas criados nesta avaliação.
        """
        transformer_id = snapshot_data["transformer_id"]
        alerts_created = []

        # ── Erro de balanço ────────────────────────────────────────────────
        erro_pct = snapshot_data.get("erro_balanco_pct")
        if erro_pct is not None:
            if erro_pct >= self._th.erro_balanco_pct_critico:
                alert = self._create_alert(
                    transformer_id=transformer_id,
                    alert_type="erro_balanco_critico",
                    severity="critico",
                    title=f"Erro de balanço crítico: {erro_pct:.1f}%",
                    message=(
                        f"O transformador {transformer_id} apresenta erro de balanço "
                        f"de {erro_pct:.1f}%, acima do limite crítico de "
                        f"{self._th.erro_balanco_pct_critico}%. "
                        "Inspeção imediata recomendada."
                    ),
                    threshold_value=self._th.erro_balanco_pct_critico,
                    observed_value=erro_pct,
                )
                alerts_created.append(alert)

            elif erro_pct >= self._th.erro_balanco_pct_alto:
                alert = self._create_alert(
                    transformer_id=transformer_id,
                    alert_type="erro_balanco_alto",
                    severity="alto",
                    title=f"Erro de balanço elevado: {erro_pct:.1f}%",
                    message=(
                        f"O transformador {transformer_id} apresenta erro de balanço "
                        f"de {erro_pct:.1f}%, acima do limite de "
                        f"{self._th.erro_balanco_pct_alto}%. "
                        "Monitoramento intensivo recomendado."
                    ),
                    threshold_value=self._th.erro_balanco_pct_alto,
                    observed_value=erro_pct,
                )
                alerts_created.append(alert)

        # ── Anomalias ativas ───────────────────────────────────────────────
        anomalias = snapshot_data.get("total_anomalias_ativas", 0)
        if anomalias >= self._th.anomalias_ativas_alto:
            alert = self._create_alert(
                transformer_id=transformer_id,
                alert_type="anomalias_multiplas",
                severity="alto",
                title=f"Alto volume de anomalias ativas: {anomalias}",
                message=(
                    f"{anomalias} anomalias energéticas ativas detectadas "
                    f"no transformador {transformer_id}. "
                    "Revisão do cluster prioritária."
                ),
                threshold_value=float(self._th.anomalias_ativas_alto),
                observed_value=float(anomalias),
            )
            alerts_created.append(alert)

        elif anomalias >= self._th.anomalias_ativas_medio:
            alert = self._create_alert(
                transformer_id=transformer_id,
                alert_type="anomalias_detectadas",
                severity="medio",
                title=f"Anomalias energéticas detectadas: {anomalias}",
                message=(
                    f"{anomalias} anomalias ativas no transformador "
                    f"{transformer_id}. Investigação recomendada."
                ),
                threshold_value=float(self._th.anomalias_ativas_medio),
                observed_value=float(anomalias),
            )
            alerts_created.append(alert)

        # ── Confiança baixa ────────────────────────────────────────────────
        confianca = snapshot_data.get("confianca_media_deteccao")
        if confianca is not None and confianca < self._th.confianca_minima:
            alert = self._create_alert(
                transformer_id=transformer_id,
                alert_type="baixa_confianca_deteccao",
                severity="medio",
                title=f"Confiança de detecção baixa: {confianca:.0%}",
                message=(
                    f"A confiança média de detecção FV do transformador "
                    f"{transformer_id} é {confianca:.0%}, abaixo do mínimo "
                    f"de {self._th.confianca_minima:.0%}. "
                    "Reprocessar imagens ou revisar modelo."
                ),
                threshold_value=self._th.confianca_minima,
                observed_value=confianca,
            )
            alerts_created.append(alert)

        # ── Score crítico ──────────────────────────────────────────────────
        if snapshot_data.get("score_operacional") == "prioridade_inspecao":
            alert = self._create_alert(
                transformer_id=transformer_id,
                alert_type="score_prioridade_inspecao",
                severity="critico",
                title="Transformador com prioridade de inspeção",
                message=(
                    f"O transformador {transformer_id} atingiu o score "
                    f"'prioridade_inspecao'. Inspeção de campo obrigatória."
                ),
                threshold_value=None,
                observed_value=None,
                metadata={"score": "prioridade_inspecao"},
            )
            alerts_created.append(alert)

        logger.info(
            "alert_service.evaluated",
            transformer_id=transformer_id,
            alerts_created=len(alerts_created),
        )
        return alerts_created

    def list_open_alerts(
        self,
        transformer_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> AlertListResponse:
        records = self._repo.list_open(transformer_id, severity, limit)
        counts = {}
        if transformer_id:
            counts = self._repo.count_open_by_severity(transformer_id)

        return AlertListResponse(
            total=len(records),
            criticos=counts.get("critico", 0),
            altos=counts.get("alto", 0),
            medios=counts.get("medio", 0),
            alerts=[AlertResponse.model_validate(r) for r in records],
        )

    def acknowledge_alert(
        self, alert_id: int, acknowledged_by: str
    ) -> Optional[AlertResponse]:
        record = self._repo.acknowledge(alert_id, acknowledged_by)
        return AlertResponse.model_validate(record) if record else None

    def resolve_alert(
        self, alert_id: int, notes: Optional[str] = None
    ) -> Optional[AlertResponse]:
        record = self._repo.resolve(alert_id, notes)
        return AlertResponse.model_validate(record) if record else None

    def _create_alert(
        self,
        transformer_id: str,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        threshold_value: Optional[float],
        observed_value: Optional[float],
        uc_code: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AlertResponse:
        record = self._repo.create({
            "transformer_id": transformer_id,
            "uc_code": uc_code,
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "message": message,
            "threshold_value": threshold_value,
            "observed_value": observed_value,
            "status": "aberto",
            "alert_metadata": metadata,
        })
        logger.warning(
            "alert_service.alert_created",
            transformer_id=transformer_id,
            alert_type=alert_type,
            severity=severity,
        )
        return AlertResponse.model_validate(record)
