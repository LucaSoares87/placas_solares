"""
Task: despacho de alertas por e-mail e/ou webhook quando anomalias
ou balanços críticos são detectados.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from backend.core.config import settings
from backend.repositories.batch_job_repository import BatchJobRepository
from backend.worker.context import db_session

logger = structlog.get_logger(__name__)


async def dispatch_alerts(
    ctx: dict,
    *,
    job_id: str,
    alerts: list[dict[str, Any]],
) -> dict:
    """
    ARQ task — envia alertas para os canais configurados.

    Args:
        ctx: contexto ARQ.
        job_id: ID rastreável.
        alerts: lista de dicts com campos: transformer_id, type, message, severity.
    """
    log = logger.bind(job_id=job_id, total_alerts=len(alerts))
    log.info("alert_dispatcher.started")

    async with db_session(ctx) as session:
        job_repo = BatchJobRepository(session)
        await job_repo.create_job(
            job_id=job_id,
            job_type="alert_dispatch",
            total_items=len(alerts),
        )
        await job_repo.mark_running(job_id)

    sent = 0
    failed = 0

    for alert in alerts:
        try:
            await _send_alert(alert)
            sent += 1
        except Exception as exc:
            failed += 1
            log.warning(
                "alert_dispatcher.send_error",
                alert=alert.get("type"),
                error=str(exc),
            )

    async with db_session(ctx) as session:
        job_repo = BatchJobRepository(session)
        await job_repo.mark_success(
            job_id,
            processed=sent,
            failed=failed,
            summary=f"sent={sent} failed={failed}",
        )

    log.info("alert_dispatcher.finished", sent=sent, failed=failed)
    return {"job_id": job_id, "sent": sent, "failed": failed}


async def _send_alert(alert: dict[str, Any]) -> None:
    """Envia alerta para o webhook configurado."""
    webhook_url = settings.ALERT_WEBHOOK_URL
    if not webhook_url:
        logger.debug("alert_dispatcher.no_webhook_configured")
        return

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system": "unidades_geradoras",
        **alert,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            webhook_url,
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        logger.info(
            "alert_dispatcher.webhook_sent",
            status=response.status_code,
            alert_type=alert.get("type"),
        )
