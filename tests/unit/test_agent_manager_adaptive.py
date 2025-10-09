"""Test AgentManager intelligent fallback integration."""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from stomper.ai.agent_manager import AgentManager
from stomper.ai.base import AgentCapabilities, AgentInfo, AIAgent
from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import FixOutcome, PromptStrategy
from stomper.quality.base import QualityError


def create_sample_error(
    tool: str = "ruff",
    code: str = "E501",
    file: str = "test.py",
    line: int = 10,
    column: int = 80,
    message: str = "Line too long",
) -> QualityError:
    """Create a sample QualityError for testing."""
    return QualityError(
        tool=tool,
        file=Path(file),
        line=line,
        column=column,
        code=code,
        message=message,
        severity="error",
        auto_fixable=True,
    )


def create_mock_agent(name: str = "test-agent") -> Mock:
    """Create a properly mocked AIAgent for testing."""
    mock_agent = Mock(spec=AIAgent)
    mock_agent.get_agent_info.return_value = AgentInfo(
        name=name,
        version="1.0.0",
        description="Test agent",
        capabilities=AgentCapabilities(
            can_fix_linting=True,
            can_fix_types=True,
            can_fix_tests=False,
            max_context_length=4000,
            supported_languages=["python"],
        ),
    )
    return mock_agent


@pytest.mark.unit
class TestAgentManagerAdaptive:
    """Test AgentManager intelligent fallback integration."""

    def test_accepts_project_root_parameter(self, tmp_path):
        """Test AgentManager accepts project_root parameter."""
        manager = AgentManager(project_root=tmp_path)

        assert manager.mapper is not None
        assert manager.mapper.project_root == tmp_path.resolve()

    def test_accepts_mapper_parameter(self, tmp_path):
        """Test AgentManager accepts mapper parameter."""
        mapper = ErrorMapper(project_root=tmp_path)
        manager = AgentManager(mapper=mapper)

        assert manager.mapper is mapper

    def test_works_without_mapper_backwards_compatibility(self):
        """Test AgentManager still works without mapper (backwards compatibility)."""
        # Old code that doesn't pass mapper should still work
        manager = AgentManager()

        assert manager.mapper is None

    def test_generate_fix_with_intelligent_fallback_exists(self, tmp_path):
        """Test generate_fix_with_intelligent_fallback method exists."""
        manager = AgentManager(project_root=tmp_path)

        assert hasattr(manager, "generate_fix_with_intelligent_fallback")
        assert callable(manager.generate_fix_with_intelligent_fallback)

    def test_intelligent_fallback_uses_mapper(self, tmp_path):
        """Test intelligent fallback uses mapper for strategy selection."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error(code="E501")

        # Record that DETAILED strategy worked before
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)

        # Create manager with mapper
        manager = AgentManager(mapper=mapper)

        # Register mock agent
        mock_agent = create_mock_agent()
        mock_agent.generate_fix = MagicMock(return_value="fixed code")
        manager.register_agent("test_agent", mock_agent)

        # Try to fix
        result = manager.generate_fix_with_intelligent_fallback(
            "test_agent",
            error,
            {"test": "context"},
            "code context",
            "fix prompt",
        )

        assert result == "fixed code"
        assert mock_agent.generate_fix.called

    def test_records_successful_outcome(self, tmp_path):
        """Test AgentManager records successful fix outcomes."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        manager = AgentManager(mapper=mapper)

        # Register mock agent
        mock_agent = create_mock_agent()
        mock_agent.generate_fix = MagicMock(return_value="fixed code")
        manager.register_agent("test_agent", mock_agent)

        # Initial state - no attempts
        assert mapper.data.total_attempts == 0

        # Attempt fix
        manager.generate_fix_with_intelligent_fallback(
            "test_agent",
            error,
            {},
            "",
            "",
        )

        # Check mapper recorded the outcome
        assert mapper.data.total_attempts == 1
        assert mapper.data.total_successes == 1

    def test_records_failed_outcome_and_retries(self, tmp_path):
        """Test AgentManager records failures and retries with different strategies."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        manager = AgentManager(mapper=mapper)

        # Register mock agent that fails first, then succeeds
        mock_agent = create_mock_agent()
        mock_agent.generate_fix = MagicMock(
            side_effect=[Exception("Failed"), "fixed code"]
        )
        manager.register_agent("test_agent", mock_agent)

        # Attempt fix (should retry after first failure)
        result = manager.generate_fix_with_intelligent_fallback(
            "test_agent",
            error,
            {},
            "",
            "",
            max_retries=3,
        )

        # Should eventually succeed
        assert result == "fixed code"

        # Should have recorded both failure and success
        assert mapper.data.total_attempts == 2
        assert mapper.data.total_successes == 1
        assert mapper.data.patterns["ruff:E501"].failures == 1
        assert mapper.data.patterns["ruff:E501"].successes == 1

    def test_raises_error_after_max_retries(self, tmp_path):
        """Test raises error when all retries exhausted."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        manager = AgentManager(mapper=mapper)

        # Register mock agent that always fails
        mock_agent = create_mock_agent()
        mock_agent.generate_fix = MagicMock(
            side_effect=Exception("Always fails")
        )
        manager.register_agent("test_agent", mock_agent)

        # Should raise after max_retries
        with pytest.raises(RuntimeError, match="All .* retry attempts failed"):
            manager.generate_fix_with_intelligent_fallback(
                "test_agent",
                error,
                {},
                "",
                "",
                max_retries=2,
            )

        # Should have recorded all failures
        assert mapper.data.total_attempts == 2
        assert mapper.data.total_successes == 0

    def test_uses_historically_successful_strategies(self, tmp_path):
        """Test uses strategies that worked before for same error."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error(code="E501")

        # Record history: DETAILED works, NORMAL doesn't
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        manager = AgentManager(mapper=mapper)

        # Register mock agent
        mock_agent = create_mock_agent()
        mock_agent.generate_fix = MagicMock(return_value="fixed")
        manager.register_agent("test_agent", mock_agent)

        # Should succeed quickly using historical knowledge
        result = manager.generate_fix_with_intelligent_fallback(
            "test_agent",
            error,
            {},
            "",
            "",
        )

        assert result == "fixed"

    def test_fallback_to_simple_mode_without_mapper(self):
        """Test falls back to simple mode when no mapper available."""
        # Create manager without mapper
        manager = AgentManager()

        # Register mock agent
        mock_agent = create_mock_agent()
        mock_agent.generate_fix = MagicMock(return_value="fixed")
        manager.register_agent("test_agent", mock_agent)

        error = create_sample_error()

        # Should still work, just without intelligent fallback
        result = manager.generate_fix_with_intelligent_fallback(
            "test_agent",
            error,
            {},
            "",
            "",
        )

        assert result == "fixed"

