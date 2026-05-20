type KpiCardProps = {
  label: string;
  value: string;
  trend?: string;
};

export default function KpiCard({ label, value, trend }: KpiCardProps) {
  return (
    <article className="card kpi-card">
      <span className="kpi-label">{label}</span>
      <strong className="kpi-value">{value}</strong>
      {trend ? <span className="kpi-trend">{trend}</span> : null}
    </article>
  );
}