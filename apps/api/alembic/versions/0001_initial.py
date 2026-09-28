"""Create the V1 schema.

Revision ID: 0001_initial
"""

from alembic import op

from lead_factory.db import Base
from lead_factory.models import Account  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
