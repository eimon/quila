"""property catalog fields

Adds the guest-facing catalog data used by the public catalog export and the
chatbot: max_guests, amenities, check-in/out times, cancellation policy and
house rules. All columns are nullable so existing properties stay valid.

Revision ID: 012
Revises: 011
Create Date: 2026-11-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("properties", sa.Column("max_guests", sa.Integer(), nullable=True))
    op.add_column("properties", sa.Column("amenities", sa.JSON(), nullable=True))
    op.add_column("properties", sa.Column("check_in_time", sa.Time(), nullable=True))
    op.add_column("properties", sa.Column("check_out_time", sa.Time(), nullable=True))
    op.add_column("properties", sa.Column("cancellation_policy", sa.Text(), nullable=True))
    op.add_column("properties", sa.Column("house_rules", sa.Text(), nullable=True))
    op.create_check_constraint("ck_properties_max_guests_positive", "properties", "max_guests > 0")


def downgrade() -> None:
    op.drop_constraint("ck_properties_max_guests_positive", "properties", type_="check")
    op.drop_column("properties", "house_rules")
    op.drop_column("properties", "cancellation_policy")
    op.drop_column("properties", "check_out_time")
    op.drop_column("properties", "check_in_time")
    op.drop_column("properties", "amenities")
    op.drop_column("properties", "max_guests")
