from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.dependencies import CurrentUser, EngineeringRequired
from backend.core.database import get_db_session
from backend.schemas.common import APIResponse, PaginatedResponse, PaginationParams
from backend.schemas.energy_inference import (
    EnergyInferenceCreate,
    EnergyInferenceResponse,
    EnergyInferenceSummary,
    EnergyInferenceUpdate,
)
from backend.schemas.transformer_balance import (
    TransformerBalanceResponse,
)
from backend.services.energy_inference_service import EnergyInferenceService

router = APIRouter(prefix="/energy", tags=["Inferência Energética"])
logger = structlog.get_logger(__name__)


@router.post(
    "/inferences",
    response_model=APIResponse[EnergyInferenceResponse],
    dependencies=[EngineeringRequired],
)
async def register_inference(
    body: EnergyInferenceCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = EnergyInferenceService(session)
    result = await service.register_inference(body)
    return APIResponse(
        data=EnergyInferenceResponse.from_model(result),
        message="Inferência registrada com sucesso.",
    )


@router.get(
    "/inferences/uc/{uc_code}",
    response_model=APIResponse[EnergyInferenceResponse],
)
async def get_latest_inference(
    uc_code: str,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = EnergyInferenceService(session)
    result = await service.get_latest_inference(uc_code)
    return APIResponse(data=EnergyInferenceResponse.from_model(result))


@router.post(
    "/inferences/uc/{uc_code}/auto",
    response_model=APIResponse[EnergyInferenceResponse],
    dependencies=[EngineeringRequired],
)
async def infer_from_profile(
    uc_code: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Gera inferência automática por perfil para uma UC sem dados telemetrados."""
    service = EnergyInferenceService(session)
    result = await service.infer_from_profile(uc_code)
    return APIResponse(
        data=EnergyInferenceResponse.from_model(result),
        message="Inferência automática gerada com sucesso.",
    )


@router.patch(
    "/inferences/{inference_id}",
    response_model=APIResponse[EnergyInferenceResponse],
    dependencies=[EngineeringRequired],
)
async def update_inference(
    inference_id: int,
    body: EnergyInferenceUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = EnergyInferenceService(session)
    result = await service.update_inference(inference_id, body)
    return APIResponse(data=EnergyInferenceResponse.from_model(result))


@router.get(
    "/inferences/transformer/{transformer_id}",
    response_model=PaginatedResponse[EnergyInferenceSummary],
)
async def list_inferences_by_transformer(
    transformer_id: str,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    params = PaginationParams(page=page, page_size=page_size)
    service = EnergyInferenceService(session)
    items = await service.list_by_transformer(
        transformer_id, params.offset, params.page_size
    )
    return PaginatedResponse(
        data=[EnergyInferenceSummary.model_validate(i) for i in items],
        total=len(items),
        page=params.page,
        page_size=params.page_size,
        pages=1,
    )


@router.get(
    "/balances/transformer/{transformer_id}/latest",
    response_model=APIResponse[TransformerBalanceResponse],
)
async def get_latest_balance(
    transformer_id: str,
    _: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    service = EnergyInferenceService(session)
    balance = await service.get_latest_balance(transformer_id)
    return APIResponse(data=TransformerBalanceResponse.from_model(balance))
