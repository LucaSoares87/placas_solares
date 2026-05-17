"""
Schedule do Celery Beat — tarefas periódicas do sistema.
"""

from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # ── Clima ──────────────────────────────────────────────────────────────
    "climate.fetch_all_daily": {
        "task": "climate.fetch_all_transformers",
        "schedule": crontab(hour=2, minute=0),         # 02:00 UTC diário
        "kwargs": {
            "date_start_iso": "today-1",
            "date_end_iso": "today",
            "force_refresh": False,
        },
    },

    # ── ML — retreinamento semanal ─────────────────────────────────────────
    "ml.weekly_retrain": {
        "task": "ml.daily_retrain",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),  # Segunda 03:00 UTC
    },

    # ── ML — predições diárias em lote ────────────────────────────────────
    "ml.daily_predictions": {
        "task": "ml.predict_batch",
        "schedule": crontab(hour=4, minute=0),         # 04:00 UTC diário
        "kwargs": {
            "transformer_ids": [],
            "ref_date_iso": "today",
            "target": "energy_loss_pct",
        },
    },

    # ── Balanço energético ─────────────────────────────────────────────────
    "balance.daily_all": {
        "task": "balance.compute_all",
        "schedule": crontab(hour=5, minute=0),
    },
}
