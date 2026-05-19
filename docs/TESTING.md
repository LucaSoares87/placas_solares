# Testes

## Estratégia

O projeto utiliza testes unitários e de integração para validar domínio, services, APIs, pipelines e módulos analíticos.

A suíte de testes é critério obrigatório antes de qualquer commit relevante.

## Comando principal

```powershell
python -m pytest
```

Resultado esperado na base estabilizada:

```text
250 passed
```

## Testes por bloco

### Integração

```powershell
python -m pytest backend/tests/integration/test_batch_endpoints.py
python -m pytest backend/tests/integration/test_consumer_units.py
python -m pytest backend/tests/integration/test_dashboard_endpoints.py
python -m pytest backend/tests/integration/test_energy_balance_endpoints.py
python -m pytest backend/tests/integration/test_health.py
```

### Visão computacional

```powershell
python -m pytest backend/tests/test_fv_api.py
python -m pytest backend/tests/test_fv_detection.py
```

### Services

```powershell
python -m pytest backend/tests/test_services.py
python -m pytest backend/tests/unit/test_dashboard_service.py
python -m pytest backend/tests/unit/test_energy_balance_service.py
python -m pytest backend/tests/unit/test_energy_inference_service.py
python -m pytest backend/tests/unit/test_ml_service.py
```

### Domínio

```powershell
python -m pytest backend/tests/unit/test_climate_domain.py
python -m pytest backend/tests/unit/test_energy_balance_domain.py
python -m pytest backend/tests/unit/test_ml_domain.py
```

### ML

```powershell
python -m pytest backend/tests/unit/test_predictor.py
python -m pytest backend/tests/unit/test_trainer.py
```

### Validação e telemetria

```powershell
python -m pytest backend/tests/unit/test_telemetry_validator.py
python -m pytest tests/test_validation.py
```

## Boas práticas

- Rodar testes específicos durante desenvolvimento.
- Rodar a suíte completa antes de commit e push.
- Não alterar módulos estáveis sem teste relacionado.
- Ao mudar schemas, rodar endpoints afetados.
- Ao mudar autenticação, rodar testes de integração.
- Ao mudar ML, rodar domínio, predictor, trainer e ML service.

## Warnings conhecidos

A suíte pode apresentar warnings relacionados a:

- `json_encoders` depreciado no Pydantic;
- campos com prefixo `model_`;
- `datetime.utcnow()` depreciado em Python recente;
- warnings internos de bibliotecas de terceiros.

Esses warnings não quebram a suíte atual, mas devem ser tratados em etapa futura de limpeza técnica.

## Critério mínimo de aceite

Antes de finalizar um ato:

```powershell
python -m pytest
```

A entrega só deve ser considerada estável se a suíte completa passar.
