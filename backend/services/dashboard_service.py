import structlog
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from backend.repositories.dashboard_repository import (
    DashboardRepository,
    AlertRepository,
)
from backend.repositories.calibration_repository import CalibrationRepository
from backend.repositories.validation_repository import (
    ValidationRepository,
    AnomalyRepository,
)
from backend.schemas.dashboard import (
    SnapshotRequest,
    SnapshotResponse,
    GlobalKPIsResponse,
    RankingResponse,
    RankingItemResponse,
    ErrorSeriesResponse,
    ErrorSeriesPoint,
    CalibrationSeriesResponse,
    CalibrationSeriesPoint,
    AnomalySeriesResponse,
    AnomalySeriesPoint,
    MapResponse,
    MapFeature,
    MapFeatureProperties,
)

logger = structlog.get_logger(__name__)


class DashboardService:
    """
    Orquestra todos os dados do dashboard executivo.
    Consolida KPIs, rankings, séries temporais e mapa energético
    a partir dos dados gerados pelos atos anteriores.
    """

    def __init__(self, db: Session):
        self._db = db
        self._dash_repo = DashboardRepository(db)
        self._alert_repo = AlertRepository(db)
        self._calib_repo = CalibrationRepository(db)
        self._val_repo = ValidationRepository(db)
        self._anomaly_repo = AnomalyRepository(db)

    # ── Snapshot ───────────────────────────────────────────────────────────

    def generate_snapshot(self, request: SnapshotRequest) -> SnapshotResponse:
        logger.info(
            "dashboard_service.generate_snapshot",
            transformer_id=request.transformer_id,
            period=request.reference_period,
        )

        cobertura = (
            round(request.total_ucs_fv / request.total_ucs * 100, 1)
            if request.total_ucs > 0
            else 0.0
        )

        latest_calib = self._calib_repo.get_latest(request.transformer_id)
        anomaly_count = self._anomaly_repo.get_unresolved_count(
            request.transformer_id
        )
        open_alerts = len(
            self._alert_repo.list_open(request.transformer_id)
        )

        data = {
            "transformer_id": request.transformer_id,
            "reference_period": request.reference_period,
            "total_ucs": request.total_ucs,
            "total_ucs_fv": request.total_ucs_fv,
            "cobertura_fv_pct": cobertura,
            "kwp_total_estimado": request.kwp_total_estimado,
            "area_total_m2": request.area_total_m2,
            "geracao_total_kwh": request.geracao_total_kwh,
            "consumo_total_kwh": request.consumo_total_kwh,
            "injecao_total_kwh": request.injecao_total_kwh,
            "balanco_estimado_kwh": request.balanco_estimado_kwh,
            "balanco_real_kwh": request.balanco_real_kwh,
            "erro_balanco_pct": request.erro_balanco_pct,
            "kwp_factor_atual": (
                latest_calib.kwp_factor_new if latest_calib
                else request.kwp_factor_atual
            ),
            "loss_factor_atual": (
                latest_calib.loss_factor_new if latest_calib
                else request.loss_factor_atual
            ),
            "modelo_convergido": (
                latest_calib.converged if latest_calib else False
            ),
            "score_operacional": request.score_operacional,
            "total_anomalias_ativas": anomaly_count,
            "total_inspecoes_pendentes": open_alerts,
            "confianca_media_deteccao": request.confianca_media_deteccao,
            "snapshot_metadata": (
                {"coordinates": request.coordinates}
                if request.coordinates
                else None
            ),
        }

        record = self._dash_repo.upsert_snapshot(data)
        return SnapshotResponse.model_validate(record)

    # ── KPIs Globais ───────────────────────────────────────────────────────

    def get_global_kpis(self) -> GlobalKPIsResponse:
        logger.info("dashboard_service.global_kpis")
        kpis = self._dash_repo.get_global_kpis()
        return GlobalKPIsResponse(**kpis)

    # ── Ranking ────────────────────────────────────────────────────────────

    def get_risk_ranking(self, limit: int = 50) -> RankingResponse:
        logger.info("dashboard_service.risk_ranking", limit=limit)
        items = self._dash_repo.get_risk_ranking(limit=limit)
        return RankingResponse(
            total=len(items),
            items=[RankingItemResponse(**i) for i in items],
        )

    # ── Séries temporais ───────────────────────────────────────────────────

    def get_error_series(
        self, transformer_id: str, limit: int = 24
    ) -> ErrorSeriesResponse:
        data = self._dash_repo.get_error_series(transformer_id, limit=limit)
        return ErrorSeriesResponse(
            transformer_id=transformer_id,
            total_points=len(data),
            series=[ErrorSeriesPoint(**p) for p in data],
        )

    def get_calibration_series(
        self, transformer_id: str, limit: int = 24
    ) -> CalibrationSeriesResponse:
        data = self._dash_repo.get_kwp_calibration_series(
            transformer_id, limit=limit
        )
        return CalibrationSeriesResponse(
            transformer_id=transformer_id,
            total_cycles=len(data),
            series=[CalibrationSeriesPoint(**p) for p in data],
        )

    def get_anomaly_series(
        self, transformer_id: str, days: int = 90
    ) -> AnomalySeriesResponse:
        data = self._dash_repo.get_anomaly_series(transformer_id, days=days)
        total_anomalies = sum(1 for p in data if p["is_anomaly"])
        return AnomalySeriesResponse(
            transformer_id=transformer_id,
            days=days,
            total_events=len(data),
            total_anomalies=total_anomalies,
            series=[AnomalySeriesPoint(**p) for p in data],
        )

    # ── Mapa energético ────────────────────────────────────────────────────

    def get_map_data(self) -> MapResponse:
        logger.info("dashboard_service.map_data")
        raw = self._dash_repo.get_map_data()

        features = []
        for item in raw:
            coords = item.get("coordinates")
            geometry = None
            if coords and "lat" in coords and "lon" in coords:
                geometry = {
                    "type": "Point",
                    "coordinates": [coords["lon"], coords["lat"]],
                }

            features.append(
                MapFeature(
                    geometry=geometry,
                    properties=MapFeatureProperties(
                        transformer_id=item["transformer_id"],
                        score_operacional=item["score_operacional"],
                        kwp_total_estimado=item.get("kwp_total_estimado"),
                        total_ucs_fv=item.get("total_ucs_fv"),
                        erro_balanco_pct=item.get("erro_balanco_pct"),
                        total_anomalias_ativas=item.get("total_anomalias_ativas"),
                        reference_period=item.get("reference_period"),
                    ),
                )
            )

        return MapResponse(total_features=len(features), features=features)

    # ── Snapshot histórico ─────────────────────────────────────────────────

    def get_snapshot_history(
        self, transformer_id: str, limit: int = 12
    ) -> list[SnapshotResponse]:
        records = self._dash_repo.get_snapshot_history(transformer_id, limit=limit)
        return [SnapshotResponse.model_validate(r) for r in records]
