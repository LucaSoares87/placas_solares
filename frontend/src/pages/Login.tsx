export default function Login() {
  return (
    <main className="login-page">
      <section className="login-panel">
        <div>
          <span className="eyebrow">Acesso seguro</span>
          <h1>Energy Inference Platform</h1>
          <p>
            Plataforma analítica para inferência energética, validação
            operacional e priorização de inspeções em redes de distribuição.
          </p>
        </div>

        <form className="login-form">
          <label>
            E-mail
            <input type="email" placeholder="usuario@empresa.com" />
          </label>

          <label>
            Senha
            <input type="password" placeholder="Digite sua senha" />
          </label>

          <button className="button button-primary" type="button">
            Entrar
          </button>
        </form>
      </section>
    </main>
  );
}