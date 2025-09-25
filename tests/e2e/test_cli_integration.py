"""End-to-end tests for CLI integration."""

import pytest
from typer.testing import CliRunner

from stomper.cli import app


@pytest.mark.e2e
class TestCLIIntegration:
    """Test CLI integration functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_help(self):
        """Test that CLI help works."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Fix code quality issues" in result.output
        assert "--file" in result.output
        assert "--files" in result.output
        assert "--directory" in result.output
        assert "--pattern" in result.output
        assert "--exclude" in result.output
        assert "--max-files" in result.output

    def test_cli_version(self):
        """Test CLI version command."""
        result = self.runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "stomper v" in result.output

    def test_cli_file_argument(self):
        """Test --file argument parsing."""
        result = self.runner.invoke(app, ["--file", "test.py", "--dry-run"])

        # Should not crash (though it might fail due to missing file)
        assert result.exit_code in [0, 1]  # 0 for success, 1 for file not found

    def test_cli_files_argument(self):
        """Test --files argument parsing."""
        result = self.runner.invoke(app, ["--files", "test1.py,test2.py", "--dry-run"])

        # Should not crash
        assert result.exit_code in [0, 1]

    def test_cli_directory_argument(self):
        """Test --directory argument parsing."""
        result = self.runner.invoke(app, ["--directory", "src/", "--dry-run"])

        # Should not crash
        assert result.exit_code in [0, 1]

    def test_cli_pattern_argument(self):
        """Test --pattern argument parsing."""
        result = self.runner.invoke(app, ["--pattern", "src/**/*.py", "--dry-run"])

        # Should not crash
        assert result.exit_code in [0, 1]

    def test_cli_exclude_argument(self):
        """Test --exclude argument parsing."""
        result = self.runner.invoke(
            app, ["--pattern", "src/**/*.py", "--exclude", "**/__pycache__/**", "--dry-run"]
        )

        # Should not crash
        assert result.exit_code in [0, 1]

    def test_cli_max_files_argument(self):
        """Test --max-files argument parsing."""
        result = self.runner.invoke(
            app, ["--pattern", "src/**/*.py", "--max-files", "5", "--dry-run"]
        )

        # Should not crash
        assert result.exit_code in [0, 1]

    def test_cli_error_type_argument(self):
        """Test --error-type argument parsing."""
        result = self.runner.invoke(app, ["--file", "test.py", "--error-type", "E501", "--dry-run"])

        # Should not crash
        assert result.exit_code in [0, 1]

    def test_cli_ignore_argument(self):
        """Test --ignore argument parsing."""
        result = self.runner.invoke(
            app, ["--file", "test.py", "--ignore", "E501,F401", "--dry-run"]
        )

        # Should not crash
        assert result.exit_code in [0, 1]

    def test_cli_mutual_exclusivity_file_files(self):
        """Test mutual exclusivity between --file and --files."""
        result = self.runner.invoke(
            app, ["--file", "test.py", "--files", "test1.py,test2.py", "--dry-run"]
        )

        # Should fail due to mutual exclusivity
        assert result.exit_code != 0

    def test_cli_mutual_exclusivity_file_directory(self):
        """Test mutual exclusivity between --file and --directory."""
        result = self.runner.invoke(app, ["--file", "test.py", "--directory", "src/", "--dry-run"])

        # Should fail due to mutual exclusivity
        assert result.exit_code != 0

    def test_cli_mutual_exclusivity_file_pattern(self):
        """Test mutual exclusivity between --file and --pattern."""
        result = self.runner.invoke(
            app, ["--file", "test.py", "--pattern", "src/**/*.py", "--dry-run"]
        )

        # Should fail due to mutual exclusivity
        assert result.exit_code != 0
