const exports = [
  {
    title: "Resumo executivo",
    description: "KPIs, ranking de risco e balanço consolidado.",
    format: "PDF"
  },
  {
    title: "Base analítica",
    description: "Dados tabulares para auditoria e BI.",
    format: "CSV"
  },
  {
    title: "Validação operacional",
    description: "Comparativo entre estimado, real e feedback de campo.",
    format: "XLSX"
  }
];

export default function ExportPanel() {
  return (
    <div className="export-grid">
      {exports.map((item) => (
        <article className="card export-card" key={item.title}>
          <div>
            <h3>{item.title}</h3>
            <p>{item.description}</p>
          </div>

          <div className="export-footer">
            <span className="badge badge-info">{item.format}</span>
            <button className="button button-secondary">Preparar exportação</button>
          </div>
        </article>
      ))}
    </div>
  );
}