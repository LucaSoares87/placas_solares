"""energy models — anomalias e campo inference_method

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-02 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adiciona inference_method à tabela energy_inferences
    op.add_column(
        "energy_inferences",
        sa.Column(
            "inference_method",
            sa.String(20),
            nullable=False,
            server_default="default",
        ),
    )

    # Renomeia operational_score em transformer_balances → balance_status
    op.add_column(
        "transformer_balances",
        sa.Column(
            "balance_status",
            sa.String(30),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "transformer_balances",
        sa.Column(
            "gd_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # Nova tabela de anomalias energéticas
    op.create_table(
        "energy_anomalies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uc_code", sa.String(20), nullable=True),
        sa.Column("transformer_id", sa.String(30), nullable=False),
        sa.Column("anomaly_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["uc_code"], ["consumer_units.uc_code"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_energy_anomalies_uc_code", "energy_anomalies", ["uc_code"]
    )
    op.create_index(
        "ix_energy_anomalies_transformer_id",
        "energy_anomalies",
        ["transformer_id"],
    )
    op.create_index(
        "ix_energy_anomalies_detected_at",
        "energy_anomalies",
        ["detected_at"],
    )


def downgrade() -> None:
    op.drop_table("energy_anomalies")
    op.drop_column("transformer_balances", "gd_count")
    op.drop_column("transformer_balances", "balance_status")
    op.drop_column("energy_inferences", "inference_method")
