"""
Testes unitários do MlService com dependências mockadas.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from backend.domain.ml_model import (
    FEATURE_NAMES,
    ModelType,
    PredictionTarget,
    TrainingConfig,
)
from backend.services.ml_service import MlService


def _make_service():
    session = MagicMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    session.commit = AsyncMock()
    service = MlService(session)
    service._repo = MagicMock()
    service._repo.mark_failed = AsyncMock()
    service._repo.save_prediction = AsyncMock()
    service._repo.get_anomalies = AsyncMock(return_value=[])
    service._registry = MagicMock()
    service._registry.register = AsyncMock()
    service._registry.get_predictor = AsyncMock(return_value=None)
    service._feature_eng = MagicMock()
    return service


def _make_synthetic_df(n: int = 50) -> pd.DataFrame:
    import numpy as np
    rng = np.random.default_rng(7)
    rows = []
    for i in range(n):
        row = {name: rng.uniform(0.1, 10.0) for name in FEATURE_NAMES}
        row["target"] = row["error_pct"] * 0.5 + rng.normal(0, 0.3)
        row["transformer_id"] = f"TR-{i:03d}"
        row["ref_date"] = f"2025-01-{(i % 28) + 1:02d}"
        rows.append(row)
    return pd.DataFrame(rows)


@pytest.mark.asyncio
async def test_train_insufficient_data():
    service = _make_service()
    service._feature_eng.build_training_dataset = AsyncMock(
        return_value=pd.DataFrame()
    )
    config = TrainingConfig()
    with pytest.raises(ValueError, match="insuficientes"):
        await service.train(config)


@pytest.mark.asyncio
async def test_train_calls_registry_on_acceptable_model():
    service = _make_service()
    df = _make_synthetic_df(80)
    service._feature_eng.build_training_dataset = AsyncMock(return_value=df)
    service._repo.deprecate_active = AsyncMock()
    service._repo.save_model = AsyncMock(return_value="v_test")

    config = TrainingConfig(
        model_type=ModelType.GRADIENT_BOOSTING,
        n_estimators=50,
    )
    result = await service.train(config)

    assert result.version.startswith("v")
    assert result.n_samples == 80


@pytest.mark.asyncio
async def test_predict_no_active_model():
    service = _make_service()
    service._registry.get_predictor = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="Nenhum modelo ativo"):
        await service.predict(
            transformer_id="TR-001",
            ref_date=date(2025, 1, 1),
            target=PredictionTarget.ENERGY_LOSS_PCT,
        )


@pytest.mark.asyncio
async def test_predict_no_balance():
    from unittest.mock import MagicMock

    service = _make_service()
    predictor_mock = MagicMock()
    service._registry.get_predictor = AsyncMock(return_value=predictor_mock)
    service._session.scalar = AsyncMock(return_value=None)  # sem balanço

    with pytest.raises(ValueError, match="Balanço não encontrado"):
        await service.predict(
            transformer_id="TR-001",
            ref_date=date(2025, 1, 1),
            target=PredictionTarget.ENERGY_LOSS_PCT,
        )


@pytest.mark.asyncio
async def test_get_anomalies_empty():
    service = _make_service()
    service._repo.get_anomalies = AsyncMock(return_value=[])
    result = await service.get_anomalies()
    assert result == []
