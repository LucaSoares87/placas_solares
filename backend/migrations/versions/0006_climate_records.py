"""
Cria tabela climate_records e atualiza transformer_balances
com o fator de correção climática real.

Revision ID: 0006
Revises: 0005
Create Date: 2025-01-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "climate_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("ref_date", sa.Date(), nullable=False),
        sa.Column("irradiance_daily_kwh_m2", sa.Float(), nullable=False),
        sa.Column("temperature_avg_c", sa.Float(), nullable=False),
        sa.Column("temperature_max_c", sa.Float(), nullable=False),
        sa.Column("temperature_min_c", sa.Float(), nullable=False),
        sa.Column("wind_speed_avg_ms", sa.Float(), nullable=False),
        sa.Column("cloud_cover_avg_pct", sa.Float(), nullable=False),
        sa.Column("humidity_avg_pct", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("hourly_records", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("irradiance_factor", sa.Float(), nullable=False),
        sa.Column("temperature_factor", sa.Float(), nullable=False),
        sa.Column("cloud_factor", sa.Float(), nullable=False),
        sa.Column("composite_factor", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_climate_records_latitude", "climate_records", ["latitude"])
    op.create_index("ix_climate_records_longitude", "climate_records", ["longitude"])
    op.create_index("ix_climate_records_ref_date", "climate_records", ["ref_date"])
    op.create_unique_constraint(
        "uq_climate_records_location_date",
        "climate_records",
        ["latitude", "longitude", "ref_date"],
    )

    # Ativar o climate_correction_factor no transformer_balances (coluna já criada no Ato 5)
    # Adicionar índice para facilitar joins no Ato 7
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


def downgrade() -> None:
    op.drop_index("ix_transformer_balances_operational_score", "transformer_balances")
    op.drop_index("ix_transformer_balances_balance_status", "transformer_balances")
    op.drop_constraint("uq_climate_records_location_date", "climate_records")
    op.drop_index("ix_climate_records_ref_date", "climate_records")
    op.drop_index("ix_climate_records_longitude", "climate_records")
    op.drop_index("ix_climate_records_latitude", "climate_records")
    op.drop_table("climate_records")
