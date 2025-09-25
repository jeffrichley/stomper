"""Pytest quality tool integration."""

import json
from pathlib import Path

from .base import BaseQualityTool, QualityError


class PytestTool(BaseQualityTool):
    """Pytest test runner integration."""

    def __init__(self):
        """Initialize Pytest tool."""
        super().__init__("pytest")

    @property
    def command(self) -> str:
        """Get the Pytest command."""
        return "pytest"

    @property
    def json_output_flag(self) -> str:
        """Get the JSON output flag."""
        return "--json-report"

    def parse_errors(self, json_output: str, project_root: Path) -> list[QualityError]:
        """Parse Pytest JSON output into QualityError objects.

        Args:
            json_output: Raw JSON output from Pytest (this is actually a file path)
            project_root: Root directory of the project

        Returns:
            List of QualityError objects
        """
        # Pytest --json-report writes to a file, not stdout
        # We need to read the report file
        report_path = Path(json_output.strip())

        if not report_path.exists():
            return []

        try:
            with open(report_path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse Pytest JSON report: {e}")

        errors = []

        # Pytest JSON report structure
        summary = data.get("summary", {})

        # Process test results
        for test_data in data.get("tests", []):
            if test_data.get("outcome") == "failed":
                file_path = project_root / test_data.get("nodeid", "").split("::")[0]

                # Extract line number from test failure
                line = 1  # Default, could be improved with stack trace parsing
                column = 1

                # Create error message from test failure
                message = f"Test failed: {test_data.get('nodeid', '')}"
                if test_data.get("call", {}).get("longrepr"):
                    message = str(test_data["call"]["longrepr"])

                error = QualityError(
                    tool=self.tool_name,
                    file=file_path,
                    line=line,
                    column=column,
                    code="TEST_FAILED",
                    message=message,
                    severity="error",
                    auto_fixable=False,
                )

                errors.append(error)

        return errors

    def _get_base_args(self) -> list[str]:
        """Get base arguments for Pytest command.

        Returns:
            List of base arguments
        """
        return [
            "--json-report",
            "--json-report-file=/tmp/pytest_report.json",  # Temporary file for JSON report
        ]

    def get_config_file(self, project_root: Path) -> Path | None:
        """Get Pytest configuration file.

        Args:
            project_root: Root directory of the project

        Returns:
            Path to pytest.ini, pyproject.toml, or tox.ini if found, None otherwise
        """
        # Check for pytest.ini first
        pytest_ini = project_root / "pytest.ini"
        if pytest_ini.exists():
            return pytest_ini

        # Check for pyproject.toml
        pyproject_path = project_root / "pyproject.toml"
        if pyproject_path.exists():
            return pyproject_path

        # Check for tox.ini
        tox_ini = project_root / "tox.ini"
        return tox_ini if tox_ini.exists() else None
