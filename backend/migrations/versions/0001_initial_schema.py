"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "authorized_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("matricula", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("perfil", sa.String(30), nullable=False, server_default="consulta"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("matricula"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "access_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("matricula", sa.String(20), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(200), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["authorized_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transformers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transformer_id", sa.String(30), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("rated_kva", sa.Float(), nullable=False),
        sa.Column("uc_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gd_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("substation", sa.String(50), nullable=True),
        sa.Column("feeder", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transformer_id"),
    )
    op.create_index("ix_transformers_transformer_id", "transformers", ["transformer_id"])

    op.create_table(
        "consumer_units",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uc_code", sa.String(20), nullable=False),
        sa.Column("transformer_id", sa.String(30), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("profile", sa.String(30), nullable=False, server_default="residential"),
        sa.Column("is_telemetered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_gd", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("gd_installed_kwp", sa.Float(), nullable=True),
        sa.Column("inverter_model", sa.String(100), nullable=True),
        sa.Column("panel_count", sa.Integer(), nullable=True),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["transformer_id"], ["transformers.transformer_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uc_code"),
    )
    op.create_index("ix_consumer_units_uc_code", "consumer_units", ["uc_code"])
    op.create_index("ix_consumer_units_transformer_id", "consumer_units", ["transformer_id"])

    op.create_table(
        "energy_inferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uc_code", sa.String(20), nullable=False),
        sa.Column("transformer_id", sa.String(30), nullable=False),
        sa.Column("has_fv", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("area_m2", sa.Float(), nullable=True),
        sa.Column("kwp_estimated", sa.Float(), nullable=True),
        sa.Column("generation_kw", sa.Float(), nullable=True),
        sa.Column("consumption_estimated_kw", sa.Float(), nullable=False),
        sa.Column("injection_kw_min", sa.Float(), nullable=True),
        sa.Column("injection_kw_max", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("operational_score", sa.String(30), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["uc_code"], ["consumer_units.uc_code"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_energy_inferences_uc_code", "energy_inferences", ["uc_code"])
    op.create_index("ix_energy_inferences_transformer_id", "energy_inferences", ["transformer_id"])
    op.create_index("ix_energy_inferences_computed_at", "energy_inferences", ["computed_at"])

    op.create_table(
        "transformer_balances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transformer_id", sa.String(30), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("measured_kwh", sa.Float(), nullable=False),
        sa.Column("estimated_consumption_kwh", sa.Float(), nullable=False),
        sa.Column("estimated_generation_kwh", sa.Float(), nullable=False),
        sa.Column("estimated_injection_kwh", sa.Float(), nullable=False),
        sa.Column("technical_losses_kwh", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("residual_kwh", sa.Float(), nullable=False),
        sa.Column("absolute_error", sa.Float(), nullable=False),
        sa.Column("percentage_error", sa.Float(), nullable=False),
        sa.Column("operational_score", sa.String(30), nullable=False),
        sa.Column("uc_count", sa.Integer(), nullable=False),
        sa.Column("telemetered_count", sa.Integer(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["transformer_id"], ["transformers.transformer_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transformer_balances_transformer_id",
        "transformer_balances",
        ["transformer_id"],
    )


def downgrade() -> None:
    op.drop_table("transformer_balances")
    op.drop_table("energy_inferences")
    op.drop_table("consumer_units")
    op.drop_table("transformers")
    op.drop_table("access_logs")
    op.drop_table("authorized_users")
