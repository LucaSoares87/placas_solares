# Variáveis de Ambiente

Este documento descreve as principais variáveis necessárias para execução local, testes e preparação para ambiente produtivo.

## Aplicação

```env
APP_ENV=development
APP_NAME=EnergyInferencePlatform
APP_VERSION=0.1.0
APP_SECRET_KEY=change-this-app-secret-with-at-least-32-characters
DEBUG=false
```

## Banco de dados

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/energy_platform
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
DATABASE_POOL_TIMEOUT=30
```

Banco utilizado nos testes:

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/energy_platform_test
```

## Redis

```env
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_DB=1
REDIS_CELERY_DB=2
REDIS_CACHE_TTL=3600
```

## Celery

```env
CELERY_BROKER_URL=redis://localhost:6379/2
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_TASK_SOFT_TIME_LIMIT=300
CELERY_TASK_TIME_LIMIT=600
```

## JWT

```env
JWT_SECRET_KEY=change-this-jwt-secret-with-at-least-32-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

## APIs climáticas

```env
NASA_POWER_BASE_URL=https://power.larc.nasa.gov/api/temporal/hourly/point
PVGIS_BASE_URL=https://re.jrc.ec.europa.eu/api/v5_2
INMET_BASE_URL=https://apitempo.inmet.gov.br
INMET_API_TOKEN=
```

## Machine Learning e visão computacional

```env
ML_MODEL_BASE_PATH=/data/models
YOLO_MODEL_PATH=/data/models/fv_detector.pt
YOLO_CONFIDENCE_THRESHOLD=0.45
YOLO_IOU_THRESHOLD=0.5
YOLO_MAX_IMAGE_SIZE_MB=20
IMAGE_GSD_DEFAULT=0.15
```

## Constantes energéticas

```env
KWP_FACTOR_DEFAULT=0.18
PERFORMANCE_RATIO_DEFAULT=0.78
PANEL_EFFICIENCY_DEFAULT=0.20
```

## Observabilidade

```env
PROMETHEUS_ENABLED=false
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Boas práticas

- Nunca versionar `.env` real.
- Usar `.env.example` como referência pública.
- Chaves JWT e segredos devem possuir pelo menos 32 caracteres.
- Ambientes devem ser separados em `development`, `staging` e `production`.
- Credenciais corporativas devem ser tratadas fora do código-fonte.
