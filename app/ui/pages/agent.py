"""Agent page — chat-style interface for AI resume agent with conversation history."""
from __future__ import annotations

import json
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.database import db
from app.database.repositories.agent_repository import AgentRepository
from app.domain.agent import AgentAction, AgentProposal, AgentTool
from app.services.agent import AgentService
from app.ui.components.agent_proposal_card import AgentProposalCard
from app.ui.components.loading_overlay import LoadingOverlayManager
from app.ui.workers import Worker

logger = logging.getLogger(__name__)

_TOOL_LABELS: dict[AgentTool, str] = {
    AgentTool.SCORE: "Score Resume",
    AgentTool.TARGET: "Target Keywords",
    AgentTool.SUGGEST_BULLETS: "Suggest Bullets",
    AgentTool.REWRITE_SUMMARY: "Rewrite Summary",
    AgentTool.EXPLAIN_ISSUES: "Explain Issues",
    AgentTool.OPTIMIZE: "Full Optimization",
    AgentTool.CHECK_FACTS: "Check Facts",
}


class _ChatBubble(QFrame):
    """A single chat message bubble."""

    def __init__(self, role: str, text: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        role_label = QLabel(role.upper())
        color = "#2563EB" if role == "assistant" else "#6B7280"
        role_label.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(role_label)

        content = QLabel(text)
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.PlainText)
        content.setStyleSheet("font-size: 13px;")
        layout.addWidget(content)


