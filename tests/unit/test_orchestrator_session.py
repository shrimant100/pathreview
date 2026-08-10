"""Tests for orchestrator session persistence (issue #43)."""

from typing import cast
from unittest.mock import Mock

import pytest
from redis import Redis

from agent.memory.session_store import SessionStore
from agent.orchestrator import Orchestrator
from agent.tools.base import ToolResult


class FakeRedis:
    """Minimal in-memory Redis stand-in for unit tests."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> bytes | None:
        value = self._data.get(key)
        return value.encode() if value is not None else None

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)


def _make_tool(name: str, payload: dict) -> Mock:
    tool = Mock()
    tool.name = name
    tool.execute = Mock(return_value=ToolResult(success=True, data=payload))
    return tool


@pytest.mark.unit
class TestOrchestratorSessionState:
    """Reproduce issue #43: stale session keys persist across reviews."""

    @pytest.fixture
    def session_store(self) -> SessionStore:
        return SessionStore(cast(Redis, FakeRedis()))

    @pytest.fixture
    def tools(self) -> dict:
        return {
            "readme_scorer": _make_tool("readme_scorer", {"score": 72, "version": "old"}),
            "skill_extractor": _make_tool(
                "skill_extractor", {"skills": ["Python"], "version": "new"}
            ),
            "market_analyzer": _make_tool("market_analyzer", {"demand": "high"}),
        }

    def test_session_does_not_retain_stale_tool_results_between_reviews(
        self, session_store: SessionStore, tools: dict
    ) -> None:
        """Second review for the same profile should not keep prior tool output."""
        profile_id = "profile-abc123"

        first_orchestrator = Orchestrator(tools=tools, session_store=session_store)
        first_orchestrator.run(
            profile_id,
            {"readme_content": "Original README before portfolio update."},
        )

        second_orchestrator = Orchestrator(tools=tools, session_store=session_store)
        second_orchestrator.run(
            profile_id,
            {"resume_text": "Updated resume after portfolio refresh."},
        )

        stored_session = session_store.get(profile_id)
        assert stored_session is not None

        # After a portfolio update, tools from the first review must not linger.
        assert "readme_scorer" not in stored_session
        assert "skill_extractor" in stored_session

    def test_first_review_persists_session_when_no_prior_state(
        self, session_store: SessionStore, tools: dict
    ) -> None:
        """First review for a profile should store tool results normally."""
        profile_id = "profile-new-user"

        orchestrator = Orchestrator(tools=tools, session_store=session_store)
        orchestrator.run(profile_id, {"readme_content": "First portfolio README."})

        stored_session = session_store.get(profile_id)
        assert stored_session is not None
        assert "readme_scorer" in stored_session
        assert "market_analyzer" in stored_session

    def test_empty_plan_clears_prior_session(
        self, session_store: SessionStore, tools: dict
    ) -> None:
        """A review with no tools should not retain keys from an earlier review."""
        profile_id = "profile-empty-plan"

        first_orchestrator = Orchestrator(tools=tools, session_store=session_store)
        first_orchestrator.run(profile_id, {"readme_content": "README from review #1."})

        second_orchestrator = Orchestrator(tools=tools, session_store=session_store)
        second_orchestrator.run(profile_id, {})

        stored_session = session_store.get(profile_id)
        assert stored_session == {}
