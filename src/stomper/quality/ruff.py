"""Ruff quality tool integration."""

import json
from pathlib import Path

from .base import BaseQualityTool, QualityError


class RuffTool(BaseQualityTool):
    """Ruff linter integration."""

    def __init__(self):
        """Initialize Ruff tool."""
        super().__init__("ruff")

    @property
    def command(self) -> str:
        """Get the Ruff command."""
        return "ruff"

    def _get_base_args(self) -> list[str]:
        """Get base arguments for Ruff command.

        Returns:
            List of base arguments
        """
        return ["check", self.json_output_flag]

    @property
    def json_output_flag(self) -> str:
        """Get the JSON output flag."""
        return "--output-format=json"

    def parse_errors(self, json_output: str, project_root: Path) -> list[QualityError]:
        """Parse Ruff JSON output into QualityError objects.

        Args:
            json_output: Raw JSON output from Ruff
            project_root: Root directory of the project

        Returns:
            List of QualityError objects
        """
        if not json_output.strip():
            return []

        try:
            data = json.loads(json_output)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Ruff JSON output: {e}")

        errors = []

        # Ruff outputs a list of violations
        for violation in data:
            file_path = project_root / violation["filename"]

            # Ruff provides line and column information
            line = violation.get("location", {}).get("row", 1)
            column = violation.get("location", {}).get("column", 0)

            # Determine if auto-fixable
            auto_fixable = violation.get("fix", None) is not None

            # Map Ruff severity to standard severity
            severity_map = {
                "E": "error",  # pycodestyle errors
                "W": "warning",  # pycodestyle warnings
                "F": "error",  # pyflakes errors
                "B": "warning",  # flake8-bugbear
                "C4": "warning",  # flake8-comprehensions
                "C9": "warning",  # mccabe complexity
                "D": "warning",  # pydocstyle
                "N": "warning",  # pep8-naming
                "UP": "warning",  # pyupgrade
                "YTT": "warning",  # flake8-2020
                "ANN": "warning",  # flake8-annotations
                "ASYNC": "warning",  # flake8-async
                "S": "warning",  # flake8-bandit
                "BLE": "warning",  # flake8-blind-except
                "FBT": "warning",  # flake8-boolean-trap
                "A": "warning",  # flake8-builtins
                "COM": "warning",  # flake8-commas
                "C90": "warning",  # mccabe
                "DJ": "warning",  # flake8-django
                "EM": "warning",  # flake8-errmsg
                "EXE": "warning",  # flake8-executable
                "FA": "warning",  # flake8-future-annotations
                "ISC": "warning",  # flake8-implicit-str-concat
                "ICN": "warning",  # flake8-import-conventions
                "G": "warning",  # flake8-logging-format
                "INP": "warning",  # flake8-no-pep420
                "PIE": "warning",  # flake8-pie
                "T20": "warning",  # flake8-print
                "PYI": "warning",  # flake8-pyi
                "PT": "warning",  # flake8-pytest-style
                "Q": "warning",  # flake8-quotes
                "RSE": "warning",  # flake8-raise
                "RET": "warning",  # flake8-return
                "SLF": "warning",  # flake8-self
                "SLOT": "warning",  # flake8-slots
                "SIM": "warning",  # flake8-simplify
                "TID": "warning",  # flake8-tidy-imports
                "TCH": "warning",  # flake8-type-checking
                "INT": "warning",  # flake8-gettext
                "ARG": "warning",  # flake8-unused-arguments
                "PTH": "warning",  # flake8-use-pathlib
                "ERA": "warning",  # eradicate
                "PD": "warning",  # pandas-vet
                "PGH": "warning",  # pygrep-hooks
                "PL": "warning",  # pylint
                "TRY": "warning",  # tryceratops
                "FLY": "warning",  # flynt
                "NPY": "warning",  # numpy
                "AIR": "warning",  # airflow
                "PERF": "warning",  # perflint
                "FURB": "warning",  # refurb
                "RUF": "warning",  # ruff-specific rules
            }

            code = violation.get("code", "UNKNOWN")
            severity = "warning"  # default
            if code:
                # Extract prefix for severity mapping
                # For codes like "E501", extract just "E"
                if "." in code:
                    prefix = code.split(".")[0]
                else:
                    # For codes like "E501", take the first letter(s)
                    prefix = code[0] if code[0].isalpha() else code
                severity = severity_map.get(prefix, "warning")

            error = QualityError(
                tool=self.tool_name,
                file=file_path,
                line=line,
                column=column,
                code=code,
                message=violation.get("message", ""),
                severity=severity,
                auto_fixable=auto_fixable,
            )

            errors.append(error)

        return errors

    def discover_tool_config(self, project_root: Path) -> Path | None:
        """Discover Ruff's configuration file using Ruff's own discovery logic.

        Args:
            project_root: Root directory of the project

        Returns:
            Path to Ruff configuration file if found, None otherwise
        """
        # Ruff config discovery order (from ruff docs):
        # 1. pyproject.toml [tool.ruff]
        # 2. ruff.toml
        # 3. .ruff.toml
        # 4. ruff.ini
        # 5. setup.cfg [tool.ruff]

        # Check for pyproject.toml with [tool.ruff] section
        pyproject_path = project_root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib

                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    if "tool" in data and "ruff" in data["tool"]:
                        return pyproject_path
            except Exception:
                pass

        # Check for ruff.toml
        ruff_toml = project_root / "ruff.toml"
        if ruff_toml.exists():
            return ruff_toml

        # Check for .ruff.toml
        ruff_toml_hidden = project_root / ".ruff.toml"
        if ruff_toml_hidden.exists():
            return ruff_toml_hidden

        # Check for ruff.ini
        ruff_ini = project_root / "ruff.ini"
        if ruff_ini.exists():
            return ruff_ini

        # Check for setup.cfg with [tool.ruff] section
        setup_cfg = project_root / "setup.cfg"
        if setup_cfg.exists():
            try:
                with open(setup_cfg) as f:
                    content = f.read()
                    if "[tool.ruff]" in content:
                        return setup_cfg
            except Exception:
                pass

        return None

    def _get_stomper_baseline_args(self, project_root: Path) -> list[str]:
        """Get Stomper's baseline configuration for Ruff.

        Args:
            project_root: Root directory of the project

        Returns:
            List of command arguments using Stomper's baseline Ruff configuration
        """
        # Stomper's baseline Ruff configuration
        # Use sensible defaults with common exclusions
        return [
            ".",
            "--extend-exclude",
            "tests/fixtures/",  # Exclude test fixtures
            "--extend-exclude",
            "**/__pycache__/",  # Exclude cache directories
            "--extend-exclude",
            "**/migrations/",  # Exclude migrations
        ]

    def _get_pattern_args(
        self, include_patterns: list[str], exclude_patterns: list[str]
    ) -> list[str]:
        """Get pattern-specific arguments for Ruff (DEPRECATED).

        This method is deprecated in favor of _get_tool_native_args() to respect
        the "don't surprise me" rule.

        Args:
            include_patterns: Patterns to include (Ruff uses current directory by default)
            exclude_patterns: Patterns to exclude (Ruff uses --extend-exclude)

        Returns:
            List of command arguments for pattern-based execution
        """
        args = ["."]  # Use current directory for pattern-based discovery

        if exclude_patterns:
            args.extend(["--extend-exclude", ",".join(exclude_patterns)])

        return args

    def get_config_file(self, project_root: Path) -> Path | None:
        """Get Ruff configuration file.

        Args:
            project_root: Root directory of the project

        Returns:
            Path to pyproject.toml if found, None otherwise
        """
        pyproject_path = project_root / "pyproject.toml"
        return pyproject_path if pyproject_path.exists() else None
