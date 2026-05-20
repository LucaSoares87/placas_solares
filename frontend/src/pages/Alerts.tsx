const alerts = [
  {
    title: "Erro de balanço crítico",
    target: "TR-211",
    severity: "Crítico",
    status: "Aberto",
    action: "Priorizar inspeção em campo",
    badge: "danger"
  },
  {
    title: "Baixa confiança FV",
    target: "TR-087",
    severity: "Atenção",
    status: "Em análise",
    action: "Reprocessar imagem com nova amostra",
    badge: "warning"
  },
  {
    title: "Fila de validação acumulada",
    target: "Operação",
    severity: "Monitorar",
    status: "Pendente",
    action: "Revisar jobs aguardando validação",
    badge: "info"
  }
];

export default function Alerts() {
  return (
    <div className="simple-page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Operação</span>
          <h2>Alertas</h2>
          <p>
            Monitoramento de eventos que exigem decisão técnica, reprocessamento
            ou inspeção operacional.
          </p>
        </div>

        <div className="page-actions">
          <button className="button button-secondary">Somente abertos</button>
          <button className="button button-primary">Nova análise</button>
        </div>
      </div>

      <section className="summary-grid">
        <article className="card summary-card">
          <span>Alertas abertos</span>
          <strong>18</strong>
        </article>
        <article className="card summary-card">
          <span>Críticos</span>
          <strong>4</strong>
        </article>
        <article className="card summary-card">
          <span>Tempo médio de resolução</span>
          <strong>2,3 dias</strong>
        </article>
      </section>

      <div className="alert-page-list">
        {alerts.map((alert) => (
          <article className="card alert-page-card" key={alert.title}>
            <div>
              <span className={`badge badge-${alert.badge}`}>{alert.severity}</span>
              <h3>{alert.title}</h3>
              <p>{alert.action}</p>
            </div>

            <div className="alert-meta">
              <span>Alvo: {alert.target}</span>
              <strong>{alert.status}</strong>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}