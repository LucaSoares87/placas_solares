import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import ConflictException, EntityNotFoundException
from backend.models.transformer import Transformer
from backend.repositories.transformer_repository import TransformerRepository
from backend.schemas.transformer import TransformerCreate

logger = structlog.get_logger(__name__)


class TransformerService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = TransformerRepository(session)

    async def create(self, data: TransformerCreate) -> Transformer:
        if await self._repo.exists_by_transformer_id(data.transformer_id):
            raise ConflictException(
                message=f"Transformador {data.transformer_id} já existe.",
                details={"transformer_id": data.transformer_id},
            )

        transformer = Transformer(**data.model_dump())
        saved = await self._repo.save(transformer)
        logger.info("transformer.created", transformer_id=data.transformer_id)
        return saved

    async def get_by_id(self, transformer_id: str) -> Transformer:
        transformer = await self._repo.get_by_transformer_id(transformer_id)
        if not transformer:
            raise EntityNotFoundException(
                message=f"Transformador {transformer_id} não encontrado.",
                details={"transformer_id": transformer_id},
            )
        return transformer

    async def list_paginated(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[list[Transformer], int]:
        items = await self._repo.list_all(offset, limit)
        total = await self._repo.count_all()
        return list(items), total

    async def list_by_substation(
        self, substation: str, offset: int = 0, limit: int = 50
    ) -> list[Transformer]:
        return await self._repo.list_by_substation(substation, offset, limit)

    async def delete(self, transformer_id: str) -> None:
        transformer = await self.get_by_id(transformer_id)
        await self._repo.delete(transformer)
        logger.info("transformer.deleted", transformer_id=transformer_id)
