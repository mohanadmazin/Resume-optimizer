"""Repository for agent conversations and messages."""
import json
import logging

from app.database.models import AgentConversation, AgentMessage
from app.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AgentRepository(BaseRepository):
    """CRUD for agent conversations and messages."""

    def create_conversation(
        self,
        resume_id: int | None = None,
        job_id: int | None = None,
        title: str = "",
    ) -> int:
        row = AgentConversation(
            resume_id=resume_id,
            job_id=job_id,
            title=title,
        )
        self.add(row)
        self.flush()
        logger.info("Created agent conversation %d", row.id)
        return row.id

    def get_conversation(self, conversation_id: int) -> AgentConversation | None:
        return (
            self.session.query(AgentConversation)
            .filter(AgentConversation.id == conversation_id)
            .first()
        )

    def list_conversations(
        self,
        resume_id: int | None = None,
    ) -> list[AgentConversation]:
        q = self.session.query(AgentConversation)
        if resume_id is not None:
            q = q.filter(AgentConversation.resume_id == resume_id)
        return q.order_by(AgentConversation.created_at.desc()).all()

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model: str = "",
        tokens_used: int = 0,
    ) -> int:
        row = AgentMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            tokens_used=tokens_used,
        )
        self.add(row)
        self.flush()
        return row.id

    def get_messages(self, conversation_id: int) -> list[AgentMessage]:
        return (
            self.session.query(AgentMessage)
            .filter(AgentMessage.conversation_id == conversation_id)
            .order_by(AgentMessage.id.asc())
            .all()
        )

    def add_proposal_message(
        self,
        conversation_id: int,
        tool: str,
        summary: str,
        actions: list[dict],
        model: str = "",
    ) -> int:
        content = json.dumps(
            {"tool": tool, "summary": summary, "actions": actions},
            ensure_ascii=False,
        )
        return self.add_message(
            conversation_id,
            role="assistant",
            content=content,
            model=model,
        )
