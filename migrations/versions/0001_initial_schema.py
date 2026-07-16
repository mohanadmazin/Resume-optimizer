"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("data_json", sa.Text, nullable=False),
        sa.Column("raw_text", sa.Text, server_default=""),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("resume_id", sa.Integer, sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("job_descriptions.id"), nullable=False),
        sa.Column("ats_score", sa.Integer, nullable=False),
        sa.Column("keyword_match", sa.Float, server_default="0.0"),
        sa.Column("skills_match", sa.Float, server_default="0.0"),
        sa.Column("missing_keywords", sa.Text, server_default="[]"),
        sa.Column("suggestions", sa.Text, server_default="[]"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "optimizations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("resume_id", sa.Integer, sa.ForeignKey("resumes.id"), nullable=False),
        sa.Column("job_id", sa.Integer, sa.ForeignKey("job_descriptions.id"), nullable=False),
        sa.Column("model", sa.String(100), server_default=""),
        sa.Column("optimized_json", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("optimizations")
    op.drop_table("analyses")
    op.drop_table("job_descriptions")
    op.drop_table("resumes")
