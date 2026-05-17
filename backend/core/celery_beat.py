from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # Snapshot diário de todos os transformadores às 02:00
    "refresh-all-snapshots-daily": {
        "task": "workers.dashboard.refresh_all_snapshots",
        "schedule": crontab(hour=2, minute=0),
        "kwargs": {"reference_period": "auto"},
    },
    # Exportação CSV semanal às segundas às 06:00
    "weekly-csv-export": {
        "task": "workers.dashboard.export_csv",
        "schedule": crontab(hour=6, minute=0, day_of_week=1),
        "kwargs": {
            "request_data": {
                "format": "csv",
                "include_anomalies": True,
                "include_calibration": True,
                "include_validations": True,
            }
        },
    },
}
