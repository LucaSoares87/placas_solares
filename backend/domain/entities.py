from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class UserProfile(str, Enum):
    ADMIN = "admin"
    ENGINEERING = "engenharia"
    FIELD = "campo"
    READONLY = "consulta"


class UCProfile(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    RURAL = "rural"
    PUBLIC = "public"


class EnergyStatus(str, Enum):
    """Status da inferência energética da UC."""
    NORMAL = "normal"
    GENERATION_DETECTED = "generation_detected"
    INJECTION_DETECTED = "injection_detected"
    HIGH_CONSUMPTION = "high_consumption"
    LOW_CONFIDENCE = "low_confidence"
    NO_DATA = "no_data"
    ANOMALY = "anomaly"

class RiskScore(str, Enum):
    """Nível de risco operacional do transformador ou UC."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InferenceMethod(str, Enum):
    """Método utilizado para inferência energética."""
    TELEMETRY = "telemetry"           # Dados telemetrados diretos
    SATELLITE = "satellite"           # Análise de imagem de satélite
    STATISTICAL = "statistical"       # Modelo estatístico por perfil
    HYBRID = "hybrid"                 # Combinação de métodos
    DEFAULT = "default"               # Valores padrão por perfil


class BalanceStatus(str, Enum):
    """Status do balanço energético do transformador."""
    BALANCED = "balanced"
    UNDER_GENERATED = "under_generated"
    OVER_INJECTED = "over_injected"
    HIGH_LOSS = "high_loss"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AnomalyType(str, Enum):
    """Tipos de anomalia detectados na inferência."""
    NEGATIVE_CONSUMPTION = "negative_consumption"
    EXCESS_INJECTION = "excess_injection"
    IMPLAUSIBLE_GENERATION = "implausible_generation"
    METER_REVERSAL = "meter_reversal"
    SUDDEN_SPIKE = "sudden_spike"
    CONSISTENT_ZERO = "consistent_zero"

@dataclass
class ConsumerUnit:
    uc_code: str
    transformer_id: str
    latitude: float
    longitude: float
    profile: UCProfile
    is_telemetered: bool
    has_gd: bool
    gd_installed_kwp: Optional[float] = None
    inverter_model: Optional[str] = None
    panel_count: Optional[int] = None
    address: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Transformer:
    transformer_id: str
    latitude: float
    longitude: float
    rated_kva: float
    substation: Optional[str] = None
    feeder: Optional[str] = None
    uc_count: int = 0
    gd_count: int = 0


@dataclass
class EnergyInferenceResult:
    uc_code: str
    has_fv: bool
    latitude: float
    longitude: float
    area_m2: Optional[float]
    kwp_estimated: Optional[float]
    generation_kw: Optional[float]
    consumption_estimated_kw: float
    injection_kw_min: Optional[float]
    injection_kw_max: Optional[float]
    status: EnergyStatus
    confidence: float
    transformer_id: str
    operational_score: RiskScore
    computed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TransformerBalance:
    transformer_id: str
    period_start: datetime
    period_end: datetime
    measured_kwh: float
    estimated_consumption_kwh: float
    estimated_generation_kwh: float
    estimated_injection_kwh: float
    technical_losses_kwh: float
    residual_kwh: float
    absolute_error: float
    percentage_error: float
    operational_score: RiskScore
    uc_count: int
    telemetered_count: int
