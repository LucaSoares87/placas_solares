"""
Endpoints do Dashboard — KPIs, mapa de risco, rankings, séries temporais,
detalhamento de UC e exportação de relatórios.

Todos os endpoints de leitura exigem autenticação.
Os endpoints de exportação exigem perfil Engineering ou acima.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import CurrentUser, EngineeringRequired
from backend.core.database import get_db_session
from backend.core.exceptions import EntityNotFoundException
from backend.schemas.common import APIResponse, PaginatedResponse
from backend.schemas.dashboard import (
    BalanceTimeSeriesResponse,
    ExportRequest,
    GDRankingResponse,
    GlobalKPIResponse,
    RiskMapResponse,
    TransformerSummaryResponse,
    UCDetailResponse,
)
from backend.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# KPIs Globais
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/kpis",
    response_model=APIResponse[GlobalKPIResponse],
    summary="KPIs Globais da Rede",
    description=(
        "Retorna indicadores agregados de toda a rede: totais de UCs, "
        "GD, cobertura de telemetria, geração/consumo estimados, "
        "saúde dos transformadores e contagem de anomalias abertas."
    ),
)
async def get_global_kpis(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> APIResponse[GlobalKPIResponse]:
    service = DashboardService(session)
    kpis = await service.get_global_kpis()
    return APIResponse(data=kpis, message="KPIs calculados com sucesso.")


# ─────────────────────────────────────────────────────────────────────────────
# Sumário de Transformadores
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/transformers",
    response_model=PaginatedResponse[TransformerSummaryResponse],
    summary="Lista Sumários de Transformadores",
)
async def list_transformer_summaries(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    score: Optional[str] = Query(
        None,
        description="Filtrar por score operacional: low | medium | high | critical",
        pattern="^(low|medium|high|critical)$",
    ),
    substation: Optional[str] = Query(None, max_length=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[TransformerSummaryResponse]:
    service = DashboardService(session)
    offset = (page - 1) * page_size
    items, total = await service.list_transformer_summaries(
        offset=offset,
        limit=page_size,
        score_filter=score,
        substation=substation,
    )
    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 1,
    )


@router.get(
    "/transformers/{transformer_id}",
    response_model=APIResponse[TransformerSummaryResponse],
    summary="Sumário de um Transformador",
)
async def get_transformer_summary(
    transformer_id: str = Path(..., min_length=2, max_length=30),
    _: CurrentUser = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> APIResponse[TransformerSummaryResponse]:
    service = DashboardService(session)
    summary = await service.get_transformer_summary(transformer_id)
    if not summary:
        raise EntityNotFoundException(
            message=f"Transformador '{transformer_id}' não encontrado.",
            details={"transformer_id": transformer_id},
        )
    return APIResponse(data=summary)


# ─────────────────────────────────────────────────────────────────────────────
# Mapa de Risco
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/risk-map",
    response_model=APIResponse[RiskMapResponse],
    summary="Mapa de Risco Georreferenciado",
    description=(
        "Retorna todos os transformadores com suas coordenadas, "
        "score operacional e contagem de anomalias abertas. "
        "Ideal para renderização em mapa interativo (Leaflet / Mapbox)."
    ),
)
async def get_risk_map(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    score: Optional[str] = Query(
        None,
        description="Filtrar pontos por score: low | medium | high | critical",
        pattern="^(low|medium|high|critical)$",
    ),
) -> APIResponse[RiskMapResponse]:
    service = DashboardService(session)
    risk_map = await service.get_risk_map(score_filter=score)
    return APIResponse(
        data=risk_map,
        message=f"{risk_map.total} transformadores no mapa.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Ranking de GD
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/gd-ranking",
    response_model=APIResponse[GDRankingResponse],
    summary="Ranking de Geração Distribuída",
    description=(
        "Lista UCs com GD ordenadas por geração estimada (maior primeiro). "
        "Suporta filtro por transformador e mínimo de geração."
    ),
)
async def get_gd_ranking(
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    transformer_id: Optional[str] = Query(None, max_length=30),
    min_generation_kw: Optional[float] = Query(None, ge=0.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> APIResponse[GDRankingResponse]:
    service = DashboardService(session)
    ranking = await service.get_gd_ranking(
        page=page,
        page_size=page_size,
        transformer_id=transformer_id,
        min_generation_kw=min_generation_kw,
    )
    return APIResponse(
        data=ranking,
        message=f"{ranking.total} UCs com GD encontradas.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Série Temporal de Balanços
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/transformers/{transformer_id}/balance-series",
    response_model=APIResponse[BalanceTimeSeriesResponse],
    summary="Série Temporal de Balanços",
    description=(
        "Retorna o histórico de balanços energéticos de um transformador, "
        "com estatísticas de erro percentual ao longo do tempo."
    ),
)
async def get_balance_time_series(
    transformer_id: str = Path(..., min_length=2, max_length=30),
    _: CurrentUser = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
    start: Optional[datetime] = Query(
        None, description="ISO 8601, ex: 2025-01-01T00:00:00Z"
    ),
    end: Optional[datetime] = Query(
        None, description="ISO 8601, ex: 2025-03-31T23:59:59Z"
    ),
    limit: int = Query(
        default=90, ge=1, le=365,
        description="Máximo de pontos retornados (padrão: 90 dias)",
    ),
) -> APIResponse[BalanceTimeSeriesResponse]:
    service = DashboardService(session)
    series = await service.get_balance_time_series(
        transformer_id=transformer_id,
        start=start,
        end=end,
        limit=limit,
    )
    return APIResponse(
        data=series,
        message=f"{series.total_points} pontos na série temporal.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Detalhamento de UC
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/uc/{uc_code}",
    response_model=APIResponse[UCDetailResponse],
    summary="Detalhamento de Unidade Consumidora",
    description=(
        "Retorna dados cadastrais, última inferência energética "
        "e anomalias abertas de uma UC."
    ),
)
async def get_uc_detail(
    uc_code: str = Path(..., min_length=2, max_length=20),
    _: CurrentUser = None,
    session: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> APIResponse[UCDetailResponse]:
    service = DashboardService(session)
    detail = await service.get_uc_detail(uc_code)
    if not detail:
        raise EntityNotFoundException(
            message=f"UC '{uc_code}' não encontrada.",
            details={"uc_code": uc_code},
        )
    return APIResponse(data=detail)


# ─────────────────────────────────────────────────────────────────────────────
# Exportação de Relatórios
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/export",
    summary="Exportar Relatório",
    description=(
        "Gera e retorna um relatório em CSV ou JSON conforme o tipo solicitado. "
        "Requer perfil Engineering."
    ),
    dependencies=[EngineeringRequired],
)
async def export_report(
    body: ExportRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    service = DashboardService(session)

    content: str | bytes
    media_type: str
    filename: str

    if body.report_type == "transformer_balance":
        content, media_type = await service.export_transformer_balances(
            body.transformer_id, body.period_start, body.period_end, body.format
        )
        filename = f"transformer_balance.{body.format}"

    elif body.report_type == "anomalies":
        content, media_type = await service.export_anomalies(
            body.transformer_id,
            body.include_resolved_anomalies,
            body.format,
        )
        filename = f"anomalies.{body.format}"

    elif body.report_type == "uc_inferences":
        content, media_type = await service.export_inferences(
            body.transformer_id, body.period_start, body.period_end, body.format
        )
        filename = f"uc_inferences.{body.format}"

    else:
        from backend.core.exceptions import ValidationException
        raise ValidationException(
            message=f"Tipo de relatório '{body.report_type}' não suportado.",
            details={"report_type": body.report_type},
        )

    logger.info(
        "dashboard.export",
        report_type=body.report_type,
        format=body.format,
        transformer_id=body.transformer_id,
    )

    return Response(
        content=content if isinstance(content, bytes) else content.encode("utf-8"),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Type": body.report_type,
        },
    )
