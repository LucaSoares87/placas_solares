"""add dashboard and alert tables

Revision ID: 010_dashboard_alert
Revises: 009_validation_calibration
Create Date: 2025-05-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "010_dashboard_alert"
down_revision = "009_validation_calibration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transformer_id", sa.String(64), nullable=False),
        sa.Column("reference_period", sa.String(32), nullable=False),
        sa.Column("total_ucs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_ucs_fv", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cobertura_fv_pct", sa.Float(), nullable=True),
        sa.Column("kwp_total_estimado", sa.Float(), nullable=True),
        sa.Column("area_total_m2", sa.Float(), nullable=True),
        sa.Column("geracao_total_kwh", sa.Float(), nullable=True),
        sa.Column("consumo_total_kwh", sa.Float(), nullable=True),
        sa.Column("injecao_total_kwh", sa.Float(), nullable=True),
        sa.Column("balanco_estimado_kwh", sa.Float(), nullable=True),
        sa.Column("balanco_real_kwh", sa.Float(), nullable=True),
        sa.Column("erro_balanco_pct", sa.Float(), nullable=True),
        sa.Column("kwp_factor_atual", sa.Float(), nullable=True),
        sa.Column("loss_factor_atual", sa.Float(), nullable=True),
        sa.Column("modelo_convergido", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("score_operacional", sa.String(32), nullable=False, server_default="baixo_risco"),
        sa.Column("total_anomalias_ativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_inspecoes_pendentes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confianca_media_deteccao", sa.Float(), nullable=True),
        sa.Column("gerado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("valido_ate", sa.DateTime(), nullable=True),
        sa.Column("snapshot_metadata", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_snapshot_transformer_id",
        "dashboard_snapshots",
        ["transformer_id"],
    )
    op.create_index(
        "ix_snapshot_transformer_period",
        "dashboard_snapshots",
        ["transformer_id", "reference_period"],
    )

    op.create_table(
        "alert_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transformer_id", sa.String(64), nullable=False),
        sa.Column("uc_code", sa.String(64), nullable=True),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False, server_default="medio"),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("observed_value", sa.Float(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="aberto"),
        sa.Column("acknowledged_by", sa.String(64), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("alert_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_alert_transformer_id",
        "alert_records",
        ["transformer_id"],
    )
    op.create_index(
        "ix_alert_uc_code",
        "alert_records",
        ["uc_code"],
    )
    op.create_index(
        "ix_alert_transformer_status",
        "alert_records",
        ["transformer_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_alert_transformer_status", "alert_records")
    op.drop_index("ix_alert_uc_code", "alert_records")
    op.drop_index("ix_alert_transformer_id", "alert_records")
    op.drop_table("alert_records")
    op.drop_index("ix_snapshot_transformer_period", "dashboard_snapshots")
    op.drop_index("ix_snapshot_transformer_id", "dashboard_snapshots")
    op.drop_table("dashboard_snapshots")
