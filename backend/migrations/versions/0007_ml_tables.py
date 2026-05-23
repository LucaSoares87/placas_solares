"""
Cria tabelas ml_model_records e ml_predictions.
Ativa coluna ml_adjusted em transformer_balances.

Revision ID: 0007
Revises: 0006
Create Date: 2025-01-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_model_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("version", sa.String(60), nullable=False),
        sa.Column("model_type", sa.String(40), nullable=False),
        sa.Column("target", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("artifact", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_ml_model_records_version"),
        if_not_exists=True,
    )

    op.create_index(
        "ix_ml_model_records_target",
        "ml_model_records",
        ["target"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ml_model_records_status",
        "ml_model_records",
        ["status"],
        if_not_exists=True,
    )

    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transformer_id", sa.String(30), nullable=False),
        sa.Column("ref_date", sa.Date(), nullable=False),
        sa.Column("target", sa.String(40), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("ci_lower", sa.Float(), nullable=False),
        sa.Column("ci_upper", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(60), nullable=False),
        sa.Column("feature_contributions", sa.JSON(), nullable=True),
        sa.Column("is_anomaly", sa.Boolean(), nullable=True),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )

    op.create_index(
        "ix_ml_predictions_transformer_id",
        "ml_predictions",
        ["transformer_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ml_predictions_ref_date",
        "ml_predictions",
        ["ref_date"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_ml_predictions_is_anomaly",
        "ml_predictions",
        ["is_anomaly"],
        if_not_exists=True,
    )

    op.create_index(
        "ix_transformer_balances_ml_adjusted",
        "transformer_balances",
        ["ml_adjusted"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transformer_balances_ml_adjusted",
        table_name="transformer_balances",
        if_exists=True,
    )

    op.drop_index(
        "ix_ml_predictions_is_anomaly",
        table_name="ml_predictions",
        if_exists=True,
    )
    op.drop_index(
        "ix_ml_predictions_ref_date",
        table_name="ml_predictions",
        if_exists=True,
    )
    op.drop_index(
        "ix_ml_predictions_transformer_id",
        table_name="ml_predictions",
        if_exists=True,
    )
    op.drop_table("ml_predictions", if_exists=True)

    op.drop_index(
        "ix_ml_model_records_status",
        table_name="ml_model_records",
        if_exists=True,
    )
    op.drop_index(
        "ix_ml_model_records_target",
        table_name="ml_model_records",
        if_exists=True,
    )
    op.drop_table("ml_model_records", if_exists=True)