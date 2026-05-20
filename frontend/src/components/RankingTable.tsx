const rows = [
  {
    transformer: "TR-211",
    area: "Maranguape I",
    score: "Prioridade",
    error: "31,8%",
    anomalies: 12,
    badge: "danger"
  },
  {
    transformer: "TR-087",
    area: "Jardim Paulista",
    score: "Médio risco",
    error: "14,2%",
    anomalies: 5,
    badge: "warning"
  },
  {
    transformer: "TR-102",
    area: "Lusitânia",
    score: "Baixo risco",
    error: "3,7%",
    anomalies: 2,
    badge: "success"
  },
  {
    transformer: "TR-044",
    area: "Centro",
    score: "Monitorar",
    error: "9,5%",
    anomalies: 3,
    badge: "info"
  }
];

export default function RankingTable() {
  return (
    <article className="card ranking-card">
      <div className="card-header">
        <div>
          <h3 className="section-title">Ranking de risco</h3>
          <p>Transformadores priorizados por erro, anomalias e criticidade.</p>
        </div>
        <span className="badge badge-info">Top 4</span>
      </div>

      <div className="risk-table">
        {rows.map((row, index) => (
          <div className="risk-row" key={row.transformer}>
            <div className="risk-position">{index + 1}</div>

            <div className="risk-main">
              <strong>{row.transformer}</strong>
              <span>{row.area}</span>
            </div>

            <div className="risk-metric">
              <span>Erro</span>
              <strong>{row.error}</strong>
            </div>

            <div className="risk-metric">
              <span>Anomalias</span>
              <strong>{row.anomalies}</strong>
            </div>

            <span className={`badge badge-${row.badge}`}>{row.score}</span>
          </div>
        ))}
      </div>
    </article>
  );
}