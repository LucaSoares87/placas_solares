"""
Task: ingestão de leituras telemetradas em lote.

Fluxo:
  1. Recebe lista de payloads brutos (dicts) com source_id + grandezas.
  2. Valida e normaliza cada leitura.
  3. Aplica filtros de qualidade (voltage_range, power_factor).
  4. Persiste em bulk na tabela telemetry_readings.
  5. Registra BatchJob com resultado.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import structlog

from backend.models.batch_job import BatchJob
from backend.models.telemetry_reading import TelemetryReading
from backend.repositories.batch_job_repository import BatchJobRepository
from backend.repositories.telemetry_repository import TelemetryRepository
from backend.worker.context import db_session
from backend.worker.validators.telemetry_validator import TelemetryValidator

logger = structlog.get_logger(__name__)


async def ingest_telemetry_data(
    ctx: dict,
    *,
    job_id: str,
    payloads: list[dict[str, Any]],
    source_type: str = "uc",
) -> dict:
    """
    ARQ task — persiste leituras telemetradas em massa.

    Args:
        ctx: contexto ARQ (contém db_factory).
        job_id: identificador rastreável do job.
        payloads: lista de dicts com os campos da TelemetryReading.
        source_type: 'uc' ou 'transformer'.

    Returns:
        dict com totais de processamento.
    """
    log = logger.bind(job_id=job_id, source_type=source_type, total=len(payloads))
    log.info("telemetry_ingest.started")

    async with db_session(ctx) as session:
        job_repo = BatchJobRepository(session)
        tel_repo = TelemetryRepository(session)
        validator = TelemetryValidator()

        await job_repo.create_job(
            job_id=job_id,
            job_type="telemetry_ingest",
            total_items=len(payloads),
        )
        await job_repo.mark_running(job_id)

        valid_readings: list[TelemetryReading] = []
        failed = 0
        suspect = 0

        for raw in payloads:
            try:
                validated = validator.validate(raw, source_type=source_type)
                quality = validator.quality_flag(validated)
                if quality == "invalid":
                    failed += 1
                    continue

                reading = TelemetryReading(
                    source_id=validated["source_id"],
                    source_type=source_type,
                    measured_at=validated["measured_at"],
                    active_power_kw=validated.get("active_power_kw"),
                    reactive_power_kvar=validated.get("reactive_power_kvar"),
                    voltage_v=validated.get("voltage_v"),
                    current_a=validated.get("current_a"),
                    power_factor=validated.get("power_factor"),
                    energy_kwh_import=validated.get("energy_kwh_import"),
                    energy_kwh_export=validated.get("energy_kwh_export"),
                    quality_flag=quality,
                    raw_payload=json.dumps(raw),
                )
                if quality == "suspect":
                    suspect += 1

                valid_readings.append(reading)

            except Exception as exc:
                failed += 1
                log.warning("telemetry_ingest.row_error", error=str(exc))

        inserted = 0
        if valid_readings:
            inserted = await tel_repo.bulk_insert(valid_readings)

        summary = (
            f"inserted={inserted} suspect={suspect} failed={failed} "
            f"total={len(payloads)}"
        )
        await job_repo.mark_success(
            job_id,
            processed=inserted,
            failed=failed,
            summary=summary,
        )
        log.info("telemetry_ingest.finished", inserted=inserted, failed=failed)
        return {
            "job_id": job_id,
            "inserted": inserted,
            "suspect": suspect,
            "failed": failed,
            "total": len(payloads),
        }
