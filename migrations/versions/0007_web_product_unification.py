"""unify web workflow and persist generated documents

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {item["name"] for item in inspect(bind).get_columns(table)}


def upgrade() -> None:
    # Rich job metadata used by cover letters, dashboard and application tracking.
    for name, column in (
        ("company", sa.Column("company", sa.String(255), server_default="")),
        ("location", sa.Column("location", sa.String(255), server_default="")),
        ("source_url", sa.Column("source_url", sa.Text, server_default="")),
        ("employment_type", sa.Column("employment_type", sa.String(100), server_default="")),
        ("salary", sa.Column("salary", sa.String(150), server_default="")),
        ("date_posted", sa.Column("date_posted", sa.String(40), server_default="")),
        ("status", sa.Column("status", sa.String(50), server_default="saved")),
        ("updated_at", sa.Column("updated_at", sa.DateTime, server_default=sa.func.now())),
    ):
        if not _column_exists("job_descriptions", name):
            op.add_column("job_descriptions", column)

    # Preserve complete ATS output, optimization review choices and editable drafts.
    if not _column_exists("analyses", "result_json"):
        op.add_column("analyses", sa.Column("result_json", sa.Text, server_default="{}"))
    if not _column_exists("optimizations", "fact_guard_json"):
        op.add_column("optimizations", sa.Column("fact_guard_json", sa.Text, server_default="{}"))
    if not _column_exists("optimizations", "accepted_changes_json"):
        op.add_column("optimizations", sa.Column("accepted_changes_json", sa.Text, server_default="[]"))
    if not _column_exists("optimizations", "original_score"):
        op.add_column("optimizations", sa.Column("original_score", sa.Integer, server_default="0"))
    if not _column_exists("optimizations", "optimized_score"):
        op.add_column("optimizations", sa.Column("optimized_score", sa.Integer, server_default="0"))
    if not _column_exists("cover_letters", "updated_at"):
        op.add_column("cover_letters", sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()))

    if not _table_exists("web_sessions"):
        op.create_table(
            "web_sessions",
            sa.Column("sid", sa.String(64), primary_key=True),
            sa.Column("data_json", sa.Text, nullable=False, server_default="{}"),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_web_sessions_updated_at", "web_sessions", ["updated_at"])

    if not _table_exists("generated_documents"):
        op.create_table(
            "generated_documents",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("document_type", sa.String(50), nullable=False),
            sa.Column("title", sa.String(255), nullable=False, server_default="Untitled document"),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("resume_id", sa.Integer, sa.ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("job_id", sa.Integer, sa.ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_generated_documents_type", "generated_documents", ["document_type"])
        op.create_index("ix_generated_documents_resume", "generated_documents", ["resume_id"])
        op.create_index("ix_generated_documents_job", "generated_documents", ["job_id"])


def downgrade() -> None:
    if _table_exists("generated_documents"):
        op.drop_table("generated_documents")
    if _table_exists("web_sessions"):
        op.drop_table("web_sessions")
    # SQLite column downgrades are intentionally omitted; keeping optional columns
    # is safer for user data than rebuilding populated tables.
