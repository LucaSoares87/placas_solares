from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.repositories.calibration_repository import CalibrationRepository
from backend.repositories.dashboard_repository import AlertRepository, DashboardRepository
from backend.repositories.validation_repository import AnomalyRepository, ValidationRepository
from backend.schemas.dashboard import (
    AnomalySeriesPoint,
    AnomalySeriesResponse,
    BalanceTimeSeriesPoint,
    BalanceTimeSeriesResponse,
    CalibrationSeriesPoint,
    CalibrationSeriesResponse,
    ErrorSeriesPoint,
    ErrorSeriesResponse,
    GDRankingItem,
    GDRankingResponse,
    GlobalKPIResponse,
    GlobalKPIsResponse,
    MapFeature,
    MapFeatureProperties,
    MapResponse,
    RankingItemResponse,
    RankingResponse,
    RiskMapFeature,
    RiskMapResponse,
    SnapshotRequest,
    SnapshotResponse,
    TransformerSummaryResponse,
    UCDetailResponse,
)

logger = structlog.get_logger(__name__)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default

    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_dict(item: Any) -> dict[str, Any]:
    if item is None:
        return {}

    if isinstance(item, dict):
        return dict(item)

    if hasattr(item, "model_dump"):
        return item.model_dump()

    if hasattr(item, "__dict__"):
        return {
            key: value
            for key, value in item.__dict__.items()
            if not key.startswith("_")
        }

    return {}


