"""
Indexes de performance para queries analíticas do Dashboard.

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-04 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── energy_inferences ────────────────────────────────────────────────────
    # Queries de ranking de GD e balanço por transformador
    op.create_index(
        "ix_energy_inferences_transformer_id",
        "energy_inferences",
        ["transformer_id"],
    )
    op.create_index(
        "ix_energy_inferences_computed_at",
        "energy_inferences",
        ["computed_at"],
    )
    # Índice composto para consulta de última inferência por UC
    op.create_index(
        "ix_energy_inferences_uc_code_computed_at",
        "energy_inferences",
        ["uc_code", "computed_at"],
    )

    # ── transformer_balances ─────────────────────────────────────────────────
    op.create_index(
        "ix_transformer_balances_transformer_id_computed_at",
        "transformer_balances",
        ["transformer_id", "computed_at"],
    )
    op.create_index(
        "ix_transformer_balances_balance_status",
        "transformer_balances",
        ["balance_status"],
    )
    op.create_index(
        "ix_transformer_balances_operational_score",
        "transformer_balances",
        ["operational_score"],
    )

    # ── energy_anomalies ─────────────────────────────────────────────────────
    op.create_index(
        "ix_energy_anomalies_transformer_id_resolved",
        "energy_anomalies",
        ["transformer_id", "resolved_at"],
    )
    op.create_index(
        "ix_energy_anomalies_uc_code_resolved",
        "energy_anomalies",
        ["uc_code", "resolved_at"],
    )
    op.create_index(
        "ix_energy_anomalies_severity",
        "energy_anomalies",
        ["severity"],
    )

    # ── consumer_units ───────────────────────────────────────────────────────
    op.create_index(
        "ix_consumer_units_has_gd",
        "consumer_units",
        ["has_gd"],
    )
    op.create_index(
        "ix_consumer_units_transformer_id_has_gd",
        "consumer_units",
        ["transformer_id", "has_gd"],
    )


def downgrade() -> None:
    op.drop_index("ix_energy_inferences_transformer_id", "energy_inferences")
    op.drop_index("ix_energy_inferences_computed_at", "energy_inferences")
    op.drop_index("ix_energy_inferences_uc_code_computed_at", "energy_inferences")
    op.drop_index("ix_transformer_balances_transformer_id_computed_at", "transformer_balances")
    op.drop_index("ix_transformer_balances_balance_status", "transformer_balances")
    op.drop_index("ix_transformer_balances_operational_score", "transformer_balances")
    op.drop_index("ix_energy_anomalies_transformer_id_resolved", "energy_anomalies")
    op.drop_index("ix_energy_anomalies_uc_code_resolved", "energy_anomalies")
    op.drop_index("ix_energy_anomalies_severity", "energy_anomalies")
    op.drop_index("ix_consumer_units_has_gd", "consumer_units")
    op.drop_index("ix_consumer_units_transformer_id_has_gd", "consumer_units")
