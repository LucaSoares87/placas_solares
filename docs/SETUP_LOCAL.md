# Setup Local

## Pré-requisitos

- Python 3.11 ou superior
- PostgreSQL
- Redis
- Git
- PowerShell, terminal Windows ou WSL
- Ambiente virtual Python

## Clonar o repositório

```powershell
git clone https://github.com/LucaSoares87/placas_solares.git
cd placas_solares
```

## Criar ambiente virtual

```powershell
python -m venv .venv
```

Ativar no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se houver bloqueio de execução no PowerShell, rode:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Instalar dependências

Com pip:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Ou com Poetry, se estiver usando o `pyproject.toml`:

```powershell
poetry install
```

## Banco de dados local

O projeto utiliza PostgreSQL como banco principal.

Banco de teste esperado:

```text
energy_platform_test
```

Exemplo em SQL:

```sql
CREATE DATABASE energy_platform_test;
```

URL utilizada nos testes:

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/energy_platform_test
```

## Variáveis de ambiente

Crie um arquivo `.env` a partir do `.env.example`.

```powershell
copy .env.example .env
```

Ajuste credenciais, URLs e chaves conforme seu ambiente.

## Redis

Redis é necessário para cache e filas assíncronas.

Em ambiente local, pode ser executado via Docker, WSL ou instalação nativa.

Exemplo esperado:

```text
redis://localhost:6379/0
```

## Executar API

```powershell
python -m uvicorn backend.app.main:application --reload
```

Endereço padrão:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

## Executar testes

```powershell
python -m pytest
```

Resultado esperado na base estabilizada:

```text
250 passed
```

## Problemas comuns

### PostgreSQL indisponível

Verifique se o serviço está em execução e se o banco `energy_platform_test` existe.

### Redis indisponível

Verifique se o Redis está rodando em `localhost:6379`.

### Erro de importação

Confirme que o comando está sendo executado na raiz do projeto.

### Ambiente virtual não ativado

Ative a `.venv` antes de instalar dependências ou executar testes.
