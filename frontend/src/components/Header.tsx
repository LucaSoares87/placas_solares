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
  const { data, isError, isLoading } = useHealth();

  return (
    <header className="header">
      <div className="header-title">
        <strong>Centro de Operação Analítica</strong>
        <span>Inferência FV, balanço energético e risco operacional</span>
      </div>

      <div className={getStatusClass(isLoading, isError)}>
        {getStatusLabel(isLoading, isError, data?.status)}
      </div>
    </header>
  );
}