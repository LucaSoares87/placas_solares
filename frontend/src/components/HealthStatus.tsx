const items = [
  { label: "Backend API", value: "Operacional", status: "success" },
  { label: "Inferência ML", value: "Estável", status: "success" },
  { label: "Fila Redis", value: "Monitorar", status: "warning" },
  { label: "Cobertura CI", value: "Ativa", status: "success" }
];

export default function HealthStatus() {
  return (
    <article className="card health-card">
      <div className="card-header">
        <div>
          <h3 className="section-title">Saúde operacional</h3>
          <p>Status técnico consolidado dos serviços principais.</p>
        </div>
      </div>

      <div className="health-list">
        {items.map((item) => (
          <div className="health-row" key={item.label}>
            <div>
              <strong>{item.label}</strong>
              <span>{item.value}</span>
            </div>
            <span className={`status-dot status-${item.status}`} />
          </div>
        ))}
      </div>
    </article>
  );
}