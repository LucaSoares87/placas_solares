const regions = [
  { name: "Maranguape I", transformers: 32, risk: "Alto", position: "geo-point point-a" },
  { name: "Lusitânia", transformers: 18, risk: "Baixo", position: "geo-point point-b" },
  { name: "Centro", transformers: 41, risk: "Médio", position: "geo-point point-c" },
  { name: "Jardim Paulista", transformers: 27, risk: "Médio", position: "geo-point point-d" }
];

export default function GeoMap() {
  return (
    <article className="card geo-card">
      <div className="card-header">
        <div>
          <h3 className="section-title">Mapa energético</h3>
          <p>Visão mockada de concentração operacional por região.</p>
        </div>
        <span className="badge badge-info">Preview</span>
      </div>

      <div className="geo-map">
        <div className="geo-grid" />

        {regions.map((region) => (
          <div className={region.position} key={region.name}>
            <span />
            <strong>{region.name}</strong>
          </div>
        ))}
      </div>

      <div className="geo-region-list">
        {regions.map((region) => (
          <div className="geo-region-row" key={region.name}>
            <div>
              <strong>{region.name}</strong>
              <span>{region.transformers} transformadores</span>
            </div>
            <span className="badge">{region.risk}</span>
          </div>
        ))}
      </div>
    </article>
  );
}