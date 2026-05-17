import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import ConflictException, EntityNotFoundException
from backend.models.consumer_unit import ConsumerUnit
from backend.repositories.consumer_unit_repository import ConsumerUnitRepository
from backend.repositories.transformer_repository import TransformerRepository
from backend.schemas.consumer_unit import ConsumerUnitCreate, ConsumerUnitUpdate

logger = structlog.get_logger(__name__)


class ConsumerUnitService:
    def __init__(self, session: AsyncSession) -> None:
        self._uc_repo = ConsumerUnitRepository(session)
        self._tr_repo = TransformerRepository(session)

    async def create(self, data: ConsumerUnitCreate) -> ConsumerUnit:
        if await self._uc_repo.exists_by_uc_code(data.uc_code):
            raise ConflictException(
                message=f"UC {data.uc_code} já existe.",
                details={"uc_code": data.uc_code},
            )

        transformer_exists = await self._tr_repo.exists_by_transformer_id(data.transformer_id)
        if not transformer_exists:
            raise EntityNotFoundException(
                message=f"Transformador {data.transformer_id} não encontrado.",
                details={"transformer_id": data.transformer_id},
            )

        uc = ConsumerUnit(**data.model_dump())
        saved = await self._uc_repo.save(uc)

        await self._sync_transformer_counts(data.transformer_id)

        logger.info("consumer_unit.created", uc_code=data.uc_code, transformer_id=data.transformer_id)
        return saved

    async def get_by_uc_code(self, uc_code: str) -> ConsumerUnit:
        uc = await self._uc_repo.get_by_uc_code(uc_code)
        if not uc:
            raise EntityNotFoundException(
                message=f"UC {uc_code} não encontrada.",
                details={"uc_code": uc_code},
            )
        return uc

    async def update(self, uc_code: str, data: ConsumerUnitUpdate) -> ConsumerUnit:
        uc = await self.get_by_uc_code(uc_code)

        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(uc, field, value)

        saved = await self._uc_repo.save(uc)
        logger.info("consumer_unit.updated", uc_code=uc_code, fields=list(update_data.keys()))
        return saved

    async def delete(self, uc_code: str) -> None:
        uc = await self.get_by_uc_code(uc_code)
        transformer_id = uc.transformer_id
        await self._uc_repo.delete(uc)
        await self._sync_transformer_counts(transformer_id)
        logger.info("consumer_unit.deleted", uc_code=uc_code)

    async def list_by_transformer(
        self, transformer_id: str, offset: int = 0, limit: int = 100
    ) -> tuple[list[ConsumerUnit], int]:
        if not await self._tr_repo.exists_by_transformer_id(transformer_id):
            raise EntityNotFoundException(
                message=f"Transformador {transformer_id} não encontrado.",
                details={"transformer_id": transformer_id},
            )
        items = await self._uc_repo.list_by_transformer(transformer_id, offset, limit)
        total = await self._uc_repo.count_by_transformer(transformer_id)
        return items, total

    async def list_paginated(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[list[ConsumerUnit], int]:
        items = await self._uc_repo.list_all(offset, limit)
        total = await self._uc_repo.count_all()
        return list(items), total

    async def _sync_transformer_counts(self, transformer_id: str) -> None:
        uc_count = await self._uc_repo.count_by_transformer(transformer_id)
        gd_count = await self._uc_repo.count_gd_by_transformer(transformer_id)
        await self._tr_repo.update_uc_counts(transformer_id, uc_count, gd_count)
