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
    app_secret_key: str = Field(
        default="change-this-secret-key-in-development",
        min_length=32,
    )
    debug: bool = False

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/energy_platform"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_pool_timeout: int = 30

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    redis_cache_db: int = 1
    redis_celery_db: int = 2
    redis_cache_ttl: int = 3600

    # Redis / ARQ
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str | None = None
    redis_db: int = 0

    # Celery
    celery_broker_url: str = "redis://localhost:6379/2"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_soft_time_limit: int = 300
    celery_task_time_limit: int = 600

    # Worker
    worker_max_jobs: int = 10
    worker_job_timeout: int = 300
    batch_chunk_size: int = 50
    batch_concurrency: int = 5

    # JWT
    jwt_secret_key: str = Field(
        default="change-this-jwt-secret-in-development",
        min_length=32,
    )
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
    yolo_model_path: str = "ml_engine/fv_detection/weights/fv_detector.pt"
    yolo_confidence_threshold: float = 0.45
    yolo_iou_threshold: float = 0.5
    yolo_max_image_size_mb: int = 20
    image_gsd_default: float = 0.15
    gsd_default_m_per_pixel: float = 0.10

    # Energy Constants
    kwp_factor_default: float = 0.18
    kwp_default_factor: float = 0.15
    kwp_min_value: float = 0.5
    kwp_max_value: float = 500.0
    performance_ratio_default: float = 0.78
    panel_efficiency_default: float = 0.20

    # Alerts
    alert_webhook_url: str | None = None
    alert_email_recipients: list[str] = []
    alert_cooldown_minutes: int = 60

    # Telemetry
    telemetry_tolerance_minutes: int = 15
    telemetry_max_rows_per_call: int = 1000

    # Observability
    prometheus_enabled: bool = False
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, value: str) -> str:
        allowed = {"development", "staging", "production"}
        if value not in allowed:
            raise ValueError(f"app_env must be one of {allowed}")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_staging(self) -> bool:
        return self.app_env == "staging"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()