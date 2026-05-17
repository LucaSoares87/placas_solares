"""
Registro de modelos ML.

Responsabilidades:
  1. Salvar artefato (pickle) e metadados no banco
  2. Carregar o modelo ativo para um target
  3. Deprecar versões antigas
  4. Instância em memória com cache de Predictor
"""

from __future__ import annotations

from typing import Optional

import structlog

from backend.domain.ml_model import ModelStatus, ModelType, PredictionTarget, TrainingConfig
from backend.repositories.ml_model_repository import MlModelRepository
from backend.services.ml.predictor import Predictor

logger = structlog.get_logger(__name__)

# Cache em memória: target → Predictor ativo
_predictor_cache: dict[str, Predictor] = {}


class ModelRegistry:
    def __init__(self, repo: MlModelRepository) -> None:
        self._repo = repo

    async def register(
        self,
        version: str,
        model_type: ModelType,
        target: PredictionTarget,
        config: TrainingConfig,
        metrics_dict: dict,
        artifact: bytes,
    ) -> str:
        """Persiste o modelo treinado e o marca como ativo."""
        # Deprecar versões anteriores ativas
        await self._repo.deprecate_active(target.value)

        model_id = await self._repo.save_model(
            version=version,
            model_type=model_type.value,
            target=target.value,
            status=ModelStatus.READY.value,
            config_json=config.__dict__,
            metrics_json=metrics_dict,
            artifact=artifact,
        )

        # Limpar cache para forçar recarga
        _predictor_cache.pop(target.value, None)

        logger.info(
            "registry.model_registered",
            version=version,
            target=target.value,
            model_id=model_id,
        )
        return model_id

    async def get_predictor(self, target: PredictionTarget) -> Optional[Predictor]:
        """Retorna Predictor ativo para o target (com cache em memória)."""
        key = target.value

        if key in _predictor_cache:
            return _predictor_cache[key]

        record = await self._repo.get_active_model(target.value)
        if not record:
            logger.warning("registry.no_active_model", target=key)
            return None

        predictor = Predictor(
            artifact=record.artifact,
            model_version=record.version,
            model_rmse=float(record.metrics_json.get("rmse", 1.0)),
            target=target,
        )
        _predictor_cache[key] = predictor
        logger.info("registry.predictor_loaded", version=record.version, target=key)
        return predictor

    async def list_versions(self, target: PredictionTarget) -> list[dict]:
        return await self._repo.list_versions(target.value)

    def invalidate_cache(self, target: Optional[PredictionTarget] = None) -> None:
        if target:
            _predictor_cache.pop(target.value, None)
        else:
            _predictor_cache.clear()
        logger.info("registry.cache_invalidated", target=str(target))
