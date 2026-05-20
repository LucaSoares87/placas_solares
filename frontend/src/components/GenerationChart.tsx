import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

const data = [
  { month: "Jan", consumo: 41200, geracao: 28800, injecao: 4800 },
  { month: "Fev", consumo: 39800, geracao: 30100, injecao: 5200 },
  { month: "Mar", consumo: 42600, geracao: 31500, injecao: 6100 },
  { month: "Abr", consumo: 44100, geracao: 33700, injecao: 6900 },
  { month: "Mai", consumo: 41900, geracao: 32900, injecao: 6400 },
  { month: "Jun", consumo: 45600, geracao: 35100, injecao: 7200 }
];

const numberFormatter = new Intl.NumberFormat("pt-BR");

export default function GenerationChart() {
  return (
    <article className="card chart-card">
      <div className="card-header">
        <div>
          <h3 className="section-title">Balanço energético</h3>
          <p>Consumo, geração estimada e injeção na rede por ciclo mensal.</p>
        </div>
        <span className="badge badge-info">Mock operacional</span>
      </div>

      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={data} margin={{ top: 10, right: 18, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="consumoGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="geracaoGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#22c55e" stopOpacity={0.32} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="injecaoGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.28} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
              </linearGradient>
            </defs>

            <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" vertical={false} />
            <XAxis dataKey="month" stroke="#94a3b8" tickLine={false} axisLine={false} />
            <YAxis
              stroke="#94a3b8"
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${Number(value) / 1000}k`}
            />
            <Tooltip
              contentStyle={{
                background: "#020617",
                border: "1px solid rgba(148, 163, 184, 0.2)",
                borderRadius: 12,
                color: "#e5e7eb"
              }}
              formatter={(value) => [`${numberFormatter.format(Number(value))} kWh`, ""]}
            />

            <Area
              type="monotone"
              dataKey="consumo"
              stroke="#38bdf8"
              fill="url(#consumoGradient)"
              strokeWidth={2}
              name="Consumo"
            />
            <Area
              type="monotone"
              dataKey="geracao"
              stroke="#22c55e"
              fill="url(#geracaoGradient)"
              strokeWidth={2}
              name="Geração"
            />
            <Area
              type="monotone"
              dataKey="injecao"
              stroke="#f59e0b"
              fill="url(#injecaoGradient)"
              strokeWidth={2}
              name="Injeção"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}