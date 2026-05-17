from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.domain.entities import AnomalyType, RiskScore


class EnergyAnomalyCreate(BaseModel):
    uc_code: Optional[str] = Field(None, max_length=20)
    transformer_id: str = Field(..., min_length=2, max_length=30)
    anomaly_type: AnomalyType
    description: str = Field(..., min_length=5, max_length=1000)
    severity: RiskScore = RiskScore.MEDIUM


class EnergyAnomalyResponse(BaseModel):
    id: int
    uc_code: Optional[str]
    transformer_id: str
    anomaly_type: AnomalyType
    description: str
    severity: RiskScore
    resolved: bool
    detected_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}
