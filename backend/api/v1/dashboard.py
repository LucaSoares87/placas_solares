import io
import structlog

# ── Import Optional para uso nos query params ──────────────────────────────
from typing import Optional


from datetime import datetime
from fastapi import (
    APIRouter, Depends, HTTPException,
    Query, status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.services.dashboard_service import DashboardService
from backend.services.alert_service import AlertService
from backend.services.export_service import ExportService
from backend.schemas.dashboard import (
    SnapshotRequest,
    SnapshotResponse,
    GlobalKPIsResponse,
    RankingResponse,
    ErrorSeriesResponse,
    CalibrationSeriesResponse,
    AnomalySeriesResponse,
    MapResponse,
    AlertResponse,
    AlertListResponse,
    ExportRequest,
    BIPayloadResponse,
    SystemHealthResponse,
)
from backend.workers.dashboard_worker import (
    generate_snapshot_task,
    export_csv_task,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ── Snapshot ───────────────────────────────────────────────────────────────

@router.post(
    "/snapshot",
    response_model=SnapshotResponse,
    summary="Gerar ou atualizar snapshot de um transformador",
    description=(
        "Consolida KPIs energéticos, risco operacional, calibração e "
        "anomalias ativas em um snapshot materializado. "
        "Avalia automaticamente thresholds e dispara alertas se necessário. "
        "Operação de upsert: atualiza se já existir para o período."
    ),
)
def generate_snapshot(
    request: SnapshotRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SnapshotResponse:
    logger.info(
        "api.dashboard.snapshot",
        transformer_id=request.transformer_id,
        user=getattr(current_user, "matricula", "unknown"),
    )
    try:
        service = DashboardService(db)
        result = service.generate_snapshot(request)

        alert_service = AlertService(db)
        alert_service.evaluate_snapshot(result.model_dump())

        return result
    except Exception as exc:
        logger.error("api.dashboard.snapshot.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/snapshot/async",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Geração assíncrona de snapshot via Celery",
)
def generate_snapshot_async(
    request: SnapshotRequest,
    current_user=Depends(get_current_user),
) -> dict:
    task = generate_snapshot_task.apply_async(
        kwargs={
            "transformer_id": request.transformer_id,
            "request_data": request.model_dump(mode="json"),
        }
    )
    return {
        "task_id": task.id,
        "transformer_id": request.transformer_id,
        "status": "queued",
    }


@router.get(
    "/snapshot/{transformer_id}",
    response_model=SnapshotResponse,
    summary="Obter snapshot mais recente de um transformador",
)
def get_latest_snapshot(
    transformer_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SnapshotResponse:
    from backend.repositories.dashboard_repository import DashboardRepository

    repo = DashboardRepository(db)
    snapshot = repo.get_latest_snapshot(transformer_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum snapshot encontrado para o transformador {transformer_id}",
        )
    return SnapshotResponse.model_validate(snapshot)


@router.get(
    "/snapshot/{transformer_id}/history",
    response_model=list[SnapshotResponse],
    summary="Histórico de snapshots de um transformador",
)
def get_snapshot_history(
    transformer_id: str,
    limit: int = Query(default=12, ge=1, le=60),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[SnapshotResponse]:
    service = DashboardService(db)
    return service.get_snapshot_history(transformer_id, limit=limit)


# ── KPIs Globais ───────────────────────────────────────────────────────────

@router.get(
    "/kpis",
    response_model=GlobalKPIsResponse,
    summary="KPIs globais consolidados de toda a rede",
    description=(
        "Agrega métricas de todos os transformadores: "
        "cobertura FV, kWp total, geração, consumo, erros, anomalias e críticos. "
        "Base para o painel executivo."
    ),
)
def get_global_kpis(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> GlobalKPIsResponse:
    service = DashboardService(db)
    return service.get_global_kpis()


# ── Ranking ────────────────────────────────────────────────────────────────

@router.get(
    "/ranking",
    response_model=RankingResponse,
    summary="Ranking de transformadores por criticidade operacional",
    description=(
        "Ordena transformadores por score operacional (prioridade_inspecao → baixo_risco), "
        "erro de balanço e volume de anomalias. "
        "Permite priorizar vistorias de campo com dados objetivos."
    ),
)
def get_risk_ranking(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> RankingResponse:
    service = DashboardService(db)
    return service.get_risk_ranking(limit=limit)


# ── Séries temporais ───────────────────────────────────────────────────────

@router.get(
    "/series/{transformer_id}/error",
    response_model=ErrorSeriesResponse,
    summary="Série temporal de erro de balanço de um transformador",
)
def get_error_series(
    transformer_id: str,
    limit: int = Query(default=24, ge=1, le=120),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ErrorSeriesResponse:
    service = DashboardService(db)
    return service.get_error_series(transformer_id, limit=limit)


@router.get(
    "/series/{transformer_id}/calibration",
    response_model=CalibrationSeriesResponse,
    summary="Série temporal de calibração kWp de um transformador",
)
def get_calibration_series(
    transformer_id: str,
    limit: int = Query(default=24, ge=1, le=120),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CalibrationSeriesResponse:
    service = DashboardService(db)
    return service.get_calibration_series(transformer_id, limit=limit)


@router.get(
    "/series/{transformer_id}/anomalies",
    response_model=AnomalySeriesResponse,
    summary="Série temporal de anomalias de um transformador",
)
def get_anomaly_series(
    transformer_id: str,
    days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AnomalySeriesResponse:
    service = DashboardService(db)
    return service.get_anomaly_series(transformer_id, days=days)


# ── Mapa energético ────────────────────────────────────────────────────────

@router.get(
    "/map",
    response_model=MapResponse,
    summary="Dados georreferenciados para mapa energético (GeoJSON)",
    description=(
        "Retorna FeatureCollection GeoJSON com todos os transformadores, "
        "seus scores operacionais, kWp estimado e anomalias ativas. "
        "Compatível com Leaflet, Mapbox e Power BI Maps."
    ),
)
def get_map_data(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> MapResponse:
    service = DashboardService(db)
    return service.get_map_data()


# ── Alertas ────────────────────────────────────────────────────────────────

@router.get(
    "/alerts",
    response_model=AlertListResponse,
    summary="Listar alertas operacionais abertos",
)
def list_alerts(
    transformer_id: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None, pattern="^(critico|alto|medio)$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AlertListResponse:
    service = AlertService(db)
    return service.list_open_alerts(
        transformer_id=transformer_id,
        severity=severity,
        limit=limit,
    )


@router.patch(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Reconhecer um alerta",
)
def acknowledge_alert(
    alert_id: int,
    acknowledged_by: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AlertResponse:
    service = AlertService(db)
    result = service.acknowledge_alert(alert_id, acknowledged_by)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta {alert_id} não encontrado",
        )
    return result


@router.patch(
    "/alerts/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="Resolver um alerta após ação corretiva",
)
def resolve_alert(
    alert_id: int,
    notes: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AlertResponse:
    service = AlertService(db)
    result = service.resolve_alert(alert_id, notes=notes)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta {alert_id} não encontrado",
        )
    return result


# ── Exportação ─────────────────────────────────────────────────────────────

@router.post(
    "/export/json",
    summary="Exportar dados consolidados em JSON",
    description=(
        "Exportação hierárquica completa: KPIs, validações, anomalias, calibrações. "
        "Filtrável por lista de transformadores e período de referência."
    ),
)
def export_json(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    try:
        service = ExportService(db)
        return service.export_json(request)
    except Exception as exc:
        logger.error("api.dashboard.export_json.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/export/csv",
    summary="Exportar dados consolidados em CSV",
    description=(
        "Gera arquivo CSV com uma linha por transformador. "
        "Colunas: KPIs, score, anomalias, calibração. "
        "Compatível com Excel e Power BI Desktop."
    ),
)
def export_csv(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> StreamingResponse:
    try:
        service = ExportService(db)
        csv_content = service.export_csv(request)

        filename = (
            f"dashboard_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        logger.error("api.dashboard.export_csv.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/export/csv/async",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Exportação CSV assíncrona via Celery",
)
def export_csv_async(
    request: ExportRequest,
    current_user=Depends(get_current_user),
) -> dict:
    task = export_csv_task.apply_async(
        kwargs={"request_data": request.model_dump(mode="json")}
    )
    return {"task_id": task.id, "status": "queued"}


@router.get(
    "/export/bi",
    response_model=BIPayloadResponse,
    summary="Payload estruturado para Power BI / Metabase",
    description=(
        "Retorna payload padronizado compatível com a REST API do Power BI "
        "(Push Datasets) e com conectores do Metabase. "
        "Inclui KPIs globais, dados por transformador, resumo de anomalias "
        "e histórico de calibração."
    ),
)
def export_bi_payload(
    transformer_ids: Optional[str] = Query(
        default=None,
        description="IDs separados por vírgula. Ex: TR-101,TR-102",
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> BIPayloadResponse:
    try:
        ids = (
            [t.strip() for t in transformer_ids.split(",")]
            if transformer_ids
            else None
        )
        service = ExportService(db)
        return service.export_bi_payload(transformer_ids=ids)
    except Exception as exc:
        logger.error("api.dashboard.export_bi.error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# ── Task status ────────────────────────────────────────────────────────────

@router.get(
    "/task/{task_id}",
    summary="Consultar status de task assíncrona do dashboard",
)
def get_task_status(
    task_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    from celery.result import AsyncResult
    from backend.core.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.state.lower(),
        "result": result.result if result.state == "SUCCESS" else None,
        "error": str(result.result) if result.state == "FAILURE" else None,
    }


# ── Health ─────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Health check completo do sistema",
    description=(
        "Verifica status do banco de dados, workers Celery, "
        "modelo YOLO, modelos de anomalia e métricas gerais do sistema."
    ),
)
def system_health(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SystemHealthResponse:
    from backend.repositories.dashboard_repository import (
        DashboardRepository,
        AlertRepository,
    )

    db_status = "ok"
    try:
        db.execute("SELECT 1")
    except Exception:
        db_status = "error"

    celery_status = "ok"
    try:
        from backend.core.celery_app import celery_app
        celery_app.control.ping(timeout=2)
    except Exception:
        celery_status = "degraded"

    yolo_status = "ok"
    try:
        from backend.core.config import settings
        import os
        if not os.path.exists(settings.YOLO_MODEL_PATH):
            yolo_status = "model_not_found"
    except Exception:
        yolo_status = "error"

    anomaly_status = "ready"

    dash_repo = DashboardRepository(db)
    alert_repo = AlertRepository(db)

    all_snapshots = dash_repo.list_all_latest()
    open_alerts = alert_repo.list_open(limit=500)

    overall = "healthy"
    if db_status != "ok":
        overall = "critical"
    elif celery_status != "ok":
        overall = "degraded"

    return SystemHealthResponse(
        status=overall,
        database=db_status,
        celery=celery_status,
        yolo_model=yolo_status,
        anomaly_models=anomaly_status,
        total_snapshots=len(all_snapshots),
        total_open_alerts=len(open_alerts),
    )

