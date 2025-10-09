"""End-to-end tests for stats command."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from stomper.cli import app
from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import FixOutcome, PromptStrategy
from stomper.quality.base import QualityError


runner = CliRunner()


@pytest.mark.e2e
def test_stats_command_displays_statistics(tmp_path):
    """Test stats command displays learning statistics."""
    # Create some learning data
    mapper = ErrorMapper(project_root=tmp_path)
    error = QualityError(
        tool="ruff",
        file=Path("test.py"),
        line=10,
        column=0,
        code="E501",
        message="Line too long",
        severity="error",
        auto_fixable=True,
    )

    # Record some attempts - 5 successes, 2 failures = 71.4%
    for _ in range(5):
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
    for _ in range(2):
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.MINIMAL)

    # Run stats command
    result = runner.invoke(app, ["stats", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Learning Statistics" in result.stdout
    assert "Overall Performance" in result.stdout
    # Check for success rate (might be formatted as 71.4% or 71%)
    assert "71" in result.stdout


@pytest.mark.e2e
def test_stats_command_verbose_mode(tmp_path):
    """Test stats command verbose mode shows all patterns."""
    mapper = ErrorMapper(project_root=tmp_path)
    error = QualityError(
        tool="ruff",
        file=Path("test.py"),
        line=10,
        column=0,
        code="E501",
        message="Line too long",
        severity="error",
        auto_fixable=True,
    )

    mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)

    result = runner.invoke(app, ["stats", "--project-root", str(tmp_path), "--verbose"])

    assert result.exit_code == 0
    assert "All Error Patterns" in result.stdout
    assert "E501" in result.stdout


@pytest.mark.e2e
def test_stats_command_no_data(tmp_path):
    """Test stats command with no learning data."""
    # Don't create any learning data - just run command
    result = runner.invoke(app, ["stats", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "No learning data yet" in result.stdout


@pytest.mark.e2e
def test_stats_command_shows_difficult_errors(tmp_path):
    """Test stats command shows difficult errors table."""
    mapper = ErrorMapper(project_root=tmp_path)
    error = QualityError(
        tool="ruff",
        file=Path("test.py"),
        line=10,
        column=0,
        code="E501",
        message="Line too long",
        severity="error",
        auto_fixable=True,
    )

    # Create difficult pattern (25% success rate, 4 attempts)
    mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.NORMAL)
    mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
    mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
    mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)

    result = runner.invoke(app, ["stats", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Needs Improvement" in result.stdout
    assert "E501" in result.stdout


@pytest.mark.e2e
def test_stats_command_shows_mastered_errors(tmp_path):
    """Test stats command shows mastered errors table."""
    mapper = ErrorMapper(project_root=tmp_path)
    error = QualityError(
        tool="ruff",
        file=Path("test.py"),
        line=10,
        column=0,
        code="F401",
        message="Unused import",
        severity="error",
        auto_fixable=True,
    )

    # Create easy pattern (90% success rate, 10 attempts)
    for _ in range(9):
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.MINIMAL)
    mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.MINIMAL)

    result = runner.invoke(app, ["stats", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Mastered Errors" in result.stdout
    assert "F401" in result.stdout
    assert "90" in result.stdout

