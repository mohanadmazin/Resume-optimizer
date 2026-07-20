"""Tests for agent domain, repository, service, and UI."""
from __future__ import annotations

import json
import sys
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.database.models import AgentConversation, AgentMessage, Resume
from app.domain.agent import AgentAction, AgentProposal, AgentTool
from app.domain.fact_guard import ChangeType
from app.domain.resume import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    ResumeData,
)

# Ensure QApplication exists for widget tests
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_resume() -> ResumeData:
    return ResumeData(
        contact=ContactInfo(name="Alice", email="alice@test.com"),
        headline="Senior Engineer",
        summary="Senior engineer with 5 years experience.",
        skills=["python", "sql", "docker"],
        experience=[
            ExperienceItem(
                title="Engineer",
                company="Acme",
                start_date="2020",
                end_date="2024",
                bullets=["Built things", "Led a team of 3"],
            )
        ],
        education=[
            EducationItem(degree="BS CS", institution="MIT", year="2019"),
        ],
        certifications=["AWS Solutions Architect"],
    )


def _test_engine(db_path):
    from sqlalchemy import event as sa_event, create_engine as _create_engine
    eng = _create_engine(f"sqlite:///{db_path}", echo=False)

    @sa_event.listens_for(eng, "connect")
    def _pragmas(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    return eng


# ── Domain tests ────────────────────────────────────────────────────────────


class TestAgentTool:
    def test_all_seven_tools_exist(self):
        tools = list(AgentTool)
        assert len(tools) == 7

    def test_tool_values_are_strings(self):
        for tool in AgentTool:
            assert isinstance(tool.value, str)

    def test_tool_enum_is_str_subclass(self):
        assert issubclass(AgentTool, str)

    def test_tool_from_value(self):
        assert AgentTool("score") is AgentTool.SCORE
        assert AgentTool("suggest_bullets") is AgentTool.SUGGEST_BULLETS

    def test_tool_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AgentTool("nonexistent")


class TestAgentAction:
    def test_defaults(self):
        action = AgentAction(tool=AgentTool.SCORE)
        assert action.tool == AgentTool.SCORE
        assert action.description == ""
        assert action.section == ""
        assert action.original == ""
        assert action.proposed == ""
        assert action.experience_index is None
        assert action.bullet_index is None
        assert action.accepted is None

    def test_full_construction(self):
        action = AgentAction(
            tool=AgentTool.SUGGEST_BULLETS,
            description="Rewrite bullet",
            section="experience",
            original="Built things",
            proposed="Architected microservices",
            experience_index=0,
            bullet_index=1,
            accepted=True,
        )
        assert action.tool == AgentTool.SUGGEST_BULLETS
        assert action.experience_index == 0
        assert action.bullet_index == 1
        assert action.accepted is True

    def test_serialization_roundtrip(self):
        action = AgentAction(
            tool=AgentTool.REWRITE_SUMMARY,
            description="Test",
            original="old",
            proposed="new",
        )
        data = action.model_dump()
        restored = AgentAction.model_validate(data)
        assert restored == action


class TestAgentProposal:
    def test_empty_proposal(self):
        proposal = AgentProposal(tool=AgentTool.SCORE)
        assert proposal.has_actions is False
        assert proposal.all_reviewed is True  # vacuously true

    def test_has_actions(self):
        proposal = AgentProposal(
            tool=AgentTool.TARGET,
            actions=[AgentAction(tool=AgentTool.TARGET, description="Add skill")],
        )
        assert proposal.has_actions is True

    def test_all_reviewed_when_mixed(self):
        proposal = AgentProposal(
            tool=AgentTool.OPTIMIZE,
            actions=[
                AgentAction(tool=AgentTool.OPTIMIZE, accepted=True),
                AgentAction(tool=AgentTool.OPTIMIZE, accepted=None),
            ],
        )
        assert proposal.all_reviewed is False

    def test_all_reviewed_when_all_decided(self):
        proposal = AgentProposal(
            tool=AgentTool.OPTIMIZE,
            actions=[
                AgentAction(tool=AgentTool.OPTIMIZE, accepted=True),
                AgentAction(tool=AgentTool.OPTIMIZE, accepted=False),
            ],
        )
        assert proposal.all_reviewed is True


# ── Repository tests ────────────────────────────────────────────────────────


class TestAgentRepository:
    def test_create_conversation(self, tmp_path, monkeypatch):
        db = tmp_path / "test.db"
        monkeypatch.setattr("app.database.migrate.DB_PATH", db)
        from app.database.migrate import run_migrations
        run_migrations()

        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.agent_repository import AgentRepository
            repo = AgentRepository(session)
            conv_id = repo.create_conversation(resume_id=None, job_id=None, title="Test")
            assert conv_id > 0

            conv = repo.get_conversation(conv_id)
            assert conv is not None
            assert conv.title == "Test"
            assert conv.resume_id is None

    def test_list_conversations_filters_by_resume(self, tmp_path, monkeypatch):
        db = tmp_path / "test.db"
        monkeypatch.setattr("app.database.migrate.DB_PATH", db)
        from app.database.migrate import run_migrations
        run_migrations()

        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.agent_repository import AgentRepository
            repo = AgentRepository(session)

            resume = Resume(name="R", data_json="{}")
            session.add(resume)
            session.flush()

            repo.create_conversation(resume_id=resume.id, title="For resume")
            repo.create_conversation(resume_id=None, title="General")
            session.commit()

            filtered = repo.list_conversations(resume_id=resume.id)
            assert len(filtered) == 1
            assert filtered[0].title == "For resume"

    def test_add_message(self, tmp_path, monkeypatch):
        db = tmp_path / "test.db"
        monkeypatch.setattr("app.database.migrate.DB_PATH", db)
        from app.database.migrate import run_migrations
        run_migrations()

        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.agent_repository import AgentRepository
            repo = AgentRepository(session)

            conv_id = repo.create_conversation(title="Chat")
            msg_id = repo.add_message(conv_id, role="user", content="Hello")
            assert msg_id > 0

            msgs = repo.get_messages(conv_id)
            assert len(msgs) == 1
            assert msgs[0].role == "user"
            assert msgs[0].content == "Hello"

    def test_add_proposal_message(self, tmp_path, monkeypatch):
        db = tmp_path / "test.db"
        monkeypatch.setattr("app.database.migrate.DB_PATH", db)
        from app.database.migrate import run_migrations
        run_migrations()

        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.agent_repository import AgentRepository
            repo = AgentRepository(session)

            conv_id = repo.create_conversation(title="Chat")
            actions = [{"tool": "score", "description": "Test action"}]
            msg_id = repo.add_proposal_message(
                conv_id, tool="score", summary="Scored", actions=actions, model="test"
            )
            assert msg_id > 0

            msgs = repo.get_messages(conv_id)
            assert len(msgs) == 1
            content = json.loads(msgs[0].content)
            assert content["tool"] == "score"
            assert content["summary"] == "Scored"
            assert len(content["actions"]) == 1

    def test_conversation_cascade_delete(self, tmp_path, monkeypatch):
        db = tmp_path / "test.db"
        monkeypatch.setattr("app.database.migrate.DB_PATH", db)
        from app.database.migrate import run_migrations
        run_migrations()

        eng = _test_engine(db)
        with Session(eng) as session:
            from app.database.repositories.agent_repository import AgentRepository
            repo = AgentRepository(session)

            conv_id = repo.create_conversation(title="Chat")
            repo.add_message(conv_id, role="user", content="Hello")
            session.commit()

        with Session(eng) as session:
            conv = session.query(AgentConversation).one()
            session.delete(conv)
            session.commit()

        with Session(eng) as session:
            assert session.query(AgentMessage).count() == 0


# ── Service tests ───────────────────────────────────────────────────────────


class TestAgentService:
    def test_resume_to_text(self):
        from app.services.agent import _resume_to_text
        resume = _make_resume()
        text = _resume_to_text(resume)

        assert "Alice" in text
        assert "alice@test.com" in text
        assert "Senior Engineer" in text
        assert "python" in text
        assert "Engineer" in text
        assert "Acme" in text
        assert "Built things" in text
        assert "MIT" in text
        assert "AWS Solutions Architect" in text

    def test_resume_to_text_minimal(self):
        from app.services.agent import _resume_to_text
        resume = ResumeData()
        text = _resume_to_text(resume)
        assert isinstance(text, str)

    def test_parse_agent_actions(self):
        from app.services.agent import _parse_agent_actions
        raw = {
            "summary": "Found 2 issues",
            "actions": [
                {
                    "tool": "score",
                    "description": "Improve headline",
                    "section": "contact",
                    "original": "Engineer",
                    "proposed": "Senior Software Engineer",
                    "experience_index": None,
                    "bullet_index": None,
                }
            ],
        }
        proposal = _parse_agent_actions(raw, AgentTool.SCORE)
        assert proposal.tool == AgentTool.SCORE
        assert proposal.summary == "Found 2 issues"
        assert len(proposal.actions) == 1
        assert proposal.actions[0].tool == AgentTool.SCORE
        assert proposal.actions[0].proposed == "Senior Software Engineer"

    def test_parse_agent_actions_empty(self):
        from app.services.agent import _parse_agent_actions
        proposal = _parse_agent_actions({}, AgentTool.TARGET)
        assert len(proposal.actions) == 0

    def test_build_proposed_change(self):
        from app.services.agent import _build_proposed_change
        action = AgentAction(
            tool=AgentTool.SUGGEST_BULLETS,
            section="experience[0].bullets[1]",
            original="Built things",
            proposed="Architected microservices reducing latency by 40%",
            experience_index=0,
            bullet_index=1,
        )
        change = _build_proposed_change(action)
        assert change.change_type == ChangeType.BULLET
        assert change.original == "Built things"
        assert change.experience_index == 0
        assert change.bullet_index == 1

    def test_build_proposed_change_summary(self):
        from app.services.agent import _build_proposed_change
        action = AgentAction(
            tool=AgentTool.REWRITE_SUMMARY,
            original="Old summary",
            proposed="New summary with keywords",
        )
        change = _build_proposed_change(action)
        assert change.change_type == ChangeType.SUMMARY

    @patch("app.services.agent.OllamaClient")
    def test_propose_calls_client(self, MockClient):
        from app.services.agent import AgentService
        mock_client = MockClient.return_value
        mock_client.generate.return_value = json.dumps({
            "summary": "Test",
            "actions": [],
        })

        svc = AgentService(client=mock_client)
        resume = _make_resume()
        proposal = svc.propose(resume, "Software Engineer", AgentTool.SCORE)

        mock_client.generate.assert_called_once()
        assert proposal.tool == AgentTool.SCORE
        assert proposal.summary == "Test"

    @patch("app.services.agent.OllamaClient")
    def test_propose_with_actions(self, MockClient):
        from app.services.agent import AgentService
        mock_client = MockClient.return_value
        mock_client.generate.return_value = json.dumps({
            "summary": "Found issues",
            "actions": [
                {
                    "tool": "optimize",
                    "description": "Rewrite headline",
                    "section": "contact",
                    "original": "Engineer",
                    "proposed": "Senior Software Engineer",
                }
            ],
        })

        svc = AgentService(client=mock_client)
        resume = _make_resume()
        proposal = svc.propose(resume, "Software Engineer", AgentTool.OPTIMIZE)

        assert len(proposal.actions) == 1
        assert proposal.actions[0].accepted is not None  # fact guard ran

    @patch("app.services.agent.OllamaClient")
    def test_propose_invalid_json_returns_text(self, MockClient):
        from app.services.agent import AgentService
        mock_client = MockClient.return_value
        mock_client.generate.return_value = "This is not JSON"

        svc = AgentService(client=mock_client)
        resume = _make_resume()
        proposal = svc.propose(resume, "JD", AgentTool.SCORE)

        assert len(proposal.actions) == 0
        assert "This is not JSON" in proposal.summary

    @patch("app.services.agent.OllamaClient")
    def test_propose_check_facts_uses_extra_context(self, MockClient):
        from app.services.agent import AgentService
        mock_client = MockClient.return_value
        mock_client.generate.return_value = json.dumps({
            "summary": "Checked",
            "actions": [],
        })

        svc = AgentService(client=mock_client)
        resume = _make_resume()
        svc.propose(
            resume, "JD", AgentTool.CHECK_FACTS,
            extra_context="Proposed changes text here",
        )

        call_args = mock_client.generate.call_args
        prompt = call_args.kwargs.get("prompt", call_args[0][0] if call_args[0] else "")
        assert "Proposed changes text here" in prompt

    def test_create_conversation_title(self):
        from app.services.agent import AgentService
        svc = AgentService.__new__(AgentService)
        title = svc.create_conversation_title(AgentTool.SCORE, "Software Engineer at Google")
        assert "Score" in title
        assert "Software Engineer at Google" in title

    def test_create_conversation_title_short_jd(self):
        from app.services.agent import AgentService
        svc = AgentService.__new__(AgentService)
        title = svc.create_conversation_title(AgentTool.OPTIMIZE, "")
        assert "Optimize" in title


# ── UI tests ────────────────────────────────────────────────────────────────


class TestAgentProposalCard:
    def test_card_creation(self):
        from app.ui.components.agent_proposal_card import AgentProposalCard
        action = AgentAction(
            tool=AgentTool.SUGGEST_BULLETS,
            description="Rewrite bullet",
            section="experience",
            original="Built things",
            proposed="Architected microservices",
        )
        card = AgentProposalCard(action, index=0)
        assert card._action == action
        assert card._index == 0

    def test_card_accept_reject_signals(self):
        from app.ui.components.agent_proposal_card import AgentProposalCard
        action = AgentAction(tool=AgentTool.SCORE, description="Test")
        card = AgentProposalCard(action, index=2)

        accepted_results = []
        rejected_results = []
        card.accepted.connect(lambda i: accepted_results.append(i))
        card.rejected.connect(lambda i: rejected_results.append(i))

        card._accept_btn.click()
        assert accepted_results == [2]

        card._reject_btn.click()
        assert rejected_results == [2]

    def test_set_decided(self):
        from app.ui.components.agent_proposal_card import AgentProposalCard
        action = AgentAction(tool=AgentTool.SCORE, description="Test")
        card = AgentProposalCard(action, index=0)

        card.set_decided(True)
        assert not card._accept_btn.isEnabled()
        assert card._reject_btn.isHidden()

        card2 = AgentProposalCard(action, index=1)
        card2.set_decided(False)
        assert not card2._reject_btn.isEnabled()
        assert card2._accept_btn.isHidden()


class TestChatBubble:
    def test_bubble_creation(self):
        from app.ui.pages.agent import _ChatBubble
        bubble = _ChatBubble("agent", "Hello world")
        assert bubble is not None

    def test_bubble_user_role(self):
        from app.ui.pages.agent import _ChatBubble
        bubble = _ChatBubble("you", "Test message")
        assert bubble is not None
