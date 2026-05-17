"""Constantes físicas e operacionais do domínio energético."""

# ── Limites de geração fotovoltaica ──────────────────────────────────────────
FV_EFFICIENCY_MIN = 0.14        # 14% — painéis de baixa qualidade
FV_EFFICIENCY_MAX = 0.22        # 22% — painéis premium monocristalinos
FV_EFFICIENCY_DEFAULT = 0.18    # 18% — eficiência padrão de mercado

PANEL_AREA_M2 = 1.7             # Área média de um painel (m²)
PANEL_WP_DEFAULT = 450          # Potência pico padrão por painel (Wp)

# Irradiância solar — Nordeste brasileiro (kWh/m²/dia)
IRRADIANCE_NORDESTE_PEAK = 6.2
IRRADIANCE_NORDESTE_AVG = 5.5
IRRADIANCE_NORDESTE_MIN = 4.8

# Fator de desempenho do sistema FV (PR — Performance Ratio)
PERFORMANCE_RATIO_DEFAULT = 0.80

# ── Consumo por perfil (kW médio) ─────────────────────────────────────────────
PROFILE_CONSUMPTION_KW = {
    "residential": 0.9,
    "commercial": 4.5,
    "industrial": 18.0,
    "rural": 2.5,
    "public": 3.0,
}

# ── Limites de injeção por porte do sistema FV ───────────────────────────────
INJECTION_RATIO_MIN = 0.10      # 10% da geração como mínimo injetado
INJECTION_RATIO_MAX = 0.85      # 85% da geração como máximo injetado

# ── Limites de confiança ──────────────────────────────────────────────────────
CONFIDENCE_HIGH = 0.85
CONFIDENCE_MEDIUM = 0.60
CONFIDENCE_LOW = 0.35

# ── Balanço do transformador ──────────────────────────────────────────────────
TECHNICAL_LOSS_FACTOR = 0.035   # 3.5% perdas técnicas médias
BALANCE_TOLERANCE_PCT = 0.05    # 5% de tolerância no balanço

# ── Limites de risco operacional ─────────────────────────────────────────────
RISK_LOW_THRESHOLD = 0.20
RISK_MEDIUM_THRESHOLD = 0.45
RISK_HIGH_THRESHOLD = 0.70

# ── Limites de potência do transformador ─────────────────────────────────────
TRANSFORMER_OVERLOAD_THRESHOLD = 0.90   # 90% da kVA nominais
TRANSFORMER_CRITICAL_THRESHOLD = 1.10   # 110% — sobrecarga crítica

# ── Períodos padrão ───────────────────────────────────────────────────────────
INFERENCE_TTL_MINUTES = 60      # Validade de uma inferência em cache
BALANCE_WINDOW_HOURS = 24       # Janela padrão do balanço energético
