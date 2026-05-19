# Roadmap por Atos

O projeto deve evoluir por atos incrementais. Cada ato deve entregar algo funcional, testável e coerente com os atos anteriores.

A IA ou qualquer desenvolvedor não deve avançar automaticamente para o próximo ato sem validação da etapa atual.

## ATO 0 — Arquitetura e documentação

Objetivo: consolidar documentação, arquitetura, execução local, variáveis de ambiente, testes e roadmap.

Entregas:

- README preenchido.
- `docs/ARCHITECTURE.md`.
- `docs/SETUP_LOCAL.md`.
- `docs/TESTING.md`.
- `docs/ENVIRONMENT.md`.
- `docs/ROADMAP_ATOS.md`.

Critério de aceite:

```text
Documentação criada e suíte de testes completa passando.
```

## ATO 1 — Backend base

Status: avançado.

Objetivo: consolidar a base backend enterprise.

Entregas existentes:

- FastAPI.
- Configuração centralizada.
- SQLAlchemy async.
- PostgreSQL.
- JWT.
- Services, repositories, schemas e models.
- Testes unitários e de integração.
- Logs estruturados.

Próximas melhorias:

- revisar migrations Alembic;
- documentar endpoints principais;
- consolidar padrões de resposta e erro;
- reduzir warnings técnicos.

## ATO 2 — Frontend base

Objetivo: validar ou construir frontend com React, TypeScript, Vite, Tailwind, Axios e TanStack Query.

Entregas esperadas:

- layout principal;
- login;
- dashboard inicial;
- services HTTP;
- hooks reutilizáveis;
- testes mínimos com Vitest e React Testing Library.

## ATO 3 — Autenticação

Objetivo: consolidar autenticação e autorização entre backend e frontend.

Entregas esperadas:

- fluxo de login;
- expiração de token;
- proteção de rotas;
- perfis admin, engenharia, campo e consulta;
- logs de acesso;
- testes de autenticação.

## ATO 4 — Consultas reais

Objetivo: preparar integração com banco corporativo e dados reais da concessionária.

Entregas esperadas:

- conectores parametrizados;
- queries seguras;
- camada de ingestão;
- normalização;
- versionamento de datasets;
- isolamento entre dados simulados e reais.

## ATO 5 — Balanço energético

Objetivo: consolidar cálculo energético por transformador.

Entregas esperadas:

- consumo agregado;
- geração agregada;
- injeção estimada;
- perdas técnicas;
- erro absoluto e percentual;
- score operacional;
- testes de domínio e integração.

## ATO 6 — Clima

Objetivo: consolidar integração climática.

Entregas esperadas:

- NASA POWER;
- PVGIS;
- INMET;
- cache climático;
- normalização temporal;
- qualidade climática;
- testes com mocks.

## ATO 7 — Machine Learning

Objetivo: consolidar baseline supervisionado e predição.

Entregas esperadas:

- treinamento;
- predição;
- métricas;
- versionamento de modelo;
- intervalos de confiança;
- detecção de anomalia;
- critérios de aceite por métrica.

## ATO 8 — Visão computacional

Objetivo: consolidar detecção FV e estimativa kWp.

Entregas esperadas:

- YOLO;
- segmentação;
- cálculo de área;
- GSD;
- correções geométricas;
- estimativa kWp;
- pipeline CVAT para YOLO.

## ATO 9 — Validação real

Objetivo: incorporar medições reais e feedback operacional.

Entregas esperadas:

- comparação estimado versus medido;
- ciclos de validação;
- feedback de campo;
- atualização de fatores;
- aprendizado contínuo;
- histórico de calibração.

## ATO 10 — Dashboard final

Objetivo: consolidar visão executiva e operacional.

Entregas esperadas:

- dashboard executivo;
- ranking de criticidade;
- mapa energético;
- histórico de validação;
- exportação CSV/JSON;
- preparação Power BI;
- indicadores de maturidade operacional.

## Regra de continuidade

Ao finalizar cada ato, registrar:

- arquivos criados;
- arquivos alterados;
- como executar;
- como testar;
- limitações conhecidas;
- preparação para o próximo ato.
