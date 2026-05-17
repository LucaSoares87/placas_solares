from fastapi import APIRouter

from backend.api.v1.endpoints.anomalies import router as anomalies_router
from backend.api.v1.endpoints.auth import router as auth_router
from backend.api.v1.endpoints.batch import router as batch_router
from backend.api.v1.endpoints.climate import router as climate_router
from backend.api.v1.endpoints.consumer_units import router as consumer_units_router
from backend.api.v1.endpoints.dashboard import router as dashboard_router
from backend.api.v1.endpoints.energy_balance import router as energy_balance_router
from backend.api.v1.endpoints.energy_inference import router as energy_router
from backend.api.v1.endpoints.ml import router as ml_router
from backend.api.v1.endpoints.transformers import router as transformers_router
from backend.api.v1.endpoints.users import router as users_router

from backend.api.v1 import fv_detection
from backend.api.v1 import validation
from backend.api.v1 import dashboard
import structlog

logger = structlog.get_logger(__name__)
api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(transformers_router)
api_router.include_router(consumer_units_router)
api_router.include_router(energy_router)
api_router.include_router(batch_router)
api_router.include_router(anomalies_router)
api_router.include_router(dashboard_router)
api_router.include_router(energy_balance_router)
api_router.include_router(climate_router)
api_router.include_router(ml_router)
api_router.include_router(fv_detection.router)
api_router.include_router(validation.router)
api_router.include_router(dashboard.router)



@api_router.get("/ping", tags=["Sistema"])
async def ping():
    return {"message": "pong", "version": "1.0.0"}
