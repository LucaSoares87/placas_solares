import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const navigate = useNavigate();
  const { signIn, isLoading, error } = useAuth();

  const [matricula, setMatricula] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    await signIn({
      matricula,
      password
    });

    navigate("/", { replace: true });
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <div>
          <span className="eyebrow">Acesso seguro</span>
          <h1>Energy Inference Platform</h1>
          <p>
            Plataforma analítica para inferência energética, validação operacional
            e priorização de inspeções em redes de distribuição.
          </p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Matrícula
            <input
              type="text"
              placeholder="Digite sua matrícula"
              value={matricula}
              onChange={(event) => setMatricula(event.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label>
            Senha
            <input
              type="password"
              placeholder="Digite sua senha"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {error ? <div className="login-error">{error}</div> : null}

          <button className="button button-primary" type="submit" disabled={isLoading}>
            {isLoading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}