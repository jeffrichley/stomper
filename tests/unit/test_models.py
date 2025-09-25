"""Unit tests for data models."""

from pathlib import Path

import pytest

from stomper.models.cli import FixOptions, ProcessingStats, QualityTool


@pytest.mark.unit
class TestFixOptions:
    """Test FixOptions model."""

    def test_default_values(self):
        """Test default values are set correctly."""
        options = FixOptions()

        assert options.ruff is True
        assert options.mypy is True
        assert options.drill_sergeant is False
        assert options.file is None
        assert options.files is None
        assert options.error_type is None
        assert options.ignore is None
        assert options.max_errors == 100
        assert options.dry_run is False
        assert options.verbose is False

    def test_custom_values(self):
        """Test custom values are set correctly."""
        options = FixOptions(
            ruff=False,
            mypy=True,
            drill_sergeant=True,
            file=Path("test.py"),
            files=[Path("file1.py"), Path("file2.py")],
            error_type="E501",
            ignore=["F401", "F841"],
            max_errors=50,
            dry_run=True,
            verbose=True,
        )

        assert options.ruff is False
        assert options.mypy is True
        assert options.drill_sergeant is True
        assert options.file == Path("test.py")
        assert options.files == [Path("file1.py"), Path("file2.py")]
        assert options.error_type == "E501"
        assert options.ignore == ["F401", "F841"]
        assert options.max_errors == 50
        assert options.dry_run is True
        assert options.verbose is True


@pytest.mark.unit
class TestQualityTool:
    """Test QualityTool model."""

    def test_default_values(self):
        """Test default values are set correctly."""
        tool = QualityTool(name="ruff", command="ruff check")

        assert tool.name == "ruff"
        assert tool.command == "ruff check"
        assert tool.enabled is True
        assert tool.args == []

    def test_custom_values(self):
        """Test custom values are set correctly."""
        tool = QualityTool(
            name="mypy", command="mypy", enabled=False, args=["--show-error-codes", "--json-report"]
        )

        assert tool.name == "mypy"
        assert tool.command == "mypy"
        assert tool.enabled is False
        assert tool.args == ["--show-error-codes", "--json-report"]


@pytest.mark.unit
class TestProcessingStats:
    """Test ProcessingStats model."""

    def test_default_values(self):
        """Test default values are set correctly."""
        stats = ProcessingStats()

        assert stats.total_files == 0
        assert stats.total_errors == 0
        assert stats.fixed_errors == 0
        assert stats.failed_fixes == 0
        assert stats.skipped_errors == 0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = ProcessingStats(total_errors=100, fixed_errors=80, failed_fixes=20)

        assert stats.success_rate == 80.0

    def test_success_rate_zero_errors(self):
        """Test success rate with zero errors."""
        stats = ProcessingStats(total_errors=0)

        assert stats.success_rate == 0.0

    def test_success_rate_partial_fixes(self):
        """Test success rate with partial fixes."""
        stats = ProcessingStats(
            total_errors=50, fixed_errors=30, failed_fixes=10, skipped_errors=10
        )

        assert stats.success_rate == 60.0
