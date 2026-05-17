from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "EnergyInferencePlatform"
    app_version: str = "0.1.0"
    app_secret_key: str = Field(..., min_length=32)
    debug: bool = False

    # Database
    database_url: PostgresDsn = Field(...)
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30

    # Redis
    redis_url: RedisDsn = Field(...)
    redis_cache_db: int = 1
    redis_celery_db: int = 2
    redis_cache_ttl: int = 3600

    # Celery
    celery_broker_url: str = Field(...)
    celery_result_backend: str = Field(...)
    celery_task_soft_time_limit: int = 300
    celery_task_time_limit: int = 600

    # JWT
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480
    jwt_refresh_token_expire_days: int = 7

    # Weather APIs
    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    pvgis_base_url: str = "https://re.jrc.ec.europa.eu/api/v5_2"
    inmet_base_url: str = "https://apitempo.inmet.gov.br"
    inmet_api_token: str = ""

    # ML Engine
    ml_model_base_path: str = "/data/models"
    yolo_model_path: str = "/data/models/fv_detector.pt"
    yolo_confidence_threshold: float = 0.45
    yolo_iou_threshold: float = 0.5
    image_gsd_default: float = 0.15

    # Energy Constants
    kwp_factor_default: float = 0.18
    performance_ratio_default: float = 0.78
    panel_efficiency_default: float = 0.20

    # Observability
    prometheus_enabled: bool = False
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"app_env must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


class Settings(BaseSettings):
    # ... campos existentes ...

    # Redis / ARQ
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    # Worker
    WORKER_MAX_JOBS: int = 10
    WORKER_JOB_TIMEOUT: int = 300
    BATCH_CHUNK_SIZE: int = 50       # UCs processadas por chunk dentro de um job
    BATCH_CONCURRENCY: int = 5       # jobs de batch disparados simultaneamente

    # Alertas
    ALERT_WEBHOOK_URL: str | None = None
    ALERT_EMAIL_RECIPIENTS: list[str] = []
    ALERT_COOLDOWN_MINUTES: int = 60

    # Telemetria
    TELEMETRY_TOLERANCE_MINUTES: int = 15
    TELEMETRY_MAX_ROWS_PER_CALL: int = 1000

    # — Adicionar dentro da classe Settings existente —

    # YOLO / Visão Computacional
    YOLO_MODEL_PATH: str = "ml_engine/fv_detection/weights/fv_detector.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.45
    YOLO_MAX_IMAGE_SIZE_MB: int = 20

    # Fatores kWp padrão
    KWP_DEFAULT_FACTOR: float = 0.15
    KWP_MIN_VALUE: float = 0.5
    KWP_MAX_VALUE: float = 500.0

    # GSD padrão (metros/pixel)
    GSD_DEFAULT_M_PER_PIXEL: float = 0.10


    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()