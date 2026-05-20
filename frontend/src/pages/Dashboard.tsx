import KpiCard from "../components/KpiCard";

const ranking = [
  { transformer: "TR-102", score: "Baixo risco", error: "3,7%" },
  { transformer: "TR-087", score: "Médio risco", error: "14,2%" },
  { transformer: "TR-211", score: "Prioridade", error: "31,8%" }
];

export default function Dashboard() {
  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Dashboard executivo</h2>
          <p>
            Visão consolidada dos transformadores, unidades com geração
            distribuída, balanço estimado, anomalias e maturidade operacional.
          </p>
        </div>
      </div>

      <section className="kpi-grid">
        <KpiCard label="Transformadores" value="128" trend="base monitorada" />
        <KpiCard label="UCs analisadas" value="18.420" trend="ciclo atual" />
        <KpiCard label="Cobertura FV" value="21,4%" trend="+2,1 p.p." />
        <KpiCard label="Erro médio" value="8,6%" trend="meta: ±10%" />
      </section>

      <section className="dashboard-grid">
        <article className="card">
          <h3 className="section-title">Balanço energético</h3>
          <div className="placeholder">
            Área reservada para gráfico de consumo, geração, injeção e residual.
          </div>
        </article>

        <article className="card">
          <h3 className="section-title">Ranking de risco</h3>
          <div className="table-list">
            {ranking.map((item) => (
              <div className="table-row" key={item.transformer}>
                <div>
                  <strong>{item.transformer}</strong>
                  <div className="kpi-label">Erro: {item.error}</div>
                </div>
                <span className="badge">{item.score}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}