"""add validation and calibration tables

Revision ID: 009_validation_calibration
Revises: 008_fv_detection
Create Date: 2025-05-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "009_validation_calibration"
down_revision = "008_fv_detection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validation_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transformer_id", sa.String(64), nullable=False),
        sa.Column("uc_code", sa.String(64), nullable=True),
        sa.Column("reference_period", sa.String(32), nullable=False),
        sa.Column("consumo_estimado_kwh", sa.Float(), nullable=False),
        sa.Column("geracao_estimada_kwh", sa.Float(), nullable=False),
        sa.Column("injecao_estimada_kwh", sa.Float(), nullable=False),
        sa.Column("balanco_estimado_kwh", sa.Float(), nullable=False),
        sa.Column("consumo_real_kwh", sa.Float(), nullable=True),
        sa.Column("geracao_real_kwh", sa.Float(), nullable=True),
        sa.Column("balanco_real_kwh", sa.Float(), nullable=True),
        sa.Column("erro_absoluto_kwh", sa.Float(), nullable=True),
        sa.Column("erro_percentual_pct", sa.Float(), nullable=True),
        sa.Column("desvio_sazonal_pct", sa.Float(), nullable=True),
        sa.Column("score_operacional", sa.String(32), nullable=False, server_default="baixo_risco"),
        sa.Column("status_validacao", sa.String(32), nullable=False, server_default="pendente"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_validation_transformer_id", "validation_records", ["transformer_id"])
    op.create_index("ix_validation_uc_code", "validation_records", ["uc_code"])
    op.create_index(
        "ix_validation_transformer_period",
        "validation_records",
        ["transformer_id", "reference_period"],
    )

    op.create_table(
        "anomaly_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uc_code", sa.String(64), nullable=False),
        sa.Column("transformer_id", sa.String(64), nullable=False),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("consensus", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("isolation_forest_score", sa.Float(), nullable=True),
        sa.Column("one_class_svm_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("recommendation", sa.String(64), nullable=True),
        sa.Column("features_json", postgresql.JSONB(), nullable=True),
        sa.Column("detected_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(64), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anomaly_uc_code", "anomaly_records", ["uc_code"])
    op.create_index("ix_anomaly_transformer_id", "anomaly_records", ["transformer_id"])
    op.create_index(
        "ix_anomaly_transformer_uc",
        "anomaly_records",
        ["transformer_id", "uc_code"],
    )

    op.create_table(
        "calibration_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transformer_id", sa.String(64), nullable=False),
        sa.Column("kwp_factor_old", sa.Float(), nullable=False),
        sa.Column("kwp_factor_new", sa.Float(), nullable=False),
        sa.Column("kwp_factor_delta", sa.Float(), nullable=False),
        sa.Column("loss_factor_old", sa.Float(), nullable=True),
        sa.Column("loss_factor_new", sa.Float(), nullable=True),
        sa.Column("loss_factor_delta", sa.Float(), nullable=True),
        sa.Column("samples_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mean_kwp_error_pct", sa.Float(), nullable=True),
        sa.Column("mean_consumo_error_pct", sa.Float(), nullable=True),
        sa.Column("converged", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cycle_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calibration_transformer_id",
        "calibration_history",
        ["transformer_id"],
    )


def downgrade() -> None:
    op.drop_table("calibration_history")
    op.drop_index("ix_anomaly_transformer_uc", "anomaly_records")
    op.drop_index("ix_anomaly_transformer_id", "anomaly_records")
    op.drop_index("ix_anomaly_uc_code", "anomaly_records")
    op.drop_table("anomaly_records")
    op.drop_index("ix_validation_transformer_period", "validation_records")
    op.drop_index("ix_validation_uc_code", "validation_records")
    op.drop_index("ix_validation_transformer_id", "validation_records")
    op.drop_table("validation_records")
