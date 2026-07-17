"""add resume tracking columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    columns = [c["name"] for c in inspect(bind).get_columns(table)]
    return column in columns


def upgrade() -> None:
    if not _column_exists("resumes", "source_type"):
        op.add_column("resumes", sa.Column("source_type", sa.String(50), server_default="import"))
    if not _column_exists("resumes", "source_filename"):
        op.add_column("resumes", sa.Column("source_filename", sa.String(500), server_default=""))
    if not _column_exists("resumes", "source_hash"):
        op.add_column("resumes", sa.Column("source_hash", sa.String(64), server_default=""))
    if not _column_exists("resumes", "is_original"):
        op.add_column("resumes", sa.Column("is_original", sa.Boolean, server_default=sa.text("1")))


def downgrade() -> None:
    if _column_exists("resumes", "is_original"):
        op.drop_column("resumes", "is_original")
    if _column_exists("resumes", "source_hash"):
        op.drop_column("resumes", "source_hash")
    if _column_exists("resumes", "source_filename"):
        op.drop_column("resumes", "source_filename")
    if _column_exists("resumes", "source_type"):
        op.drop_column("resumes", "source_type")