class AgentPage(QWidget):
    """Chat-style agent page with tool selector, message history, and proposal cards."""

    proposal_applied = Signal(object)  # emits AgentAction when accepted

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self._worker: Worker | None = None
        self._overlay = LoadingOverlayManager()
        self._conversation_id: int | None = None
        self._current_proposal: AgentProposal | None = None
        self._proposal_cards: list[AgentProposalCard] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Resume Agent")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        desc = QLabel(
            "Ask the agent to score, target, rewrite, or optimize your resume. "
            "Select a tool and click Run, or type a custom message."
        )
        layout.addWidget(desc)

        toolbar = QHBoxLayout()

        self._tool_combo = QComboBox()
        for tool in AgentTool:
            self._tool_combo.addItem(_TOOL_LABELS[tool], tool.value)
        toolbar.addWidget(self._tool_combo)

        self._run_btn = QPushButton("Run")
        self._run_btn.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 6px 20px; "
            "border-radius: 4px; font-weight: bold;"
        )
        self._run_btn.clicked.connect(self._on_run)
        toolbar.addWidget(self._run_btn)

        self._new_chat_btn = QPushButton("New Conversation")
        self._new_chat_btn.clicked.connect(self._on_new_chat)
        toolbar.addWidget(self._new_chat_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._chat_widget = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_widget)
        self._chat_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_layout.setSpacing(8)
        self._chat_layout.addStretch()

        scroll.setWidget(self._chat_widget)
        self._scroll = scroll
        layout.addWidget(scroll, stretch=1)

        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a message or select a tool and click Run...")
        self._input.returnPressed.connect(self._on_send)
        input_row.addWidget(self._input)

        self._send_btn = QPushButton("Send")
        self._send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self._send_btn)

        layout.addLayout(input_row)

    def on_show(self) -> None:
        if self._conversation_id is None:
            self._load_latest_conversation()

    def _load_latest_conversation(self) -> None:
        """Load the most recent conversation for the active resume."""
        resume_id = self.window.state.resume_id
        if resume_id is None:
            return
        try:
            with db.session_scope() as session:
                repo = AgentRepository(session)
                convs = repo.list_conversations(resume_id=resume_id)
                if not convs:
                    return
                conv = convs[0]
                self._conversation_id = conv.id
                messages = repo.get_messages(conv.id)
                for msg in messages:
                    if msg.role == "user":
                        self._add_user_message(msg.content)
                    elif msg.role == "assistant":
                        try:
                            data = json.loads(msg.content)
                            if "actions" in data:
                                actions = [AgentAction.model_validate(a) for a in data["actions"]]
                                proposal = AgentProposal(
                                    tool=AgentTool(data.get("tool", "optimize")),
                                    summary=data.get("summary", ""),
                                    actions=actions,
                                )
                                self._render_proposal(proposal)
                            else:
                                self._add_assistant_message(data.get("summary", msg.content[:500]))
                        except (json.JSONDecodeError, Exception):
                            self._add_assistant_message(msg.content[:500])
        except Exception:
            logger.exception("Failed to load conversation history")

    def _on_new_chat(self) -> None:
        self._conversation_id = None
        self._current_proposal = None
        self._proposal_cards.clear()
        self._clear_chat()
        self._add_assistant_message(
            "New conversation started. Select a tool and click Run, or type a message."
        )

    def _on_run(self) -> None:
        tool_value = self._tool_combo.currentData()
        tool = AgentTool(tool_value)

        resume = self.window.state.resume
        jd_text = self.window.state.job_text

        if resume is None:
            QMessageBox.warning(self, "No Resume", "Please upload a resume first.")
            return

        self._add_user_message(f"Run: {_TOOL_LABELS[tool]}")
        self._save_user_message_to_db(f"Run: {_TOOL_LABELS[tool]}")
        self._run_tool(tool, resume, jd_text)

    def _on_send(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()

        resume = self.window.state.resume
        jd_text = self.window.state.job_text

        if resume is None:
            QMessageBox.warning(self, "No Resume", "Please upload a resume first.")
            return

        self._add_user_message(text)
        self._save_user_message_to_db(text)

        tool = AgentTool.OPTIMIZE
        self._run_tool(tool, resume, jd_text, extra_context=text)

    def _run_tool(
        self,
        tool: AgentTool,
        resume,
        jd_text: str,
        extra_context: str = "",
    ) -> None:
        self._run_btn.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._overlay.show(self)

        def _do_propose():
            svc = AgentService()
            return svc.propose(resume, jd_text, tool, extra_context=extra_context)

        self._worker = Worker(_do_propose, timeout_seconds=300)
        self._worker.result.connect(self._on_proposal)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _on_proposal(self, proposal: AgentProposal) -> None:
        self._overlay.hide()
        self._run_btn.setEnabled(True)
        self._send_btn.setEnabled(True)

        self._current_proposal = proposal
        self._proposal_cards.clear()

        self._render_proposal(proposal)
        self._save_proposal_to_db(proposal)

    def _render_proposal(self, proposal: AgentProposal) -> None:
        """Render a proposal into the chat area."""
        if not proposal.actions:
            self._add_assistant_message(proposal.summary or "No actions proposed.")
            return

        summary_text = f"{proposal.summary}\n\n{len(proposal.actions)} action(s) proposed:"
        self._add_assistant_message(summary_text)

        for i, action in enumerate(proposal.actions):
            card = AgentProposalCard(action, i)
            card.accepted.connect(self._on_action_accepted)
            card.rejected.connect(self._on_action_rejected)
            self._proposal_cards.append(card)
            self._chat_layout.insertWidget(self._chat_layout.count() - 1, card)

    def _on_action_accepted(self, index: int) -> None:
        if self._current_proposal and index < len(self._current_proposal.actions):
            self._current_proposal.actions[index].accepted = True
            self._proposal_cards[index].set_decided(True)
            self.proposal_applied.emit(self._current_proposal.actions[index])

    def _on_action_rejected(self, index: int) -> None:
        if self._current_proposal and index < len(self._current_proposal.actions):
            self._current_proposal.actions[index].accepted = False
            self._proposal_cards[index].set_decided(False)

    def _on_error(self, msg: str) -> None:
        self._overlay.hide()
        self._run_btn.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._add_assistant_message(f"Error: {msg}")

    def _on_cancelled(self) -> None:
        self._overlay.hide()
        self._run_btn.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._add_assistant_message("Operation cancelled.")

    def _add_user_message(self, text: str) -> None:
        bubble = _ChatBubble("you", text)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)

    def _add_assistant_message(self, text: str) -> None:
        bubble = _ChatBubble("agent", text)
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, bubble)

    def _clear_chat(self) -> None:
        while self._chat_layout.count():
            child = self._chat_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._chat_layout.addStretch()

    def _ensure_conversation(self) -> int:
        """Create a conversation if one doesn't exist yet."""
        if self._conversation_id is not None:
            return self._conversation_id
        resume_id = self.window.state.resume_id
        job_id = self.window.state.job_id
        try:
            with db.session_scope() as session:
                repo = AgentRepository(session)
                self._conversation_id = repo.create_conversation(
                    resume_id=resume_id,
                    job_id=job_id,
                )
            return self._conversation_id
        except Exception:
            logger.exception("Failed to create conversation")
            return 0

    def _save_user_message_to_db(self, text: str) -> None:
        try:
            conv_id = self._ensure_conversation()
            if conv_id:
                with db.session_scope() as session:
                    repo = AgentRepository(session)
                    repo.add_message(conv_id, role="user", content=text)
        except Exception:
            logger.exception("Failed to save user message")

    def _save_proposal_to_db(self, proposal: AgentProposal) -> None:
        try:
            conv_id = self._ensure_conversation()
            if conv_id:
                actions_data = [
                    a.model_dump(mode="json") for a in proposal.actions
                ]
                with db.session_scope() as session:
                    repo = AgentRepository(session)
                    repo.add_proposal_message(
                        conv_id,
                        tool=proposal.tool.value,
                        summary=proposal.summary,
                        actions=actions_data,
                    )
        except Exception:
            logger.exception("Failed to save agent proposal to DB")
