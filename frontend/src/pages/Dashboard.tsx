import AlertList from "../components/AlertList";
import GenerationChart from "../components/GenerationChart";
import HealthStatus from "../components/HealthStatus";
import KpiCard from "../components/KpiCard";
import RankingTable from "../components/RankingTable";

export default function Dashboard() {
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
          <button className="button button-secondary">Exportar CSV</button>
          <button className="button button-primary">Atualizar painel</button>
        </div>
      </div>

      <section className="kpi-grid">
        <KpiCard label="Transformadores" value="128" trend="base monitorada" />
        <KpiCard label="UCs analisadas" value="18.420" trend="ciclo atual" />
        <KpiCard label="Cobertura FV" value="21,4%" trend="+2,1 p.p." />
        <KpiCard label="Erro médio" value="8,6%" trend="meta operacional: ±10%" />
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