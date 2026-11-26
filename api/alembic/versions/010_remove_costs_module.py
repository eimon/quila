"""remove costs module

Drops the property_costs table, its enum types and properties.avg_stay_days.
Prices no longer depend on costs (see 011 for the new pricing rule shape).

Revision ID: 010
Revises: 009
Create Date: 2026-11-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("property_costs")
    op.execute("DROP TYPE IF EXISTS costcalculationtype")
    op.execute("DROP TYPE IF EXISTS costcategory")

    op.drop_constraint("ck_properties_avg_stay_days_positive", "properties", type_="check")
    op.drop_column("properties", "avg_stay_days")


def downgrade() -> None:
    # Best effort: restores the schema shape; cost rows are not recoverable.
    op.add_column(
        "properties",
        sa.Column("avg_stay_days", sa.Integer(), nullable=False, server_default=sa.text("3")),
    )
    op.create_check_constraint("ck_properties_avg_stay_days_positive", "properties", "avg_stay_days > 0")

    costcategory = postgresql.ENUM(
        "RECURRING_MONTHLY", "PER_DAY_RESERVATION", "PER_RESERVATION", name="costcategory", create_type=False
    )
    costcalculationtype = postgresql.ENUM("FIXED_AMOUNT", "PERCENTAGE", name="costcalculationtype", create_type=False)
    costcategory.create(op.get_bind(), checkfirst=True)
    costcalculationtype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "property_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", costcategory, nullable=False),
        sa.Column("calculation_type", costcalculationtype, nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "root_cost_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("property_costs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("value >= 0", name="ck_property_costs_value_non_negative"),
        sa.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="ck_property_costs_end_after_start",
        ),
    )
    op.create_index("ix_property_costs_id", "property_costs", ["id"])
    op.create_index("ix_property_costs_property_id", "property_costs", ["property_id"])
    op.create_index("ix_property_costs_root_cost_id", "property_costs", ["root_cost_id"])
    op.create_index("ix_property_costs_property_id_end_date", "property_costs", ["property_id", "end_date"])
