"""booking holds for the chatbot

Adds CHATBOT to bookingsource and the hold/lead columns on bookings:
expires_at, guests, lead_name, lead_phone, lead_email (all nullable).

Revision ID: 013
Revises: 012
Create Date: 2026-11-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block on older PostgreSQL
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE bookingsource ADD VALUE IF NOT EXISTS 'CHATBOT'")

    op.add_column("bookings", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("guests", sa.Integer(), nullable=True))
    op.add_column("bookings", sa.Column("lead_name", sa.String(length=255), nullable=True))
    op.add_column("bookings", sa.Column("lead_phone", sa.String(length=50), nullable=True))
    op.add_column("bookings", sa.Column("lead_email", sa.String(length=255), nullable=True))
    op.create_check_constraint("ck_bookings_guests_positive", "bookings", "guests > 0")
    op.create_index("ix_bookings_expires_at", "bookings", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_bookings_expires_at", table_name="bookings")
    op.drop_constraint("ck_bookings_guests_positive", "bookings", type_="check")
    op.drop_column("bookings", "lead_email")
    op.drop_column("bookings", "lead_phone")
    op.drop_column("bookings", "lead_name")
    op.drop_column("bookings", "guests")
    op.drop_column("bookings", "expires_at")
    # PostgreSQL cannot drop enum values: CHATBOT stays in bookingsource (see 008 for PAID)
