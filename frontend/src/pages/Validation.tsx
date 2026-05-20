const validations = [
  {
    label: "Geração estimada",
    estimated: "35.100 kWh",
    measured: "33.900 kWh",
    deviation: "3,5%"
  },
  {
    label: "Consumo estimado",
    estimated: "45.600 kWh",
    measured: "47.200 kWh",
    deviation: "3,4%"
  },
  {
    label: "Injeção estimada",
    estimated: "7.200 kWh",
    measured: "6.850 kWh",
    deviation: "5,1%"
  }
];

export default function Validation() {
  return (
    <div className="simple-page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Confiabilidade</span>
          <h2>Validação operacional</h2>
          <p>
            Comparação entre inferências do motor energético, medições reais e
            feedback operacional para ajuste contínuo.
          </p>
        </div>

        <div className="page-actions">
          <button className="button button-secondary">Importar medições</button>
          <button className="button button-primary">Registrar feedback</button>
        </div>
      </div>

      <section className="validation-grid">
        {validations.map((item) => (
          <article className="card validation-card" key={item.label}>
            <span>{item.label}</span>

            <div className="validation-values">
              <div>
                <small>Estimado</small>
                <strong>{item.estimated}</strong>
              </div>
              <div>
                <small>Real</small>
                <strong>{item.measured}</strong>
              </div>
            </div>

            <div className="validation-footer">
              <span>Desvio</span>
              <strong>{item.deviation}</strong>
            </div>
          </article>
        ))}
      </section>

      <article className="card">
        <h3 className="section-title">Ciclo de aprendizado contínuo</h3>
        <div className="timeline">
          <span>Inferência inicial</span>
          <span>Comparação com medição real</span>
          <span>Registro de feedback</span>
          <span>Atualização de fator regional</span>
        </div>
      </article>
    </div>
  );
}