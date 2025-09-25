"""Unit tests for CLI functionality."""

from pathlib import Path

import pytest
from typer import Exit

from stomper.cli import validate_file_selection


@pytest.mark.unit
class TestCLIValidation:
    """Test CLI validation functionality."""

    def test_validate_file_selection_single_file(self):
        """Test validation with single file."""
        # Should not raise an exception
        validate_file_selection(
            file=Path("test.py"), files=None, directory=None, pattern=None,
            git_changed=False, git_staged=False, git_diff=None
        )

    def test_validate_file_selection_multiple_files(self):
        """Test validation with multiple files."""
        # Should not raise an exception
        validate_file_selection(
            file=None, files="test1.py,test2.py", directory=None, pattern=None,
            git_changed=False, git_staged=False, git_diff=None
        )

    def test_validate_file_selection_directory(self):
        """Test validation with directory."""
        # Should not raise an exception
        validate_file_selection(
            file=None, files=None, directory=Path("src/"), pattern=None,
            git_changed=False, git_staged=False, git_diff=None
        )

    def test_validate_file_selection_pattern(self):
        """Test validation with pattern."""
        # Should not raise an exception
        validate_file_selection(
            file=None, files=None, directory=None, pattern="src/**/*.py",
            git_changed=False, git_staged=False, git_diff=None
        )

    def test_validate_file_selection_git_changed(self):
        """Test validation with git changed."""
        # Should not raise an exception
        validate_file_selection(
            file=None, files=None, directory=None, pattern=None,
            git_changed=True, git_staged=False, git_diff=None
        )

    def test_validate_file_selection_git_staged(self):
        """Test validation with git staged."""
        # Should not raise an exception
        validate_file_selection(
            file=None, files=None, directory=None, pattern=None,
            git_changed=False, git_staged=True, git_diff=None
        )

    def test_validate_file_selection_git_diff(self):
        """Test validation with git diff."""
        # Should not raise an exception
        validate_file_selection(
            file=None, files=None, directory=None, pattern=None,
            git_changed=False, git_staged=False, git_diff="main"
        )

    def test_validate_file_selection_conflict(self):
        """Test validation with conflicting options."""
        with pytest.raises(Exit):
            validate_file_selection(
                file=Path("test.py"), files="test1.py,test2.py", directory=None, pattern=None,
                git_changed=False, git_staged=False, git_diff=None
            )
