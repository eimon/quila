"""pricing rules: adjustment type/value and priority

Replaces profitability_percent with adjustment_type (PERCENTAGE | FIXED_PRICE),
adjustment_value and priority. Rules may overlap (highest priority wins) and a
rule may cover a single day (end_date >= start_date).
Existing rows become PERCENTAGE 0 (base price), priority 0.

Revision ID: 011
Revises: 010
Create Date: 2026-11-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

adjustment_type_enum = postgresql.ENUM(
    "PERCENTAGE", "FIXED_PRICE", name="pricingadjustmenttype", create_type=False
)


def upgrade() -> None:
    adjustment_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "pricing_rules",
        sa.Column("adjustment_type", adjustment_type_enum, nullable=False, server_default="PERCENTAGE"),
    )
    op.add_column(
        "pricing_rules",
        sa.Column("adjustment_value", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "pricing_rules",
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    # Defaults were only needed to fill existing rows
    op.alter_column("pricing_rules", "adjustment_type", server_default=None)
    op.alter_column("pricing_rules", "adjustment_value", server_default=None)

    op.drop_constraint("ck_pricing_rules_profitability_non_negative", "pricing_rules", type_="check")
    op.drop_column("pricing_rules", "profitability_percent")

    op.drop_constraint("ck_pricing_rules_end_after_start", "pricing_rules", type_="check")
    op.create_check_constraint("ck_pricing_rules_end_after_start", "pricing_rules", "end_date >= start_date")
    op.create_check_constraint(
        "ck_pricing_rules_adjustment_value_valid",
        "pricing_rules",
        "(adjustment_type = 'PERCENTAGE' AND adjustment_value > -100)"
        " OR (adjustment_type = 'FIXED_PRICE' AND adjustment_value > 0)",
    )


def downgrade() -> None:
    # Best effort: the old model cannot express fixed prices or negative adjustments.
    op.drop_constraint("ck_pricing_rules_adjustment_value_valid", "pricing_rules", type_="check")
    op.drop_constraint("ck_pricing_rules_end_after_start", "pricing_rules", type_="check")

    op.add_column(
        "pricing_rules",
        sa.Column("profitability_percent", sa.Numeric(5, 2), nullable=False, server_default=sa.text("100")),
    )
    op.alter_column("pricing_rules", "profitability_percent", server_default=None)
    op.execute(
        "UPDATE pricing_rules SET profitability_percent = LEAST(GREATEST(100 + adjustment_value, 0), 999.99) "
        "WHERE adjustment_type = 'PERCENTAGE'"
    )
    op.execute("UPDATE pricing_rules SET end_date = start_date + 1 WHERE end_date = start_date")

    op.create_check_constraint(
        "ck_pricing_rules_profitability_non_negative", "pricing_rules", "profitability_percent >= 0"
    )
    op.create_check_constraint("ck_pricing_rules_end_after_start", "pricing_rules", "end_date > start_date")

    # Migration 005 already dropped priority before this revision
    op.drop_column("pricing_rules", "priority")
    op.drop_column("pricing_rules", "adjustment_value")
    op.drop_column("pricing_rules", "adjustment_type")
    op.execute("DROP TYPE IF EXISTS pricingadjustmenttype")
