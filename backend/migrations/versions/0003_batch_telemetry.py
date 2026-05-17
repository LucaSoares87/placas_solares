"""batch_jobs e telemetry_readings

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── telemetry_readings ────────────────────────────────────────────────────
    op.create_table(
        "telemetry_readings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.String(30), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="uc"),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active_power_kw", sa.Float(), nullable=True),
        sa.Column("reactive_power_kvar", sa.Float(), nullable=True),
        sa.Column("voltage_v", sa.Float(), nullable=True),
        sa.Column("current_a", sa.Float(), nullable=True),
        sa.Column("power_factor", sa.Float(), nullable=True),
        sa.Column("energy_kwh_import", sa.Float(), nullable=True),
        sa.Column("energy_kwh_export", sa.Float(), nullable=True),
        sa.Column("quality_flag", sa.String(10), nullable=False, server_default="ok"),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telemetry_readings_source_id", "telemetry_readings", ["source_id"])
    op.create_index("ix_telemetry_readings_measured_at", "telemetry_readings", ["measured_at"])

    # ── batch_jobs ────────────────────────────────────────────────────────────
    op.create_table(
        "batch_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(100), unique=True, nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("transformer_id", sa.String(30), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batch_jobs_job_id", "batch_jobs", ["job_id"], unique=True)
    op.create_index("ix_batch_jobs_transformer_id", "batch_jobs", ["transformer_id"])
    op.create_index("ix_batch_jobs_status", "batch_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("batch_jobs")
    op.drop_table("telemetry_readings")
