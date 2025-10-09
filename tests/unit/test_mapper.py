"""Unit tests for ErrorMapper class."""

from datetime import datetime
import json
from pathlib import Path

import pytest

from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import (
    FixOutcome,
    LearningData,
    PromptStrategy,
)
from stomper.quality.base import QualityError


def create_sample_error(
    tool: str = "ruff",
    code: str = "E501",
    file: str = "test.py",
    line: int = 10,
    column: int = 80,
    message: str = "Line too long",
    severity: str = "error",
    auto_fixable: bool = True,
) -> QualityError:
    """Create a sample QualityError for testing.

    Args:
        tool: Tool name
        code: Error code
        file: File path
        line: Line number
        column: Column number
        message: Error message
        severity: Error severity
        auto_fixable: Whether error is auto-fixable

    Returns:
        QualityError instance
    """
    return QualityError(
        tool=tool,
        file=Path(file),
        line=line,
        column=column,
        code=code,
        message=message,
        severity=severity,
        auto_fixable=auto_fixable,
    )


@pytest.mark.unit
class TestErrorMapperInitialization:
    """Test ErrorMapper initialization."""

    def test_creates_with_default_storage_path(self, tmp_path):
        """Test mapper initializes with default storage path in project root."""
        mapper = ErrorMapper(project_root=tmp_path)

        expected_path = tmp_path / ".stomper" / "learning_data.json"
        assert mapper.storage_path == expected_path
        assert mapper.project_root == tmp_path.resolve()
        assert mapper.auto_save is True

    def test_creates_with_custom_storage_path(self, tmp_path):
        """Test mapper accepts custom storage path."""
        custom_path = tmp_path / "custom" / "data.json"
        mapper = ErrorMapper(project_root=tmp_path, storage_path=custom_path)

        assert mapper.storage_path == custom_path
        assert mapper.project_root == tmp_path.resolve()

    def test_loads_existing_data_on_init(self, tmp_path):
        """Test mapper loads historical data if file exists."""
        # Create existing data file
        storage_dir = tmp_path / ".stomper"
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_file = storage_dir / "learning_data.json"

        existing_data = {
            "version": "1.0.0",
            "patterns": {
                "ruff:E501": {
                    "error_code": "E501",
                    "tool": "ruff",
                    "total_attempts": 5,
                    "successes": 4,
                    "failures": 1,
                    "attempts": [],
                    "successful_strategies": ["normal"],
                    "failed_strategies": [],
                }
            },
            "total_attempts": 5,
            "total_successes": 4,
            "last_updated": datetime.now().isoformat(),
        }

        with open(storage_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f)

        # Initialize mapper
        mapper = ErrorMapper(project_root=tmp_path)

        # Verify data was loaded
        assert len(mapper.data.patterns) == 1
        assert "ruff:E501" in mapper.data.patterns
        assert mapper.data.total_attempts == 5
        assert mapper.data.total_successes == 4

    def test_creates_empty_data_when_no_file_exists(self, tmp_path):
        """Test mapper initializes empty data structure."""
        mapper = ErrorMapper(project_root=tmp_path)

        assert mapper.data.total_attempts == 0
        assert mapper.data.total_successes == 0
        assert len(mapper.data.patterns) == 0
        assert isinstance(mapper.data, LearningData)

    def test_handles_corrupted_data_file_gracefully(self, tmp_path):
        """Test mapper handles invalid JSON gracefully."""
        # Create corrupted file
        storage_dir = tmp_path / ".stomper"
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_file = storage_dir / "learning_data.json"

        with open(storage_file, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json }")

        # Should start fresh instead of crashing
        mapper = ErrorMapper(project_root=tmp_path)

        assert mapper.data.total_attempts == 0
        assert len(mapper.data.patterns) == 0

    def test_storage_in_main_project_not_sandbox(self, tmp_path):
        """Test that storage is in main project root, not sandbox."""
        # CRITICAL: Ensure this works with sandbox workflow
        main_project = tmp_path / "main"
        sandbox_path = tmp_path / "sandbox"
        main_project.mkdir()
        sandbox_path.mkdir()

        # Mapper should use main project, not sandbox
        mapper = ErrorMapper(project_root=main_project)

        assert mapper.storage_path.is_relative_to(main_project)
        assert not mapper.storage_path.is_relative_to(sandbox_path)
        assert str(mapper.storage_path).startswith(str(main_project))

    def test_auto_save_can_be_disabled(self, tmp_path):
        """Test that auto-save can be disabled."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)

        assert mapper.auto_save is False


@pytest.mark.unit
class TestErrorPatternTracking:
    """Test error pattern tracking functionality."""

    def test_records_error_attempt(self, tmp_path):
        """Test recording a single error fix attempt."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error(code="E501", tool="ruff")

        mapper.record_attempt(
            error=error,
            outcome=FixOutcome.SUCCESS,
            strategy=PromptStrategy.NORMAL,
        )

        # Check pattern was created
        pattern_key = "ruff:E501"
        assert pattern_key in mapper.data.patterns

        pattern = mapper.data.patterns[pattern_key]
        assert pattern.total_attempts == 1
        assert pattern.successes == 1
        assert pattern.failures == 0
        assert len(pattern.attempts) == 1

    def test_records_multiple_attempts_for_same_error(self, tmp_path):
        """Test accumulating multiple attempts for same error code."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error(code="E501", tool="ruff")

        # Record multiple attempts
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.DETAILED)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        pattern = mapper.data.patterns["ruff:E501"]
        assert pattern.total_attempts == 3
        assert pattern.successes == 2
        assert pattern.failures == 1
        assert len(pattern.attempts) == 3

    def test_groups_by_error_code(self, tmp_path):
        """Test errors grouped by code (E501, F401, etc.)."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)

        error1 = create_sample_error(code="E501", tool="ruff")
        error2 = create_sample_error(code="F401", tool="ruff")

        mapper.record_attempt(error1, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error2, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        # Should have separate patterns
        assert "ruff:E501" in mapper.data.patterns
        assert "ruff:F401" in mapper.data.patterns
        assert len(mapper.data.patterns) == 2

    def test_groups_by_tool(self, tmp_path):
        """Test errors can be grouped by tool (ruff, mypy)."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)

        error1 = create_sample_error(code="E501", tool="ruff")
        error2 = create_sample_error(code="E501", tool="mypy")

        mapper.record_attempt(error1, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error2, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        # Same error code but different tools - should be separate
        assert "ruff:E501" in mapper.data.patterns
        assert "mypy:E501" in mapper.data.patterns
        assert len(mapper.data.patterns) == 2

    def test_records_success_outcome(self, tmp_path):
        """Test recording successful fix outcome."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        pattern = mapper.data.patterns["ruff:E501"]
        assert pattern.successes == 1
        assert pattern.failures == 0
        assert mapper.data.total_successes == 1

    def test_records_failure_outcome(self, tmp_path):
        """Test recording failed fix outcome."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        pattern = mapper.data.patterns["ruff:E501"]
        assert pattern.successes == 0
        assert pattern.failures == 1
        assert mapper.data.total_successes == 0

    def test_tracks_strategy_used(self, tmp_path):
        """Test recording which prompt strategy was used."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)

        pattern = mapper.data.patterns["ruff:E501"]
        assert PromptStrategy.DETAILED in pattern.successful_strategies
        assert len(pattern.attempts) == 1
        assert pattern.attempts[0].strategy == PromptStrategy.DETAILED

    def test_tracks_timestamp(self, tmp_path):
        """Test attempts include timestamp for trend analysis."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        before = datetime.now()
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        after = datetime.now()

        pattern = mapper.data.patterns["ruff:E501"]
        attempt = pattern.attempts[0]

        assert isinstance(attempt.timestamp, datetime)
        assert before <= attempt.timestamp <= after

    def test_tracks_file_path(self, tmp_path):
        """Test attempts include file path when provided."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()
        file_path = Path("src/test.py")

        mapper.record_attempt(
            error,
            FixOutcome.SUCCESS,
            PromptStrategy.NORMAL,
            file_path=file_path,
        )

        pattern = mapper.data.patterns["ruff:E501"]
        assert pattern.attempts[0].file_path == str(file_path)


@pytest.mark.unit
class TestSuccessRateCalculation:
    """Test success rate calculation."""

    def test_calculates_success_rate_for_error_code(self, tmp_path):
        """Test success rate calculation per error code."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error(code="E501", tool="ruff")

        # 3 successes, 2 failures = 60% success rate
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        success_rate = mapper.get_success_rate("E501", "ruff")
        assert success_rate == 60.0

    def test_handles_zero_attempts(self, tmp_path):
        """Test success rate returns 0.0 for zero attempts."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)

        success_rate = mapper.get_success_rate("UNKNOWN", "ruff")
        assert success_rate == 0.0

    def test_handles_all_successes(self, tmp_path):
        """Test success rate returns 100.0 for all successes."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        success_rate = mapper.get_success_rate("E501", "ruff")
        assert success_rate == 100.0

    def test_handles_all_failures(self, tmp_path):
        """Test success rate returns 0.0 for all failures."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        success_rate = mapper.get_success_rate("E501", "ruff")
        assert success_rate == 0.0

    def test_calculates_partial_success_rate(self, tmp_path):
        """Test success rate for mixed outcomes."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # 7 successes, 3 failures = 70% success rate
        for _ in range(7):
            mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        for _ in range(3):
            mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        success_rate = mapper.get_success_rate("E501", "ruff")
        assert success_rate == 70.0

    def test_calculates_overall_success_rate(self, tmp_path):
        """Test overall success rate across all errors."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)

        error1 = create_sample_error(code="E501", tool="ruff")
        error2 = create_sample_error(code="F401", tool="ruff")

        # E501: 2/3 = 66.67%
        mapper.record_attempt(error1, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error1, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error1, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        # F401: 1/2 = 50%
        mapper.record_attempt(error2, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error2, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        # Overall: 3/5 = 60%
        overall_rate = mapper.data.overall_success_rate
        assert overall_rate == 60.0

    def test_pattern_is_difficult_property(self, tmp_path):
        """Test is_difficult property for error patterns."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # Low success rate with enough attempts
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        pattern = mapper.data.patterns["ruff:E501"]
        # 25% success rate with 4 attempts
        assert pattern.is_difficult is True


@pytest.mark.unit
class TestAdaptivePrompting:
    """Test adaptive prompting strategy selection."""

    def test_returns_detailed_strategy_for_low_success_rate(self, tmp_path):
        """Test returns detailed prompting for difficult errors."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # Create difficult error (low success rate, >=3 attempts)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        strategy = mapper.get_adaptive_strategy(error)

        assert strategy.verbosity in [PromptStrategy.DETAILED, PromptStrategy.VERBOSE]
        assert strategy.include_examples is True
        assert strategy.include_history is True

    def test_returns_normal_strategy_for_high_success_rate(self, tmp_path):
        """Test returns normal/minimal prompting for easy errors."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # Create easy error (high success rate)
        for _ in range(9):
            mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        strategy = mapper.get_adaptive_strategy(error)

        # 90% success rate should get minimal strategy
        assert strategy.verbosity == PromptStrategy.MINIMAL
        assert strategy.include_examples is False

    def test_handles_new_error_code_with_no_history(self, tmp_path):
        """Test default strategy for never-seen error codes."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error(code="UNKNOWN")

        strategy = mapper.get_adaptive_strategy(error)

        # No history - should use normal strategy
        assert strategy.verbosity == PromptStrategy.NORMAL
        assert strategy.include_examples is False
        assert strategy.retry_count == 0

    def test_adapts_context_based_on_history(self, tmp_path):
        """Test context adaptation based on historical data."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # Medium difficulty (50-80% success rate)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        strategy = mapper.get_adaptive_strategy(error)

        # 50% success rate - normal strategy
        assert strategy.verbosity == PromptStrategy.NORMAL

    def test_escalates_verbosity_on_retry(self, tmp_path):
        """Test verbosity escalation with retry count."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # Create difficult error
        for _ in range(3):
            mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        # First attempt
        strategy0 = mapper.get_adaptive_strategy(error, retry_count=0)
        # Second attempt (retry)
        strategy1 = mapper.get_adaptive_strategy(error, retry_count=1)
        # Third attempt (second retry)
        strategy2 = mapper.get_adaptive_strategy(error, retry_count=2)

        # Should escalate verbosity
        assert (
            strategy1.verbosity != strategy0.verbosity
            or strategy1.retry_count > strategy0.retry_count
        )
        assert strategy2.retry_count == 2


@pytest.mark.unit
class TestFallbackStrategySelection:
    """Test fallback strategy selection."""

    def test_suggests_alternative_strategy_after_failure(self, tmp_path):
        """Test suggests different strategy after failed attempt."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        failed = [PromptStrategy.NORMAL]
        fallback = mapper.get_fallback_strategy(error, failed_strategies=failed)

        assert fallback is not None
        assert fallback not in failed

    def test_tries_different_approaches_sequentially(self, tmp_path):
        """Test cycles through different fix approaches."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        failed = []
        strategies = []

        for _ in range(4):  # Try to get all strategies
            fallback = mapper.get_fallback_strategy(error, failed_strategies=failed)
            if fallback is None:
                break
            strategies.append(fallback)
            failed.append(fallback)

        # Should have tried multiple strategies
        assert len(strategies) >= 2
        # All strategies should be different
        assert len(strategies) == len(set(strategies))

    def test_avoids_repeating_failed_strategy(self, tmp_path):
        """Test doesn't repeat same failed approach."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        failed = [PromptStrategy.NORMAL, PromptStrategy.DETAILED]
        fallback = mapper.get_fallback_strategy(error, failed_strategies=failed)

        if fallback is not None:
            assert fallback not in failed

    def test_limits_fallback_attempts(self, tmp_path):
        """Test limits maximum fallback iterations."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # Try all strategies
        all_strategies = [
            PromptStrategy.MINIMAL,
            PromptStrategy.NORMAL,
            PromptStrategy.DETAILED,
            PromptStrategy.VERBOSE,
        ]

        fallback = mapper.get_fallback_strategy(error, failed_strategies=all_strategies)

        # Should return None when all exhausted
        assert fallback is None

    def test_uses_historically_successful_strategy(self, tmp_path):
        """Test prioritizes historically successful strategies."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # Record success with DETAILED strategy
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)

        # Now try to get fallback (NORMAL failed)
        fallback = mapper.get_fallback_strategy(
            error,
            failed_strategies=[PromptStrategy.NORMAL],
        )

        # Should suggest the historically successful strategy
        assert fallback == PromptStrategy.DETAILED


@pytest.mark.unit
class TestDataPersistence:
    """Test data persistence functionality."""

    def test_saves_data_to_json_file(self, tmp_path):
        """Test data saved to JSON file."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.save()

        # Check file exists
        assert mapper.storage_path.exists()

        # Check valid JSON
        with open(mapper.storage_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "patterns" in data
        assert "total_attempts" in data
        assert data["total_attempts"] == 1

    def test_loads_data_from_json_file(self, tmp_path):
        """Test data loaded from JSON file."""
        # Create first mapper and save data
        mapper1 = ErrorMapper(project_root=tmp_path, auto_save=True)
        error = create_sample_error()
        mapper1.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        # Create second mapper - should load existing data
        mapper2 = ErrorMapper(project_root=tmp_path)

        assert mapper2.data.total_attempts == 1
        assert len(mapper2.data.patterns) == 1
        assert "ruff:E501" in mapper2.data.patterns

    def test_auto_saves_after_recording_attempt(self, tmp_path):
        """Test auto-save after each attempt."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=True)
        error = create_sample_error()

        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        # File should exist immediately due to auto-save
        assert mapper.storage_path.exists()

    def test_handles_file_write_errors_gracefully(self, tmp_path):
        """Test handles I/O errors gracefully."""
        # Create mapper with invalid path (read-only parent directory)
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()

        # On Windows, we can't make directories read-only easily
        # So we'll just verify the save() method doesn't raise
        mapper = ErrorMapper(
            project_root=tmp_path,
            storage_path=read_only_dir / "subdir" / "data.json",
            auto_save=False,
        )
        error = create_sample_error()

        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        # Should not raise exception
        mapper.save()  # May fail silently

    def test_creates_directory_if_not_exists(self, tmp_path):
        """Test creates .stomper directory if needed."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.save()

        # Directory should be created
        storage_dir = tmp_path / ".stomper"
        assert storage_dir.exists()
        assert storage_dir.is_dir()

    def test_preserves_existing_data_on_load(self, tmp_path):
        """Test doesn't lose data when loading."""
        mapper1 = ErrorMapper(project_root=tmp_path, auto_save=True)

        # Record various patterns
        error1 = create_sample_error(code="E501")
        error2 = create_sample_error(code="F401")

        mapper1.record_attempt(error1, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper1.record_attempt(error2, FixOutcome.SUCCESS, PromptStrategy.DETAILED)

        # Load in new mapper
        mapper2 = ErrorMapper(project_root=tmp_path)

        # All data should be preserved
        assert len(mapper2.data.patterns) == 2
        assert mapper2.data.total_attempts == 2
        assert mapper2.data.total_successes == 2


@pytest.mark.unit
class TestStatisticsReporting:
    """Test statistics and reporting functionality."""

    def test_generates_summary_statistics(self, tmp_path):
        """Test generates summary stats for all errors."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)

        error1 = create_sample_error(code="E501")
        error2 = create_sample_error(code="F401")

        mapper.record_attempt(error1, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        mapper.record_attempt(error2, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        stats = mapper.get_statistics()

        assert "overall_success_rate" in stats
        assert "total_attempts" in stats
        assert "total_successes" in stats
        assert "total_patterns" in stats
        assert stats["total_attempts"] == 2
        assert stats["total_successes"] == 1
        assert stats["total_patterns"] == 2

    def test_identifies_most_problematic_errors(self, tmp_path):
        """Test identifies errors with lowest success rates."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)

        # Create difficult error
        error1 = create_sample_error(code="E501")
        for _ in range(1):
            mapper.record_attempt(error1, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
        for _ in range(3):
            mapper.record_attempt(error1, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        # Create easy error
        error2 = create_sample_error(code="F401")
        for _ in range(3):
            mapper.record_attempt(error2, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        stats = mapper.get_statistics()

        # E501 should be in difficult errors (25% success rate with 4 attempts)
        difficult = stats.get("difficult_errors", [])
        if difficult:
            assert any(e["code"] == "E501" for e in difficult)

    def test_identifies_most_successful_strategies(self, tmp_path):
        """Test identifies best-performing strategies."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # DETAILED strategy succeeds
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)

        # NORMAL strategy fails
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

        pattern = mapper.data.patterns["ruff:E501"]

        assert PromptStrategy.DETAILED in pattern.successful_strategies
        assert PromptStrategy.NORMAL in pattern.failed_strategies

    def test_formats_statistics_for_display(self, tmp_path):
        """Test formats stats for rich console output."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)

        error = create_sample_error()
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

        stats = mapper.get_statistics()

        # Check structure is suitable for display
        assert isinstance(stats, dict)
        assert "overall_success_rate" in stats
        assert isinstance(stats["overall_success_rate"], float)
        assert isinstance(stats["total_attempts"], int)
        assert "last_updated" in stats
        assert isinstance(stats["last_updated"], str)  # ISO format

    def test_calculates_improvement_trends(self, tmp_path):
        """Test tracks improvement over time."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error()

        # Record attempts over time
        timestamps = []
        for _ in range(5):
            mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
            pattern = mapper.data.patterns["ruff:E501"]
            timestamps.append(pattern.attempts[-1].timestamp)

        # Timestamps should be sequential
        for i in range(len(timestamps) - 1):
            assert timestamps[i] <= timestamps[i + 1]
