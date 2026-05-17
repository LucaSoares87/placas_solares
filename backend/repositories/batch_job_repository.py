from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.batch_job import BatchJob
from backend.repositories.base import BaseRepository


class BatchJobRepository(BaseRepository[BatchJob]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BatchJob, session)

    async def get_by_job_id(self, job_id: str) -> BatchJob | None:
        stmt = select(BatchJob).where(BatchJob.job_id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_job(
        self,
        job_id: str,
        job_type: str,
        transformer_id: str | None = None,
        total_items: int = 0,
    ) -> BatchJob:
        job = BatchJob(
            job_id=job_id,
            job_type=job_type,
            transformer_id=transformer_id,
            status="pending",
            total_items=total_items,
        )
        return await self.save(job)

    async def mark_running(self, job_id: str) -> BatchJob | None:
        job = await self.get_by_job_id(job_id)
        if job:
            job.status = "running"
            job.started_at = datetime.now()
            await self.session.flush()
        return job

    async def mark_success(
        self,
        job_id: str,
        processed: int,
        failed: int,
        summary: str | None = None,
    ) -> BatchJob | None:
        job = await self.get_by_job_id(job_id)
        if job:
            now = datetime.now()
            job.status = "success"
            job.finished_at = now
            job.processed_items = processed
            job.failed_items = failed
            job.result_summary = summary
            if job.started_at:
                job.duration_seconds = (now - job.started_at).total_seconds()
            await self.session.flush()
        return job

    async def mark_failed(
        self, job_id: str, error: str, processed: int = 0
    ) -> BatchJob | None:
        job = await self.get_by_job_id(job_id)
        if job:
            now = datetime.now()
            job.status = "failed"
            job.finished_at = now
            job.processed_items = processed
            job.error_detail = error
            if job.started_at:
                job.duration_seconds = (now - job.started_at).total_seconds()
            await self.session.flush()
        return job

    async def list_by_status(
        self,
        status: str,
        offset: int = 0,
        limit: int = 50,
    ) -> list[BatchJob]:
        stmt = (
            select(BatchJob)
            .where(BatchJob.status == status)
            .order_by(BatchJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_transformer(
        self,
        transformer_id: str,
        offset: int = 0,
        limit: int = 20,
    ) -> list[BatchJob]:
        stmt = (
            select(BatchJob)
            .where(BatchJob.transformer_id == transformer_id)
            .order_by(BatchJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
