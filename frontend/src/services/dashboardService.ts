import { api } from "./api";

export type DashboardKpis = {
  totalTransformers: number;
  totalConsumerUnits: number;
  totalGdUnits: number;
  gdPenetrationRate: number;
  telemetryCoverageRate: number;
  estimatedGenerationKwh: number;
  estimatedConsumptionKwh: number;
  activeAnomalies: number;
  criticalTransformers: number;
  generatedAt?: string;
};

type RawDashboardKpis = {
  total_transformers?: number;
  total_consumer_units?: number;
  total_gd_units?: number;
  total_ucs?: number;
  total_ucs_fv?: number;
  gd_penetration_rate?: number;
  cobertura_fv_pct?: number;
  telemetry_coverage_rate?: number;
  telemetry_coverage_pct?: number;
  estimated_generation_kwh?: number;
  geracao_total_kwh?: number;
  estimated_consumption_kwh?: number;
  consumo_total_kwh?: number;
  active_anomalies?: number;
  total_anomalias_ativas?: number;
  critical_transformers?: number;
  transformadores_criticos?: number;
  generated_at?: string;
  gerado_em?: string;
};

export const fallbackDashboardKpis: DashboardKpis = {
  totalTransformers: 128,
  totalConsumerUnits: 18420,
  totalGdUnits: 3942,
  gdPenetrationRate: 0.214,
  telemetryCoverageRate: 0.68,
  estimatedGenerationKwh: 35100,
  estimatedConsumptionKwh: 45600,
  activeAnomalies: 42,
  criticalTransformers: 7,
  generatedAt: undefined
};

function getNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value.replace(",", "."));
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  return fallback;
}

function getString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function normalizeRate(value: number): number {
  if (value > 1) {
    return value / 100;
  }

  if (value < 0) {
    return 0;
  }

  return value;
}

function normalizeKpis(raw: RawDashboardKpis): DashboardKpis {
  const gdRate = getNumber(raw.gd_penetration_rate ?? raw.cobertura_fv_pct, 0);
  const telemetryRate = getNumber(
    raw.telemetry_coverage_rate ?? raw.telemetry_coverage_pct,
    0
  );

  return {
    totalTransformers: getNumber(raw.total_transformers),
    totalConsumerUnits: getNumber(raw.total_consumer_units ?? raw.total_ucs),
    totalGdUnits: getNumber(raw.total_gd_units ?? raw.total_ucs_fv),
    gdPenetrationRate: normalizeRate(gdRate),
    telemetryCoverageRate: normalizeRate(telemetryRate),
    estimatedGenerationKwh: getNumber(
      raw.estimated_generation_kwh ?? raw.geracao_total_kwh
    ),
    estimatedConsumptionKwh: getNumber(
      raw.estimated_consumption_kwh ?? raw.consumo_total_kwh
    ),
    activeAnomalies: getNumber(
      raw.active_anomalies ?? raw.total_anomalias_ativas
    ),
    criticalTransformers: getNumber(
      raw.critical_transformers ?? raw.transformadores_criticos
    ),
    generatedAt: getString(raw.generated_at ?? raw.gerado_em)
  };
}

export async function getDashboardKpis(): Promise<DashboardKpis> {
  const response = await api.get<RawDashboardKpis>("/api/v1/dashboard/kpis");
  return normalizeKpis(response.data);
}