class DashboardService:
    def __init__(self, db: Session | AsyncSession):
        self._db = db
        self._dash_repo = DashboardRepository(db)
        self._alert_repo = AlertRepository(db)
        self._calib_repo = CalibrationRepository(db)
        self._val_repo = ValidationRepository(db)
        self._anomaly_repo = AnomalyRepository(db)
        self._repo = self._dash_repo

    async def generate_snapshot(self, request: SnapshotRequest) -> SnapshotResponse:
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

        latest_calib = await _maybe_await(
            self._calib_repo.get_latest(request.transformer_id)
        )
        anomaly_count = await _maybe_await(
            self._anomaly_repo.get_unresolved_count(request.transformer_id)
        )
        open_alerts = await _maybe_await(
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
                latest_calib.kwp_factor_new
                if latest_calib
                else request.kwp_factor_atual
            ),
            "loss_factor_atual": (
                latest_calib.loss_factor_new
                if latest_calib
                else request.loss_factor_atual
            ),
            "modelo_convergido": latest_calib.converged if latest_calib else False,
            "score_operacional": request.score_operacional,
            "total_anomalias_ativas": anomaly_count,
            "total_inspecoes_pendentes": len(open_alerts or []),
            "confianca_media_deteccao": request.confianca_media_deteccao,
            "snapshot_metadata": (
                {"coordinates": request.coordinates} if request.coordinates else None
            ),
        }

        record = await _maybe_await(self._dash_repo.upsert_snapshot(data))
        return SnapshotResponse.model_validate(record)

    async def get_global_kpis(self) -> GlobalKPIResponse:
        logger.info("dashboard_service.global_kpis")

        repo = getattr(self, "_repo", self._dash_repo)
        data = await _maybe_await(repo.get_global_kpis())

        total_transformers = _safe_int(
            _get_value(
                data,
                "total_transformers",
                _get_value(data, "total_transformadores", 0),
            )
        )
        total_consumer_units = _safe_int(
            _get_value(
                data,
                "total_consumer_units",
                _get_value(data, "total_ucs", 0),
            )
        )
        total_gd_units = _safe_int(
            _get_value(
                data,
                "total_gd_units",
                _get_value(
                    data,
                    "total_ucs_with_gd",
                    _get_value(data, "total_ucs_fv", 0),
                ),
            )
        )

        gd_penetration_rate = _safe_float(
            _get_value(data, "gd_penetration_rate", 0.0)
        )
        if gd_penetration_rate == 0.0 and total_consumer_units > 0:
            gd_penetration_rate = round(total_gd_units / total_consumer_units, 4)

        telemetry_coverage_rate = _safe_float(
            _get_value(data, "telemetry_coverage_rate", 0.0)
        )
        telemetry_coverage_pct = _safe_float(
            _get_value(data, "telemetry_coverage_pct", telemetry_coverage_rate * 100)
        )

        return GlobalKPIResponse(
            total_transformers=total_transformers,
            total_consumer_units=total_consumer_units,
            total_ucs=total_consumer_units,
            total_gd_units=total_gd_units,
            total_ucs_fv=total_gd_units,
            total_ucs_with_gd=total_gd_units,
            gd_penetration_rate=gd_penetration_rate,
            telemetry_coverage_rate=telemetry_coverage_rate,
            telemetry_coverage_pct=telemetry_coverage_pct,
            estimated_generation_kwh=_safe_float(
                _get_value(
                    data,
                    "estimated_generation_kwh",
                    _get_value(data, "geracao_total_kwh", 0.0),
                )
            ),
            estimated_consumption_kwh=_safe_float(
                _get_value(
                    data,
                    "estimated_consumption_kwh",
                    _get_value(data, "consumo_total_kwh", 0.0),
                )
            ),
            estimated_injection_kwh=_safe_float(
                _get_value(data, "estimated_injection_kwh", 0.0)
            ),
            active_anomalies=_safe_int(
                _get_value(
                    data,
                    "active_anomalies",
                    _get_value(data, "total_anomalias_ativas", 0),
                )
            ),
            critical_transformers=_safe_int(
                _get_value(
                    data,
                    "critical_transformers",
                    _get_value(data, "transformadores_criticos", 0),
                )
            ),
            transformers_balanced=_safe_int(
                _get_value(data, "transformers_balanced", 0)
            ),
            generated_at=_get_value(
                data,
                "generated_at",
                _get_value(data, "gerado_em", _utcnow()),
            ),
        )

    async def get_global_kpis_legacy(self) -> GlobalKPIsResponse:
        kpis = await self.get_global_kpis()
        cobertura_fv_pct = round(kpis.gd_penetration_rate * 100, 2)

        return GlobalKPIsResponse(
            total_transformadores=kpis.total_transformers,
            total_ucs=kpis.total_consumer_units,
            total_ucs_fv=kpis.total_gd_units,
            cobertura_fv_pct=cobertura_fv_pct,
            kwp_total=0.0,
            geracao_total_kwh=kpis.estimated_generation_kwh,
            consumo_total_kwh=kpis.estimated_consumption_kwh,
            erro_medio_balanco_pct=0.0,
            total_anomalias_ativas=kpis.active_anomalies,
            transformadores_criticos=kpis.critical_transformers,
            gerado_em=kpis.generated_at,
        )

    async def get_risk_ranking(self, limit: int = 50) -> RankingResponse:
        logger.info("dashboard_service.risk_ranking", limit=limit)

        repo = getattr(self, "_repo", self._dash_repo)
        items = await _maybe_await(repo.get_risk_ranking(limit=limit))

        return RankingResponse(
            total=len(items),
            items=[RankingItemResponse(**item) for item in items],
        )

    async def get_error_series(
        self,
        transformer_id: str,
        limit: int = 24,
    ) -> ErrorSeriesResponse:
        repo = getattr(self, "_repo", self._dash_repo)
        data = await _maybe_await(repo.get_error_series(transformer_id, limit=limit))

        return ErrorSeriesResponse(
            transformer_id=transformer_id,
            total_points=len(data),
            series=[ErrorSeriesPoint(**point) for point in data],
        )

    async def get_calibration_series(
        self,
        transformer_id: str,
        limit: int = 24,
    ) -> CalibrationSeriesResponse:
        repo = getattr(self, "_repo", self._dash_repo)
        data = await _maybe_await(
            repo.get_kwp_calibration_series(transformer_id, limit=limit)
        )

        return CalibrationSeriesResponse(
            transformer_id=transformer_id,
            total_cycles=len(data),
            series=[CalibrationSeriesPoint(**point) for point in data],
        )

    async def get_anomaly_series(
        self,
        transformer_id: str,
        days: int = 90,
    ) -> AnomalySeriesResponse:
        repo = getattr(self, "_repo", self._dash_repo)
        data = await _maybe_await(repo.get_anomaly_series(transformer_id, days=days))

        total_anomalies = sum(1 for point in data if point.get("is_anomaly"))

        return AnomalySeriesResponse(
            transformer_id=transformer_id,
            days=days,
            total_events=len(data),
            total_anomalies=total_anomalies,
            series=[AnomalySeriesPoint(**point) for point in data],
        )

    async def get_map_data(self) -> MapResponse:
        logger.info("dashboard_service.map_data")

        repo = getattr(self, "_repo", self._dash_repo)
        raw = await _maybe_await(repo.get_map_data())

        features = []

        for item in raw:
            coords = _get_value(item, "coordinates")
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
                        transformer_id=_get_value(item, "transformer_id", ""),
                        score_operacional=_get_value(
                            item,
                            "score_operacional",
                            _get_value(item, "operational_score", "low"),
                        ),
                        kwp_total_estimado=_get_value(item, "kwp_total_estimado"),
                        total_ucs_fv=_get_value(
                            item,
                            "total_ucs_fv",
                            _get_value(item, "gd_count"),
                        ),
                        erro_balanco_pct=_get_value(
                            item,
                            "erro_balanco_pct",
                            _get_value(item, "percentage_error"),
                        ),
                        total_anomalias_ativas=_get_value(
                            item,
                            "total_anomalias_ativas",
                            _get_value(item, "open_anomalies_count"),
                        ),
                        reference_period=_get_value(item, "reference_period"),
                    ),
                )
            )

        return MapResponse(total_features=len(features), features=features)

    async def get_snapshot_history(
        self,
        transformer_id: str,
        limit: int = 12,
    ) -> list[SnapshotResponse]:
        records = await _maybe_await(
            self._dash_repo.get_snapshot_history(transformer_id, limit=limit)
        )
        return [SnapshotResponse.model_validate(record) for record in records]

    async def get_transformer_summary(
        self,
        transformer_id: str,
    ) -> TransformerSummaryResponse | None:
        repo = getattr(self, "_repo", self._dash_repo)
        data = await _maybe_await(repo.get_transformer_summary(transformer_id))

        if not data:
            return None

        rated_kva = _safe_float(_get_value(data, "rated_kva", 0.0))
        measured_kwh = _safe_float(_get_value(data, "measured_kwh", 0.0))
        load_factor = round(measured_kwh / rated_kva, 4) if rated_kva else 0.0

        uc_count = _safe_int(_get_value(data, "uc_count", 0))
        gd_count = _safe_int(_get_value(data, "gd_count", 0))

        return TransformerSummaryResponse(
            transformer_id=_get_value(data, "transformer_id", transformer_id),
            substation=_get_value(data, "substation"),
            feeder=_get_value(data, "feeder"),
            latitude=_get_value(data, "latitude"),
            longitude=_get_value(data, "longitude"),
            rated_kva=rated_kva,
            load_factor=load_factor,
            load_factor_pct=round(load_factor * 100, 2),
            is_overloaded=load_factor > 1.0,
            uc_count=uc_count,
            gd_count=gd_count,
            telemetered_count=_safe_int(_get_value(data, "telemetered_count", 0)),
            total_consumer_units=_safe_int(
                _get_value(data, "total_consumer_units", uc_count)
            ),
            total_gd_units=_safe_int(_get_value(data, "total_gd_units", gd_count)),
            gd_penetration_rate=_safe_float(
                _get_value(data, "gd_penetration_rate", 0.0)
            ),
            telemetry_coverage_rate=_safe_float(
                _get_value(data, "telemetry_coverage_rate", 0.0)
            ),
            measured_kwh=measured_kwh,
            estimated_consumption_kwh=_safe_float(
                _get_value(data, "estimated_consumption_kwh", 0.0)
            ),
            estimated_generation_kwh=_safe_float(
                _get_value(data, "estimated_generation_kwh", 0.0)
            ),
            estimated_injection_kwh=_safe_float(
                _get_value(data, "estimated_injection_kwh", 0.0)
            ),
            technical_losses_kwh=_safe_float(
                _get_value(data, "technical_losses_kwh", 0.0)
            ),
            residual_kwh=_safe_float(_get_value(data, "residual_kwh", 0.0)),
            percentage_error=_safe_float(_get_value(data, "percentage_error", 0.0)),
            balance_error_pct=_get_value(
                data,
                "balance_error_pct",
                _get_value(data, "percentage_error"),
            ),
            balance_status=_get_value(data, "balance_status", "unknown"),
            operational_score=_get_value(data, "operational_score", "low"),
            open_anomalies_count=_safe_int(
                _get_value(data, "open_anomalies_count", 0)
            ),
            last_balance_computed_at=_get_value(data, "last_balance_computed_at"),
            last_inference_at=_get_value(data, "last_inference_at"),
            updated_at=_get_value(data, "updated_at"),
        )

    async def get_risk_map(self) -> RiskMapResponse:
        repo = getattr(self, "_repo", self._dash_repo)

        if hasattr(repo, "get_risk_map_points"):
            raw = await _maybe_await(repo.get_risk_map_points())
        else:
            raw = await _maybe_await(repo.get_map_data())

        features = []
        counts_by_score: dict[str, int] = {}

        for item in raw:
            score = _get_value(
                item,
                "operational_score",
                _get_value(item, "score_operacional", "low"),
            )
            counts_by_score[score] = counts_by_score.get(score, 0) + 1

            latitude = _get_value(item, "latitude")
            longitude = _get_value(item, "longitude")

            geometry = None
            if latitude is not None and longitude is not None:
                geometry = {
                    "type": "Point",
                    "coordinates": [longitude, latitude],
                }

            features.append(
                RiskMapFeature(
                    geometry=geometry,
                    properties={
                        "transformer_id": _get_value(item, "transformer_id"),
                        "operational_score": score,
                        "balance_status": _get_value(item, "balance_status"),
                        "open_anomalies_count": _safe_int(
                            _get_value(item, "open_anomalies_count", 0)
                        ),
                        "gd_count": _safe_int(_get_value(item, "gd_count", 0)),
                        "uc_count": _safe_int(_get_value(item, "uc_count", 0)),
                        "percentage_error": _safe_float(
                            _get_value(item, "percentage_error", 0.0)
                        ),
                        "last_computed_at": _get_value(item, "last_computed_at"),
                    },
                )
            )

        critical_count = counts_by_score.get("critical", 0)
        low_count = counts_by_score.get("low", 0)
        high_count = counts_by_score.get("high", 0)

        return RiskMapResponse(
            total=len(features),
            total_features=len(features),
            critical_count=critical_count,
            low_count=low_count,
            high_count=high_count,
            counts_by_score=counts_by_score,
            features=features,
            generated_at=_utcnow(),
        )

    async def get_gd_ranking(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> GDRankingResponse:
        repo = getattr(self, "_repo", self._dash_repo)
        result = await _maybe_await(repo.get_gd_ranking(page=page, page_size=page_size))

        if isinstance(result, tuple):
            items, total = result
        else:
            items = result or []
            total = len(items)

        ranking_items = []

        for index, item in enumerate(items):
            item_dict = _to_dict(item)
            rank = ((page - 1) * page_size) + index + 1

            ranking_items.append(
                GDRankingItem(
                    rank=rank,
                    uc_code=_get_value(item_dict, "uc_code", ""),
                    transformer_id=_get_value(item_dict, "transformer_id", ""),
                    address=_get_value(item_dict, "address"),
                    profile=_get_value(item_dict, "profile"),
                    gd_installed_kwp=_get_value(item_dict, "gd_installed_kwp"),
                    kwp_estimated=_get_value(item_dict, "kwp_estimated"),
                    estimated_kwp=_safe_float(
                        _get_value(
                            item_dict,
                            "estimated_kwp",
                            _get_value(item_dict, "kwp_estimated", 0.0),
                        )
                    ),
                    generation_kw=_get_value(item_dict, "generation_kw"),
                    estimated_generation_kwh=_safe_float(
                        _get_value(
                            item_dict,
                            "estimated_generation_kwh",
                            _get_value(item_dict, "generation_kw", 0.0),
                        )
                    ),
                    injection_kw_min=_get_value(item_dict, "injection_kw_min"),
                    injection_kw_max=_get_value(item_dict, "injection_kw_max"),
                    injection_kw_mid=_get_value(item_dict, "injection_kw_mid"),
                    injection_probability=_safe_float(
                        _get_value(item_dict, "injection_probability", 0.0)
                    ),
                    status=_get_value(item_dict, "status"),
                    confidence=_safe_float(_get_value(item_dict, "confidence", 0.0)),
                    operational_score=_get_value(
                        item_dict,
                        "operational_score",
                        "low",
                    ),
                    inference_method=_get_value(item_dict, "inference_method"),
                    last_computed_at=_get_value(item_dict, "last_computed_at"),
                )
            )

        total_generation_kw = round(
            sum(_safe_float(item.generation_kw) for item in ranking_items),
            4,
        )

        return GDRankingResponse(
            total=_safe_int(total),
            page=page,
            page_size=page_size,
            total_generation_kw=total_generation_kw,
            items=ranking_items,
            generated_at=_utcnow(),
        )

    async def get_balance_time_series(
        self,
        transformer_id: str,
        limit: int = 24,
    ) -> BalanceTimeSeriesResponse:
        repo = getattr(self, "_repo", self._dash_repo)
        records = await _maybe_await(
            repo.get_balance_time_series(transformer_id, limit=limit)
        )

        series = []
        errors = []

        for record in records:
            percentage_error = _safe_float(_get_value(record, "percentage_error", 0.0))
            errors.append(percentage_error)

            period_start = _get_value(record, "period_start")
            if hasattr(period_start, "isoformat"):
                period = period_start.isoformat()
            else:
                period = str(period_start) if period_start is not None else ""

            series.append(
                BalanceTimeSeriesPoint(
                    period=period,
                    period_end=_get_value(record, "period_end"),
                    measured_kwh=_safe_float(_get_value(record, "measured_kwh", 0.0)),
                    estimated_consumption_kwh=_safe_float(
                        _get_value(record, "estimated_consumption_kwh", 0.0)
                    ),
                    estimated_generation_kwh=_safe_float(
                        _get_value(record, "estimated_generation_kwh", 0.0)
                    ),
                    estimated_injection_kwh=_safe_float(
                        _get_value(record, "estimated_injection_kwh", 0.0)
                    ),
                    technical_losses_kwh=_safe_float(
                        _get_value(record, "technical_losses_kwh", 0.0)
                    ),
                    residual_kwh=_safe_float(
                        _get_value(record, "residual_kwh", 0.0)
                    ),
                    percentage_error=percentage_error,
                    erro_balanco_pct=percentage_error,
                    balance_status=_get_value(record, "balance_status"),
                    operational_score=_get_value(record, "operational_score"),
                    score_operacional=_get_value(record, "operational_score"),
                )
            )

        avg_error = round(sum(errors) / len(errors), 4) if errors else 0.0
        min_error = round(min(errors), 4) if errors else 0.0
        max_error = round(max(errors), 4) if errors else 0.0

        return BalanceTimeSeriesResponse(
            transformer_id=transformer_id,
            total_points=len(series),
            mean_percentage_error=avg_error,
            avg_percentage_error=avg_error,
            min_percentage_error=min_error,
            max_percentage_error=max_error,
            series=series,
            generated_at=_utcnow(),
        )

    async def get_uc_detail(self, uc_code: str) -> UCDetailResponse | None:
        repo = getattr(self, "_repo", self._dash_repo)
        data = await _maybe_await(repo.get_uc_detail(uc_code))

        if not data:
            return None

        item = _to_dict(data)

        return UCDetailResponse(
            uc_code=_get_value(item, "uc_code", uc_code),
            transformer_id=_get_value(item, "transformer_id", ""),
            has_gd=bool(_get_value(item, "has_gd", False)),
            estimated_kwp=_get_value(item, "estimated_kwp"),
            kwp_estimated=_get_value(item, "kwp_estimated"),
            estimated_generation_kwh=_get_value(item, "estimated_generation_kwh"),
            estimated_consumption_kwh=_get_value(item, "estimated_consumption_kwh"),
            estimated_injection_kwh=_get_value(item, "estimated_injection_kwh"),
            confidence=_get_value(item, "confidence"),
            operational_score=_get_value(item, "operational_score"),
            latitude=_get_value(item, "latitude"),
            longitude=_get_value(item, "longitude"),
            updated_at=_get_value(item, "updated_at"),
        )