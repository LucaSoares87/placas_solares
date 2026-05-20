import {
  AlertTriangle,
  BarChart3,
  FileDown,
  LayoutDashboard,
  Map,
  ShieldCheck
} from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/ranking", label: "Ranking de risco", icon: BarChart3 },
  { to: "/alerts", label: "Alertas", icon: AlertTriangle },
  { to: "/map", label: "Mapa energético", icon: Map },
  { to: "/validation", label: "Validação", icon: ShieldCheck },
  { to: "/export", label: "Exportações", icon: FileDown }
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h1>Energy Inference</h1>
        <p>Plataforma de inferência energética</p>
      </div>

      <nav className="sidebar-nav">
        {links.map((item) => {
          const Icon = item.icon;

          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                isActive ? "sidebar-link active" : "sidebar-link"
              }
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}