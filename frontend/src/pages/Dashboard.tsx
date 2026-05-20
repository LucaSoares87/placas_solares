import AlertList from "../components/AlertList";
import GenerationChart from "../components/GenerationChart";
import HealthStatus from "../components/HealthStatus";
import KpiCard from "../components/KpiCard";
import RankingTable from "../components/RankingTable";
import { useDashboardKpis } from "../hooks/useDashboard";

const integerFormatter = new Intl.NumberFormat("pt-BR");

function formatInteger(value: number) {
  return integerFormatter.format(Math.round(value));
}

function formatPercent(value: number) {
  return `${(value * 100).toLocaleString("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  })}%`;
}

function formatKwh(value: number) {
  if (value >= 1000) {
    return `${(value / 1000).toLocaleString("pt-BR", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    })} MWh`;
  }

  return `${formatInteger(value)} kWh`;
}

export default function Dashboard() {
  const { kpis, isLoading, isUsingFallback, isError } = useDashboardKpis();

  const dataBadge = isLoading
    ? "Carregando KPIs"
    : isUsingFallback
      ? "Dados demonstrativos"
      : "Dados reais";

  return (
    <div>
      <div className="page-header">
        <div>
          <span className="eyebrow">Visão executiva</span>
          <h2>Dashboard operacional</h2>
          <p>
            Consolidação de transformadores, unidades com geração distribuída,
            balanço energético, anomalias e priorização de inspeções.
          </p>
        </div>

        <div className="page-actions">
          <span
            className={
              isError ? "badge badge-warning" : "badge badge-info"
            }
          >
            {dataBadge}
          </span>
          <button className="button button-secondary">Exportar CSV</button>
          <button className="button button-primary">Atualizar painel</button>
        </div>
      </div>

      <section className="kpi-grid">
        <KpiCard
          label="Transformadores"
          value={formatInteger(kpis.totalTransformers)}
          trend={`${formatInteger(kpis.criticalTransformers)} críticos`}
        />
        <KpiCard
          label="UCs analisadas"
          value={formatInteger(kpis.totalConsumerUnits)}
          trend={`${formatInteger(kpis.totalGdUnits)} com GD`}
        />
        <KpiCard
          label="Cobertura FV"
          value={formatPercent(kpis.gdPenetrationRate)}
          trend={`Telemetria: ${formatPercent(kpis.telemetryCoverageRate)}`}
        />
        <KpiCard
          label="Geração estimada"
          value={formatKwh(kpis.estimatedGenerationKwh)}
          trend={`Consumo: ${formatKwh(kpis.estimatedConsumptionKwh)}`}
        />
      </section>

      <section className="dashboard-grid dashboard-grid-main">
        <GenerationChart />
        <HealthStatus />
      </section>

      <section className="dashboard-grid dashboard-grid-secondary">
        <RankingTable />
        <AlertList />
      </section>
    </div>
  );
}