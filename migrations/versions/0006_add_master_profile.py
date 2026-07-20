"""add master career profile table

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def upgrade() -> None:
    if not _table_exists("master_profiles"):
        op.create_table(
            "master_profiles",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(255), nullable=False, server_default="Default Profile"),
            sa.Column("profile_json", sa.Text, nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime,
                server_default=sa.func.now(),
            ),
        )


def downgrade() -> None:
    op.drop_table("master_profiles")
