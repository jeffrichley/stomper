"""Drill Sergeant quality tool integration."""

import json
from pathlib import Path

from .base import BaseQualityTool, QualityError


class DrillSergeantTool(BaseQualityTool):
    """Drill Sergeant test quality tool integration."""

    def __init__(self):
        """Initialize Drill Sergeant tool."""
        super().__init__("drill-sergeant")

    @property
    def command(self) -> str:
        """Get the Drill Sergeant command."""
        return "drill-sergeant"

    @property
    def json_output_flag(self) -> str:
        """Get the JSON output flag."""
        return "--json"

    def parse_errors(self, json_output: str, project_root: Path) -> list[QualityError]:
        """Parse Drill Sergeant JSON output into QualityError objects.

        Args:
            json_output: Raw JSON output from Drill Sergeant
            project_root: Root directory of the project

        Returns:
            List of QualityError objects
        """
        if not json_output.strip():
            return []

        try:
            data = json.loads(json_output)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Drill Sergeant JSON output: {e}")

        errors = []

        # Drill Sergeant typically outputs violations in a specific format
        # This is a generic implementation - may need adjustment based on actual output
        violations = data.get("violations", [])

        for violation in violations:
            file_path = project_root / violation.get("filename", "")

            if not file_path.exists():
                continue

            line = violation.get("line", 1)
            column = violation.get("column", 1)
            code = violation.get("code", "")
            message = violation.get("message", "")

            # Drill Sergeant violations are typically warnings about test quality
            severity = "warning"
            auto_fixable = False  # Most test quality issues require manual fixes

            error = QualityError(
                tool=self.tool_name,
                file=file_path,
                line=line,
                column=column,
                code=code,
                message=message,
                severity=severity,
                auto_fixable=auto_fixable,
            )

            errors.append(error)

        return errors

    def get_config_file(self, project_root: Path) -> Path | None:
        """Get Drill Sergeant configuration file.

        Args:
            project_root: Root directory of the project

        Returns:
            Path to pyproject.toml if found, None otherwise
        """
        pyproject_path = project_root / "pyproject.toml"
        return pyproject_path if pyproject_path.exists() else None
