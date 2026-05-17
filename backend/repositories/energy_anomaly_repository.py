from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.energy_anomaly import EnergyAnomaly
from backend.repositories.base import BaseRepository


class EnergyAnomalyRepository(BaseRepository[EnergyAnomaly]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(EnergyAnomaly, session)

    async def list_unresolved(
        self, offset: int = 0, limit: int = 50
    ) -> list[EnergyAnomaly]:
        stmt = (
            select(EnergyAnomaly)
            .where(EnergyAnomaly.resolved.is_(False))
            .order_by(EnergyAnomaly.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_transformer(
        self, transformer_id: str, offset: int = 0, limit: int = 50
    ) -> list[EnergyAnomaly]:
        stmt = (
            select(EnergyAnomaly)
            .where(EnergyAnomaly.transformer_id == transformer_id)
            .order_by(EnergyAnomaly.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_uc(
        self, uc_code: str, offset: int = 0, limit: int = 50
    ) -> list[EnergyAnomaly]:
        stmt = (
            select(EnergyAnomaly)
            .where(EnergyAnomaly.uc_code == uc_code)
            .order_by(EnergyAnomaly.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def resolve(self, anomaly_id: int) -> EnergyAnomaly | None:
        from datetime import datetime, timezone
        anomaly = await self.get_by_id(anomaly_id)
        if anomaly and not anomaly.resolved:
            anomaly.resolved = True
            anomaly.resolved_at = datetime.now(timezone.utc)
            await self.session.flush()
        return anomaly
