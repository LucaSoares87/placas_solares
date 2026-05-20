import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { useHealth } from "../hooks/useHealth";

function getStatusLabel(isLoading: boolean, isError: boolean, status?: string) {
  if (isLoading) {
    return "Verificando backend";
  }

  if (isError) {
    return "Backend offline";
  }

  if (status) {
    return "Backend online";
  }

  return "Status indisponível";
}

function getStatusClass(isLoading: boolean, isError: boolean) {
  if (isLoading) {
    return "header-status header-status-checking";
  }

  if (isError) {
    return "header-status header-status-offline";
  }

  return "header-status header-status-online";
}

export default function Header() {
  const navigate = useNavigate();
  const { data, isError, isLoading } = useHealth();
  const { authenticated, user, signOut } = useAuth();

  function handleLogout() {
    signOut();
    navigate("/login", { replace: true });
  }

  const userLabel = user?.nome ?? user?.name ?? user?.matricula ?? "Usuário autenticado";

  return (
    <header className="header">
      <div className="header-title">
        <strong>Centro de Operação Analítica</strong>
        <span>Inferência FV, balanço energético e risco operacional</span>
      </div>

      <div className="header-actions">
        {authenticated ? <span className="user-chip">{userLabel}</span> : null}

        <div className={getStatusClass(isLoading, isError)}>
          {getStatusLabel(isLoading, isError, data?.status)}
        </div>

        {authenticated ? (
          <button className="button button-secondary button-compact" onClick={handleLogout}>
            Sair
          </button>
        ) : null}
      </div>
    </header>
  );
}