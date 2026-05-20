import ExportPanel from "../components/ExportPanel";

export default function Export() {
  return (
    <div className="simple-page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Governança</span>
          <h2>Exportações</h2>
          <p>
            Preparação de dados e relatórios para auditoria, operação, BI e
            apresentação executiva.
          </p>
        </div>

        <div className="page-actions">
          <button className="button button-secondary">Histórico</button>
          <button className="button button-primary">Nova exportação</button>
        </div>
      </div>

      <ExportPanel />

      <article className="card">
        <h3 className="section-title">Últimas exportações</h3>
        <div className="export-history">
          <span>Resumo executivo - concluído há 2h</span>
          <span>Base analítica - concluído ontem</span>
          <span>Validação operacional - concluído há 3 dias</span>
        </div>
      </article>
    </div>
  );
}