"""
Adiciona coluna confidence na tabela transformer_balances.
Prepara ganchos para integração com dados climáticos (Ato 6)
e modelos ML (Ato 7).

Revision ID: 0005
Revises: 0004
Create Date: 2025-01-05 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Confiança média das inferências que compõem o balanço
    op.add_column(
        "transformer_balances",
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=True,
            comment="Confiança média das inferências (0.0 a 1.0)",
        ),
    )

    # Preparação para Ato 6: fator de correção climática
    op.add_column(
        "transformer_balances",
        sa.Column(
            "climate_correction_factor",
            sa.Float(),
            nullable=True,
            comment="Fator de correção baseado em dados climáticos (Ato 6)",
        ),
    )

    # Preparação para Ato 7: flag de ajuste ML
    op.add_column(
        "transformer_balances",
        sa.Column(
            "ml_adjusted",
            sa.Boolean(),
            server_default="false",
            nullable=False,
            comment="Indica se o balanço foi ajustado por modelo ML (Ato 7)",
        ),
    )

    op.create_index(
        "ix_transformer_balances_period_start",
        "transformer_balances",
        ["period_start"],
    )
    op.create_index(
        "ix_transformer_balances_period_end",
        "transformer_balances",
        ["period_end"],
    )


def downgrade() -> None:
    op.drop_index("ix_transformer_balances_period_start", "transformer_balances")
    op.drop_index("ix_transformer_balances_period_end", "transformer_balances")
    op.drop_column("transformer_balances", "ml_adjusted")
    op.drop_column("transformer_balances", "climate_correction_factor")
    op.drop_column("transformer_balances", "confidence")
