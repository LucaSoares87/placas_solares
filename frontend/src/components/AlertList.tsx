const alerts = [
  {
    title: "Erro de balanço acima do limite",
    description: "TR-211 apresentou erro estimado de 31,8% no último ciclo.",
    severity: "Crítico",
    badge: "danger"
  },
  {
    title: "Baixa confiança de detecção FV",
    description: "Região com sombra e baixa resolução em parte das imagens.",
    severity: "Atenção",
    badge: "warning"
  },
  {
    title: "Fila de reprocessamento pendente",
    description: "3 jobs aguardando validação operacional.",
    severity: "Monitorar",
    badge: "info"
  }
];

export default function AlertList() {
  return (
    <article className="card alerts-card">
      <div className="card-header">
        <div>
          <h3 className="section-title">Alertas recentes</h3>
          <p>Eventos que exigem acompanhamento técnico ou operacional.</p>
        </div>
      </div>

      <div className="alert-list">
        {alerts.map((alert) => (
          <div className="alert-row" key={alert.title}>
            <div>
              <strong>{alert.title}</strong>
              <span>{alert.description}</span>
            </div>
            <span className={`badge badge-${alert.badge}`}>{alert.severity}</span>
          </div>
        ))}
      </div>
    </article>
  );
}