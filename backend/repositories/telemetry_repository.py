from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.telemetry_reading import TelemetryReading
from backend.repositories.base import BaseRepository


class TelemetryRepository(BaseRepository[TelemetryReading]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TelemetryReading, session)

    async def get_latest_by_source(
        self, source_id: str, source_type: str = "uc"
    ) -> TelemetryReading | None:
        stmt = (
            select(TelemetryReading)
            .where(
                TelemetryReading.source_id == source_id,
                TelemetryReading.source_type == source_type,
                TelemetryReading.quality_flag == "ok",
            )
            .order_by(TelemetryReading.measured_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_source_and_period(
        self,
        source_id: str,
        start: datetime,
        end: datetime,
        source_type: str = "uc",
        only_valid: bool = True,
        offset: int = 0,
        limit: int = 500,
    ) -> list[TelemetryReading]:
        filters = [
            TelemetryReading.source_id == source_id,
            TelemetryReading.source_type == source_type,
            TelemetryReading.measured_at >= start,
            TelemetryReading.measured_at <= end,
        ]
        if only_valid:
            filters.append(TelemetryReading.quality_flag == "ok")

        stmt = (
            select(TelemetryReading)
            .where(and_(*filters))
            .order_by(TelemetryReading.measured_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_insert(self, readings: list[TelemetryReading]) -> int:
        """Insere múltiplas leituras em bloco. Retorna o total inserido."""
        for r in readings:
            self.session.add(r)
        await self.session.flush()
        return len(readings)

    async def count_by_source(
        self,
        source_id: str,
        start: datetime,
        end: datetime,
        source_type: str = "uc",
    ) -> int:
        from sqlalchemy import func
        stmt = (
            select(func.count())
            .select_from(TelemetryReading)
            .where(
                TelemetryReading.source_id == source_id,
                TelemetryReading.source_type == source_type,
                TelemetryReading.measured_at >= start,
                TelemetryReading.measured_at <= end,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def mark_suspect(self, reading_ids: list[int]) -> int:
        """Marca leituras como suspeitas após validação de qualidade."""
        from sqlalchemy import update
        stmt = (
            update(TelemetryReading)
            .where(TelemetryReading.id.in_(reading_ids))
            .values(quality_flag="suspect")
        )
        result = await self.session.execute(stmt)
        return result.rowcount
