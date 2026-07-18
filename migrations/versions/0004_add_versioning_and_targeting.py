"""add versioning, targeting, suggestions, and supporting tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def upgrade() -> None:
    # ── resume_versions ──────────────────────────────────────────────
    if not _table_exists("resume_versions"):
        op.create_table(
            "resume_versions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "resume_id",
                sa.Integer,
                sa.ForeignKey("resumes.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("version_number", sa.Integer, nullable=False),
            sa.Column("data_json", sa.Text, nullable=False),
            sa.Column("change_summary", sa.String(500), server_default=""),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "resume_id",
                "version_number",
                name="uq_resume_version",
            ),
        )

    # ── targeting_sessions ───────────────────────────────────────────
    if not _table_exists("targeting_sessions"):
        op.create_table(
            "targeting_sessions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "resume_version_id",
                sa.Integer,
                sa.ForeignKey("resume_versions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "job_id",
                sa.Integer,
                sa.ForeignKey("job_descriptions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("requirements_json", sa.Text, nullable=False),
            sa.Column("score_report_json", sa.Text, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # ── suggestions ──────────────────────────────────────────────────
    if not _table_exists("suggestions"):
        op.create_table(
            "suggestions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "targeting_session_id",
                sa.Integer,
                sa.ForeignKey("targeting_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("document_path", sa.String(500), nullable=False),
            sa.Column("original_text", sa.Text, nullable=False),
            sa.Column("suggested_text", sa.Text, nullable=False),
            sa.Column("evidence_json", sa.Text, nullable=False),
            sa.Column(
                "status",
                sa.String(30),
                server_default="pending",
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # ── template_preferences ─────────────────────────────────────────
    if not _table_exists("template_preferences"):
        op.create_table(
            "template_preferences",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "resume_id",
                sa.Integer,
                sa.ForeignKey("resumes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("template_id", sa.String(100), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("resume_id", name="uq_template_preference"),
        )

    # ── cover_letters ────────────────────────────────────────────────
    if not _table_exists("cover_letters"):
        op.create_table(
            "cover_letters",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "resume_id",
                sa.Integer,
                sa.ForeignKey("resumes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "job_id",
                sa.Integer,
                sa.ForeignKey("job_descriptions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("model", sa.String(100), server_default=""),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # ── agent_conversations ──────────────────────────────────────────
    if not _table_exists("agent_conversations"):
        op.create_table(
            "agent_conversations",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "resume_id",
                sa.Integer,
                sa.ForeignKey("resumes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "job_id",
                sa.Integer,
                sa.ForeignKey("job_descriptions.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("title", sa.String(255), server_default=""),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # ── agent_messages ───────────────────────────────────────────────
    if not _table_exists("agent_messages"):
        op.create_table(
            "agent_messages",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "conversation_id",
                sa.Integer,
                sa.ForeignKey("agent_conversations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(30), nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("model", sa.String(100), server_default=""),
            sa.Column("tokens_used", sa.Integer, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # ── job_applications ─────────────────────────────────────────────
    if not _table_exists("job_applications"):
        op.create_table(
            "job_applications",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "resume_id",
                sa.Integer,
                sa.ForeignKey("resumes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "job_id",
                sa.Integer,
                sa.ForeignKey("job_descriptions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "status",
                sa.String(50),
                server_default="draft",
                nullable=False,
            ),
            sa.Column("notes", sa.Text, server_default=""),
            sa.Column("applied_at", sa.DateTime, nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # ── interview_sessions ───────────────────────────────────────────
    if not _table_exists("interview_sessions"):
        op.create_table(
            "interview_sessions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "resume_id",
                sa.Integer,
                sa.ForeignKey("resumes.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "job_id",
                sa.Integer,
                sa.ForeignKey("job_descriptions.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("company", sa.String(255), server_default=""),
            sa.Column("role", sa.String(255), server_default=""),
            sa.Column("notes", sa.Text, server_default=""),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # ── score_snapshots ──────────────────────────────────────────────
    if not _table_exists("score_snapshots"):
        op.create_table(
            "score_snapshots",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "resume_id",
                sa.Integer,
                sa.ForeignKey("resumes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "job_id",
                sa.Integer,
                sa.ForeignKey("job_descriptions.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("ats_score", sa.Integer, nullable=False),
            sa.Column("keyword_match", sa.Float, server_default="0.0"),
            sa.Column("skills_match", sa.Float, server_default="0.0"),
            sa.Column("score_report_json", sa.Text, server_default="{}"),
            sa.Column(
                "created_at",
                sa.DateTime,
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    tables_in_drop_order = [
        "score_snapshots",
        "interview_sessions",
        "job_applications",
        "agent_messages",
        "agent_conversations",
        "cover_letters",
        "template_preferences",
        "suggestions",
        "targeting_sessions",
        "resume_versions",
    ]
    for table in tables_in_drop_order:
        if _table_exists(table):
            op.drop_table(table)
