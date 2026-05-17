from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BatchJobResponse(BaseModel):
    id: int
    job_id: str
    job_type: str
    transformer_id: Optional[str]
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    total_items: int
    processed_items: int
    failed_items: int
    duration_seconds: Optional[float]
    success_rate: float
    result_summary: Optional[str]
    error_detail: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchJobStatusResponse(BaseModel):
    job_id: str
    status: str
    enqueue_time: Optional[str]
    start_time: Optional[str]
    finish_time: Optional[str]
    result: Optional[dict] = None


class EnqueueBatchRequest(BaseModel):
    transformer_id: str = Field(..., min_length=2, max_length=30)
    measured_kwh: float = Field(..., ge=0.0)
    period_start: datetime
    period_end: datetime

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class EnqueueTelemetryRequest(BaseModel):
    source_type: str = Field(default="uc", pattern="^(uc|transformer)$")
    payloads: list[dict] = Field(..., min_length=1, max_length=1000)


class EnqueueReprocessRequest(BaseModel):
    transformer_id: str = Field(..., min_length=2, max_length=30)
    measured_kwh: float = Field(..., ge=0.0)
    period_start: datetime
    period_end: datetime
    reason: Optional[str] = Field(None, max_length=300)
