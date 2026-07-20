"""add career evidence vault tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return bind.dialect.has_table(bind, name)


def upgrade() -> None:
    if not _table_exists("career_facts"):
        op.create_table(
            "career_facts",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("statement", sa.Text, nullable=False),
            sa.Column("fact_type", sa.String(50), nullable=False, server_default="other"),
            sa.Column(
                "confidence",
                sa.String(50),
                nullable=False,
                server_default="user_estimate",
            ),
            sa.Column("employer", sa.String(255), server_default=""),
            sa.Column("project", sa.String(255), server_default=""),
            sa.Column("date_from", sa.String(20), server_default=""),
            sa.Column("date_to", sa.String(20), server_default=""),
            sa.Column("sensitive", sa.Boolean, server_default=sa.text("0")),
            sa.Column("metrics_json", sa.Text, server_default="{}"),
            sa.Column("tags_json", sa.Text, server_default="[]"),
            sa.Column("notes", sa.Text, server_default=""),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column(
                "updated_at",
                sa.DateTime,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_career_facts_fact_type", "career_facts", ["fact_type"])
        op.create_index("ix_career_facts_confidence", "career_facts", ["confidence"])
        op.create_index("ix_career_facts_employer", "career_facts", ["employer"])

    if not _table_exists("evidence_sources"):
        op.create_table(
            "evidence_sources",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "source_type",
                sa.String(50),
                nullable=False,
                server_default="document",
            ),
            sa.Column("name", sa.String(500), nullable=False),
            sa.Column("file_path", sa.Text, server_default=""),
            sa.Column("excerpt", sa.Text, server_default=""),
            sa.Column("page_reference", sa.String(100), server_default=""),
            sa.Column("notes", sa.Text, server_default=""),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index("ix_evidence_sources_source_type", "evidence_sources", ["source_type"])

    if not _table_exists("career_fact_sources"):
        op.create_table(
            "career_fact_sources",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "fact_id",
                sa.Integer,
                sa.ForeignKey("career_facts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "source_id",
                sa.Integer,
                sa.ForeignKey("evidence_sources.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.UniqueConstraint("fact_id", "source_id", name="uq_fact_source"),
        )
        op.create_index("ix_career_fact_sources_fact_id", "career_fact_sources", ["fact_id"])
        op.create_index(
            "ix_career_fact_sources_source_id",
            "career_fact_sources",
            ["source_id"],
        )

    if not _table_exists("content_fact_links"):
        op.create_table(
            "content_fact_links",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("content_type", sa.String(50), nullable=False),
            sa.Column("content_id", sa.Integer, nullable=False),
            sa.Column(
                "fact_id",
                sa.Integer,
                sa.ForeignKey("career_facts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("relevance", sa.String(50), server_default="direct"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "content_type",
                "content_id",
                "fact_id",
                name="uq_content_fact",
            ),
        )
        op.create_index("ix_content_fact_links_content_type", "content_fact_links", ["content_type"])
        op.create_index("ix_content_fact_links_content_id", "content_fact_links", ["content_id"])
        op.create_index("ix_content_fact_links_fact_id", "content_fact_links", ["fact_id"])

    if not _table_exists("fact_verification_events"):
        op.create_table(
            "fact_verification_events",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "fact_id",
                sa.Integer,
                sa.ForeignKey("career_facts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "previous_confidence",
                sa.String(50),
                server_default="unsupported",
            ),
            sa.Column(
                "new_confidence",
                sa.String(50),
                server_default="unsupported",
            ),
            sa.Column("reason", sa.Text, server_default=""),
            sa.Column("verified_by", sa.String(100), server_default="user"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index(
            "ix_fact_verification_events_fact_id",
            "fact_verification_events",
            ["fact_id"],
        )


def downgrade() -> None:
    op.drop_table("fact_verification_events")
    op.drop_table("content_fact_links")
    op.drop_table("career_fact_sources")
    op.drop_table("evidence_sources")
    op.drop_table("career_facts")
