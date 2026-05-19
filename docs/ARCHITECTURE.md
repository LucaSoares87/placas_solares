# Arquitetura

## Visão geral

A Energy Inference Platform é organizada em camadas para separar API, domínio, serviços, persistência, processamento assíncrono, machine learning, visão computacional e preparação para integração operacional.

O objetivo arquitetural é manter o projeto robusto, modular, testável e evolutivo, evitando duplicação de módulos, regras espalhadas ou acoplamento indevido entre API, banco e modelos analíticos.

## Camadas principais

### API

A camada de API expõe endpoints versionados em `/api/v1`.

Responsabilidades:

- receber requisições;
- validar entradas com schemas Pydantic;
- aplicar autenticação e autorização;
- delegar regras para services;
- retornar respostas padronizadas;
- manter documentação OpenAPI/Swagger.

A API não deve concentrar regra de negócio pesada.

### Services

A camada de services orquestra casos de uso da aplicação.

Responsabilidades:

- inferência energética;
- balanço por transformador;
- consulta e consolidação de dashboard;
- treinamento e predição ML;
- validação operacional;
- integração com repositories;
- coordenação de workers e pipelines.

### Domain

A camada de domínio contém regras puras, enums, cálculos e contratos que não dependem diretamente da API ou do banco.

Responsabilidades:

- regras elétricas;
- classificação de risco;
- classificação de balanço;
- cálculo de scores;
- regras de modelos ML;
- entidades e tipos de domínio.

### Repositories

Repositories encapsulam o acesso ao banco de dados.

Responsabilidades:

- consultas SQLAlchemy;
- persistência de entidades;
- filtros reutilizáveis;
- isolamento entre services e banco.

### Models

Models representam entidades persistidas no PostgreSQL.

Responsabilidades:

- mapear tabelas;
- definir relacionamentos;
- preservar compatibilidade com migrations;
- manter coerência com repositories e schemas.

### Schemas

Schemas são DTOs de entrada e saída.

Responsabilidades:

- validar payloads;
- definir contratos públicos da API;
- separar objetos de transporte dos models persistidos.

### Workers

Workers executam tarefas assíncronas com Celery e Redis.

Responsabilidades:

- tarefas de inferência pesada;
- processamento em lote;
- validações assíncronas;
- exportações;
- integrações de maior custo computacional.

### ML Engine

O `ml_engine` contém módulos analíticos e algoritmos desacoplados da API.

Responsabilidades:

- detecção FV;
- segmentação;
- estimativa de geração;
- modelos de carga;
- modelos de perfil;
- detecção de anomalias;
- calibração;
- aprendizado contínuo.

### Data Pipeline

O `data_pipeline` é reservado para ingestão, normalização, clima, GIS, topologia, transformadores e datasets.

Responsabilidades futuras:

- ingestão de banco corporativo;
- versionamento de datasets;
- integração climática;
- associação UC-transformador;
- preparação de dados para ML e dashboards.

## Fluxo macro de inferência

```text
Dados corporativos
→ normalização
→ identificação UC-transformador
→ detecção FV
→ estimativa de área
→ estimativa kWp
→ integração climática
→ estimativa de geração
→ reconstrução de carga
→ inferência de injeção
→ balanço por transformador
→ validação operacional
→ score de risco
→ dashboard/API
→ aprendizado contínuo
```

## Princípios arquiteturais

- Regras de negócio devem ficar fora das rotas.
- Services devem orquestrar casos de uso.
- Domain deve conter regras puras e testáveis.
- Repositories devem concentrar acesso a dados.
- Schemas devem separar contrato de API de entidades persistidas.
- ML e visão computacional devem permanecer desacoplados da API.
- Workers devem processar tarefas pesadas.
- Testes devem validar domínio, services e endpoints.
- Módulos estáveis não devem ser reescritos sem necessidade.

## Decisões atuais

- Backend em FastAPI.
- Banco principal: PostgreSQL.
- ORM: SQLAlchemy async.
- Filas: Celery com Redis.
- Autenticação: JWT.
- Logs estruturados: structlog.
- Testes: Pytest e pytest-asyncio.
- ML inicial com modelos interpretáveis e evolutivos.
- Visão computacional preparada para YOLO/segmentação.

## Pontos que ainda precisam amadurecer

- Documentação de migrations Alembic.
- Hardening de produção.
- Observabilidade com métricas reais.
- Frontend corporativo completo.
- Geoprocessamento operacional.
- Integração climática produtiva.
- Validação com dados reais de campo.
- Pipeline completo de aprendizado contínuo em produção.
