"""
Indexes de performance para queries analíticas do Dashboard.

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-04 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_energy_inferences_transformer_id",
        "energy_inferences",
        ["transformer_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_energy_inferences_computed_at",
        "energy_inferences",
        ["computed_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_energy_inferences_uc_code_computed_at",
        "energy_inferences",
        ["uc_code", "computed_at"],
        if_not_exists=True,
    )

    op.create_index(
        "ix_transformer_balances_transformer_id_computed_at",
        "transformer_balances",
        ["transformer_id", "computed_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_transformer_balances_balance_status",
        "transformer_balances",
        ["balance_status"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_transformer_balances_operational_score",
        "transformer_balances",
        ["operational_score"],
        if_not_exists=True,
    )

    op.create_index(
        "ix_energy_anomalies_transformer_id_resolved",
        "energy_anomalies",
        ["transformer_id", "resolved_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_energy_anomalies_uc_code_resolved",
        "energy_anomalies",
        ["uc_code", "resolved_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_energy_anomalies_severity",
        "energy_anomalies",
        ["severity"],
        if_not_exists=True,
    )

    op.create_index(
        "ix_consumer_units_has_gd",
        "consumer_units",
        ["has_gd"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_consumer_units_transformer_id_has_gd",
        "consumer_units",
        ["transformer_id", "has_gd"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_consumer_units_transformer_id_has_gd",
        table_name="consumer_units",
        if_exists=True,
    )
    op.drop_index(
        "ix_consumer_units_has_gd",
        table_name="consumer_units",
        if_exists=True,
    )
    op.drop_index(
        "ix_energy_anomalies_severity",
        table_name="energy_anomalies",
        if_exists=True,
    )
    op.drop_index(
        "ix_energy_anomalies_uc_code_resolved",
        table_name="energy_anomalies",
        if_exists=True,
    )
    op.drop_index(
        "ix_energy_anomalies_transformer_id_resolved",
        table_name="energy_anomalies",
        if_exists=True,
    )
    op.drop_index(
        "ix_transformer_balances_operational_score",
        table_name="transformer_balances",
        if_exists=True,
    )
    op.drop_index(
        "ix_transformer_balances_balance_status",
        table_name="transformer_balances",
        if_exists=True,
    )
    op.drop_index(
        "ix_transformer_balances_transformer_id_computed_at",
        table_name="transformer_balances",
        if_exists=True,
    )
    op.drop_index(
        "ix_energy_inferences_uc_code_computed_at",
        table_name="energy_inferences",
        if_exists=True,
    )
    op.drop_index(
        "ix_energy_inferences_computed_at",
        table_name="energy_inferences",
        if_exists=True,
    )
    op.drop_index(
        "ix_energy_inferences_transformer_id",
        table_name="energy_inferences",
        if_exists=True,
    )