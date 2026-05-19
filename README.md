# Energy Inference Platform

Plataforma enterprise-grade para inferência energética em redes secundárias de distribuição, com foco em unidades consumidoras com geração distribuída fotovoltaica, balanço energético por transformador, detecção de anomalias, validação operacional e aprendizado contínuo.

O projeto combina backend FastAPI, PostgreSQL, Redis, Celery, modelos de machine learning, visão computacional, dados climáticos, regras elétricas e preparação para integração com dashboards executivos e operação em concessionárias de energia.

## Objetivo

Inferir o comportamento energético de unidades consumidoras com geração fotovoltaica, inclusive sem telemedição, utilizando:

- visão computacional para detecção de painéis fotovoltaicos;
- estimativa de área, kWp e geração solar;
- reconstrução de consumo e injeção;
- balanço energético por transformador;
- validação com medições reais;
- detecção de anomalias;
- aprendizado contínuo com feedback operacional.

A meta operacional é reduzir progressivamente o erro de inferência para valores próximos de ±10%.

## Status atual

O backend e os testes foram estabilizados.

Resultado de referência da suíte completa:

```text
250 passed
```

Blocos já validados:

```text
backend/tests/integration/test_batch_endpoints.py
backend/tests/integration/test_consumer_units.py
backend/tests/integration/test_dashboard_endpoints.py
backend/tests/integration/test_energy_balance_endpoints.py
backend/tests/integration/test_health.py
backend/tests/test_fv_api.py
backend/tests/test_fv_detection.py
backend/tests/test_services.py
backend/tests/unit/test_anomaly_detector.py
backend/tests/unit/test_climate_domain.py
backend/tests/unit/test_climate_service.py
backend/tests/unit/test_config.py
backend/tests/unit/test_dashboard_service.py
backend/tests/unit/test_energy_balance_domain.py
backend/tests/unit/test_energy_balance_service.py
backend/tests/unit/test_energy_inference_service.py
backend/tests/unit/test_ml_domain.py
backend/tests/unit/test_ml_service.py
backend/tests/unit/test_predictor.py
backend/tests/unit/test_schemas_energy.py
backend/tests/unit/test_telemetry_validator.py
backend/tests/unit/test_trainer.py
tests/test_dashboard_service.py
tests/test_inference_pipeline.py
tests/test_validation.py
```

## Stack principal

- Python 3.11+
- FastAPI
- SQLAlchemy async
- PostgreSQL
- Alembic
- Redis
- Celery
- Pydantic
- Structlog
- JWT
- Pytest
- Scikit-learn
- XGBoost
- LightGBM
- pvlib
- OpenCV
- GeoPandas
- Rasterio
- Shapely
- PyProj

## Estrutura macro

```text
project_root/
├── backend/
│   ├── app/
│   ├── api/
│   ├── core/
│   ├── domain/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── workers/
│   └── tests/
├── ml_engine/
├── data_pipeline/
├── frontend/
├── infra/
├── docs/
├── scripts/
├── data/
├── notebooks/
├── docker/
└── tests/
```

## Execução local

Consulte:

```text
docs/SETUP_LOCAL.md
```

## Testes

Para executar a suíte completa:

```powershell
python -m pytest
```

Resultado esperado na base estabilizada:

```text
250 passed
```

Detalhes em:

```text
docs/TESTING.md
```

## Configuração

As variáveis de ambiente esperadas estão descritas em:

```text
docs/ENVIRONMENT.md
```

## Arquitetura

A visão de camadas, responsabilidades e fluxo macro está em:

```text
docs/ARCHITECTURE.md
```

## Roadmap por atos

A evolução do projeto deve seguir atos incrementais, sem avançar automaticamente para funcionalidades futuras.

Consulte:

```text
docs/ROADMAP_ATOS.md
```

## Maturidade atual

Maturidade estimada: 72%.

O backend, os testes e parte do motor analítico estão bem avançados para um MVP técnico. Ainda faltam consolidação do frontend, documentação operacional mais completa, observabilidade, hardening de produção, geoprocessamento avançado, validação real em campo e integração corporativa completa.

## Próximo passo

Concluir o ATO 0/1 de documentação e arquitetura, mantendo a suíte de testes verde, e em seguida avançar para o próximo ato definido no roadmap.
