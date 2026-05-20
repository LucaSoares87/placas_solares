const rows = [
  {
    transformer: "TR-211",
    area: "Maranguape I",
    consumers: 184,
    error: "31,8%",
    anomalies: 12,
    priority: "Inspeção prioritária",
    badge: "danger"
  },
  {
    transformer: "TR-087",
    area: "Jardim Paulista",
    consumers: 142,
    error: "14,2%",
    anomalies: 5,
    priority: "Monitoramento ativo",
    badge: "warning"
  },
  {
    transformer: "TR-044",
    area: "Centro",
    consumers: 226,
    error: "9,5%",
    anomalies: 3,
    priority: "Acompanhamento",
    badge: "info"
  },
  {
    transformer: "TR-102",
    area: "Lusitânia",
    consumers: 98,
    error: "3,7%",
    anomalies: 2,
    priority: "Baixo risco",
    badge: "success"
  }
];

export default function Ranking() {
  return (
    <div className="simple-page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Priorização</span>
          <h2>Ranking de risco</h2>
          <p>
            Lista executiva de transformadores classificados por erro de balanço,
            anomalias ativas e criticidade operacional.
          </p>
        </div>

        <div className="page-actions">
          <button className="button button-secondary">Filtrar região</button>
          <button className="button button-primary">Exportar ranking</button>
        </div>
      </div>

      <section className="summary-grid">
        <article className="card summary-card">
          <span>Transformadores críticos</span>
          <strong>7</strong>
        </article>
        <article className="card summary-card">
          <span>Erro médio no top 10</span>
          <strong>18,4%</strong>
        </article>
        <article className="card summary-card">
          <span>Anomalias ativas</span>
          <strong>42</strong>
        </article>
      </section>

      <article className="card">
        <div className="executive-table">
          <div className="executive-table-head">
            <span>Transformador</span>
            <span>Área</span>
            <span>UCs</span>
            <span>Erro</span>
            <span>Anomalias</span>
            <span>Prioridade</span>
          </div>

          {rows.map((row) => (
            <div className="executive-table-row" key={row.transformer}>
              <strong>{row.transformer}</strong>
              <span>{row.area}</span>
              <span>{row.consumers}</span>
              <span>{row.error}</span>
              <span>{row.anomalies}</span>
              <span className={`badge badge-${row.badge}`}>{row.priority}</span>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}