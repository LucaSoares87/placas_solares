"""
Task: processamento em lote de inferências energéticas para um transformador.

Fluxo:
  1. Busca todas as UCs do transformador.
  2. Divide em chunks de BATCH_CHUNK_SIZE.
  3. Para cada UC:
     a. Verifica se há leitura telemetrada recente → usa dados reais.
     b. Caso contrário → usa inferência por perfil (estatística).
  4. Após processar todas as UCs → computa balanço do transformador.
  5. Detecta anomalias no balanço.
  6. Registra resultado no BatchJob.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from backend.core.config import settings
from backend.domain.constants import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM
from backend.domain.entities import (
    EnergyStatus,
    InferenceMethod,
    RiskScore,
)
from backend.models.energy_inference import EnergyInference
from backend.repositories.batch_job_repository import BatchJobRepository
from backend.repositories.consumer_unit_repository import ConsumerUnitRepository
from backend.repositories.energy_inference_repository import EnergyInferenceRepository
from backend.repositories.telemetry_repository import TelemetryRepository
from backend.repositories.transformer_repository import TransformerRepository
from backend.schemas.energy_inference import EnergyInferenceCreate
from backend.services.energy_inference_service import EnergyInferenceService
from backend.worker.context import db_session
from backend.worker.anomaly_detector import AnomalyDetector

logger = structlog.get_logger(__name__)


async def run_batch_inference_for_transformer(
    ctx: dict,
    *,
    job_id: str,
    transformer_id: str,
    measured_kwh: float,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    """
    ARQ task — processa inferências de todas as UCs de um transformador.

    Args:
        ctx: contexto ARQ.
        job_id: ID rastreável do job.
        transformer_id: ID do transformador a processar.
        measured_kwh: energia medida no medidor do transformador (kWh).
        period_start: ISO string do início do período.
        period_end: ISO string do fim do período.
    """
    log = logger.bind(job_id=job_id, transformer_id=transformer_id)
    log.info("batch_inference.started")

    p_start = datetime.fromisoformat(period_start)
    p_end = datetime.fromisoformat(period_end)

    async with db_session(ctx) as session:
        job_repo = BatchJobRepository(session)
        uc_repo = ConsumerUnitRepository(session)
        tr_repo = TransformerRepository(session)
        tel_repo = TelemetryRepository(session)
        inf_repo = EnergyInferenceRepository(session)
        inf_service = EnergyInferenceService(session)
        anomaly_detector = AnomalyDetector(session)

        # Valida transformador
        transformer = await tr_repo.get_by_transformer_id(transformer_id)
        if not transformer:
            log.error("batch_inference.transformer_not_found")
            return {"error": f"Transformador {transformer_id} não encontrado."}

        uc_list = await uc_repo.list_by_transformer(transformer_id, limit=10_000)
        total = len(uc_list)

        await job_repo.create_job(
            job_id=job_id,
            job_type="batch_inference",
            transformer_id=transformer_id,
            total_items=total,
        )
        await job_repo.mark_running(job_id)

        processed = 0
        failed = 0
        telemetered_count = 0

        # ── Processamento por chunks ──────────────────────────────────────────
        chunk_size = settings.BATCH_CHUNK_SIZE

        for chunk_start in range(0, total, chunk_size):
            chunk = uc_list[chunk_start: chunk_start + chunk_size]
            tasks = [
                _process_single_uc(
                    uc=uc,
                    p_start=p_start,
                    p_end=p_end,
                    tel_repo=tel_repo,
                    inf_repo=inf_repo,
                    inf_service=inf_service,
                )
                for uc in chunk
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for uc, result in zip(chunk, results):
                if isinstance(result, Exception):
                    failed += 1
                    log.warning(
                        "batch_inference.uc_error",
                        uc_code=uc.uc_code,
                        error=str(result),
                    )
                else:
                    processed += 1
                    if result.get("method") == InferenceMethod.TELEMETRY:
                        telemetered_count += 1

        # ── Balanço do transformador ─────────────────────────────────────────
        balance = None
        try:
            balance = await inf_service.compute_transformer_balance(
                transformer_id=transformer_id,
                measured_kwh=measured_kwh,
                period_start=p_start,
                period_end=p_end,
            )
            log.info(
                "batch_inference.balance_computed",
                error_pct=balance.percentage_error,
                status=balance.balance_status,
            )
        except Exception as exc:
            log.error("batch_inference.balance_error", error=str(exc))

        # ── Detecção de anomalias ────────────────────────────────────────────
        anomalies_detected = 0
        if balance:
            try:
                anomalies_detected = await anomaly_detector.analyze_balance(balance)
            except Exception as exc:
                log.warning("batch_inference.anomaly_detection_error", error=str(exc))

        summary = (
            f"processed={processed} failed={failed} "
            f"telemetered={telemetered_count} anomalies={anomalies_detected}"
        )
        await job_repo.mark_success(
            job_id,
            processed=processed,
            failed=failed,
            summary=summary,
        )
        log.info("batch_inference.finished", summary=summary)

        return {
            "job_id": job_id,
            "transformer_id": transformer_id,
            "processed": processed,
            "failed": failed,
            "telemetered_count": telemetered_count,
            "anomalies_detected": anomalies_detected,
            "balance_status": balance.balance_status if balance else None,
            "percentage_error": balance.percentage_error if balance else None,
        }


async def _process_single_uc(
    *,
    uc: Any,
    p_start: datetime,
    p_end: datetime,
    tel_repo: TelemetryRepository,
    inf_repo: EnergyInferenceRepository,
    inf_service: EnergyInferenceService,
) -> dict:
    """Processa a inferência de uma única UC."""

    # Tenta usar dados telemetrados recentes
    if uc.is_telemetered:
        reading = await tel_repo.get_latest_by_source(uc.uc_code, source_type="uc")
        if reading and reading.measured_at >= p_start:
            inference = await _build_telemetry_inference(uc, reading, inf_service)
            return {"uc_code": uc.uc_code, "method": InferenceMethod.TELEMETRY}

    # Fallback: inferência por perfil estatístico
    await inf_service.infer_from_profile(uc.uc_code)
    return {"uc_code": uc.uc_code, "method": InferenceMethod.STATISTICAL}


async def _build_telemetry_inference(
    uc: Any,
    reading: Any,
    inf_service: EnergyInferenceService,
) -> EnergyInference:
    """Constrói e registra inferência a partir de leitura telemetrada."""
    kw = reading.active_power_kw or 0.0
    export_kw = (reading.energy_kwh_export or 0.0)

    has_fv = uc.has_gd
    kwp = uc.gd_installed_kwp or 0.0
    generation_kw = None
    injection_min = None
    injection_max = None
    status = EnergyStatus.NORMAL

    if has_fv and export_kw > 0:
        generation_kw = round(export_kw, 4)
        injection_min = round(export_kw * 0.8, 4)
        injection_max = round(export_kw * 1.0, 4)
        status = EnergyStatus.INJECTION_DETECTED

    payload = EnergyInferenceCreate(
        uc_code=uc.uc_code,
        transformer_id=uc.transformer_id,
        has_fv=has_fv,
        kwp_estimated=kwp if has_fv else None,
        generation_kw=generation_kw,
        consumption_estimated_kw=abs(kw),
        injection_kw_min=injection_min,
        injection_kw_max=injection_max,
        status=status,
        confidence=CONFIDENCE_HIGH,
        operational_score=RiskScore.LOW,
        inference_method=InferenceMethod.TELEMETRY,
    )
    return await inf_service.register_inference(payload)
