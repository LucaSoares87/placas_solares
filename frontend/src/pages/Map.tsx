import GeoMap from "../components/GeoMap";

export default function Map() {
  return (
    <div className="simple-page">
      <div className="page-header">
        <div>
          <span className="eyebrow">Geovisão</span>
          <h2>Mapa energético</h2>
          <p>
            Visualização geográfica planejada para transformadores, concentração
            de geração distribuída, anomalias e prioridade de inspeção.
          </p>
        </div>

        <div className="page-actions">
          <button className="button button-secondary">Camadas</button>
          <button className="button button-primary">Atualizar mapa</button>
        </div>
      </div>

      <section className="map-layout">
        <GeoMap />

        <aside className="card map-side-panel">
          <h3 className="section-title">Camadas planejadas</h3>
          <div className="layer-list">
            <span>Transformadores</span>
            <span>UCs com FV</span>
            <span>Erro de balanço</span>
            <span>Anomalias</span>
            <span>Inspeções pendentes</span>
          </div>
        </aside>
      </section>
    </div>
  );
}