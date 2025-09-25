"""MyPy quality tool integration for Stomper."""

from pathlib import Path

from .base import BaseQualityTool, QualityError


class MyPyTool(BaseQualityTool):
    """MyPy type checker integration."""

    def __init__(self):
        super().__init__("mypy")

    @property
    def command(self) -> str:
        return "mypy"

    @property
    def json_output_flag(self) -> str:
        return "--show-error-codes"

    def parse_errors(self, text_output: str, project_root: Path) -> list[QualityError]:
        """Parse MyPy text output and extract errors.

        Args:
            text_output: Text output from MyPy
            project_root: Root directory of the project

        Returns:
            List of QualityError objects
        """
        if not text_output.strip():
            return []

        errors = []

        # Parse MyPy text output line by line
        # Format: "file:line: error: message [error-code]"
        # Example: "src/file.py:10: error: Incompatible types [assignment]"
        for line in text_output.strip().split("\n"):
            if not line.strip() or "error:" not in line:
                continue

            # Parse line format: "file:line: error: message [error-code]"
            parts = line.split(":")
            if len(parts) < 3:
                continue

            file_path_str = parts[0].strip()
            if not file_path_str:
                continue

            try:
                line_num = int(parts[1].strip())
            except (ValueError, IndexError):
                line_num = 1

            # Extract error message and code
            error_part = ":".join(parts[2:]).strip()
            if "error:" in error_part:
                message = error_part.split("error:")[1].strip()
                # Extract error code from brackets [code]
                if "[" in message and "]" in message:
                    code_start = message.rfind("[") + 1
                    code_end = message.rfind("]")
                    code = message[code_start:code_end]
                    message = message[: code_start - 1].strip()
                else:
                    code = "unknown"
            else:
                message = error_part
                code = "unknown"

            file_path = project_root / file_path_str

            # MyPy errors are generally not auto-fixable
            auto_fixable = False

            # MyPy errors are always "error" severity
            severity = "error"

            error = QualityError(
                tool=self.tool_name,
                file=file_path,
                line=line_num,
                column=0,  # MyPy doesn't provide column info in text output
                code=code,
                message=message,
                severity=severity,
                auto_fixable=auto_fixable,
            )

            errors.append(error)

        return errors

    def _get_base_args(self) -> list[str]:
        """Get base arguments for MyPy command.

        Returns:
            List of base arguments
        """
        return ["--show-error-codes"]

    def discover_tool_config(self, project_root: Path) -> Path | None:
        """Discover MyPy's configuration file using MyPy's own discovery logic.

        Args:
            project_root: Root directory of the project

        Returns:
            Path to MyPy configuration file if found, None otherwise
        """
        # MyPy config discovery order (from mypy docs):
        # 1. mypy.ini
        # 2. .mypy.ini
        # 3. setup.cfg [mypy]
        # 4. pyproject.toml [tool.mypy]

        # Check for mypy.ini
        mypy_ini = project_root / "mypy.ini"
        if mypy_ini.exists():
            return mypy_ini

        # Check for .mypy.ini
        mypy_ini_hidden = project_root / ".mypy.ini"
        if mypy_ini_hidden.exists():
            return mypy_ini_hidden

        # Check for setup.cfg with [mypy] section
        setup_cfg = project_root / "setup.cfg"
        if setup_cfg.exists():
            try:
                with open(setup_cfg) as f:
                    content = f.read()
                    if "[mypy]" in content:
                        return setup_cfg
            except Exception:
                pass

        # Check for pyproject.toml with [tool.mypy] section
        pyproject_path = project_root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib

                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    if "tool" in data and "mypy" in data["tool"]:
                        return pyproject_path
            except Exception:
                pass

        return None

    def _get_stomper_baseline_args(self, project_root: Path) -> list[str]:
        """Get Stomper's baseline configuration for MyPy.

        Args:
            project_root: Root directory of the project

        Returns:
            List of command arguments using Stomper's baseline MyPy configuration
        """
        # Stomper's baseline MyPy configuration
        # Use strict mode with sensible defaults
        return [
            ".",
            "--strict",  # Enable strict mode
            "--show-error-codes",  # Show error codes
            "--exclude",
            "tests/fixtures/",  # Exclude test fixtures
            "--exclude",
            ".*/__pycache__/.*",  # Exclude cache directories (regex format)
        ]

    def _get_pattern_args(
        self, include_patterns: list[str], exclude_patterns: list[str]
    ) -> list[str]:
        """Get pattern-specific arguments for MyPy (DEPRECATED).

        This method is deprecated in favor of _get_tool_native_args() to respect
        the "don't surprise me" rule.

        Args:
            include_patterns: Patterns to include (MyPy uses current directory by default)
            exclude_patterns: Patterns to exclude (MyPy uses --exclude with regex)

        Returns:
            List of command arguments for pattern-based execution
        """
        args = ["."]  # Use current directory for pattern-based discovery

        if exclude_patterns:
            # MyPy expects regex patterns, not glob patterns
            # Convert glob patterns to regex patterns
            for pattern in exclude_patterns:
                # Convert glob to regex: **/pattern/** -> .*pattern.*
                regex_pattern = pattern.replace("**/", ".*").replace("/**", ".*").replace("*", ".*")
                args.extend(["--exclude", regex_pattern])

        return args

    def get_config_file(self, project_root: Path) -> Path | None:
        """Get MyPy configuration file.

        Args:
            project_root: Root directory of the project

        Returns:
            Path to mypy.ini or pyproject.toml if found, None otherwise
        """
        # Check for mypy.ini first
        mypy_ini = project_root / "mypy.ini"
        if mypy_ini.exists():
            return mypy_ini

        # Check for pyproject.toml
        pyproject_path = project_root / "pyproject.toml"
        return pyproject_path if pyproject_path.exists() else None
