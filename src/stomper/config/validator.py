"""Configuration validation for Stomper."""

from pathlib import Path

from rich.console import Console

from stomper.config.models import ConfigOverride, StomperConfig

console = Console()


class ConfigValidator:
    """Validates Stomper configuration."""

    def __init__(self):
        """Initialize config validator."""
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate_config(self, config: StomperConfig, project_root: Path) -> bool:
        """Validate a Stomper configuration.

        Args:
            config: Configuration to validate.
            project_root: Root directory of the project.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        self.errors.clear()
        self.warnings.clear()

        # Validate quality tools
        self._validate_quality_tools(config.quality_tools, project_root)

        # Validate AI agent
        self._validate_ai_agent(config.ai_agent)

        # Validate processing options
        self._validate_processing_options(config)

        # Validate ignore patterns
        self._validate_ignore_patterns(config.ignores.files, project_root)

        # Validate git configuration
        self._validate_git_config(config.git)

        # Report results
        if self.warnings:
            for warning in self.warnings:
                console.print(f"[yellow]Warning: {warning}[/yellow]")

        if self.errors:
            for error in self.errors:
                console.print(f"[red]Error: {error}[/red]")
            return False

        return True

    def _validate_quality_tools(self, tools: list[str], project_root: Path) -> None:
        """Validate quality tools configuration."""
        # Check if tools are available
        for tool in tools:
            if tool == "ruff":
                if not self._is_command_available("ruff"):
                    self.warnings.append("Ruff is not available in PATH")
            elif tool == "mypy":
                if not self._is_command_available("mypy"):
                    self.warnings.append("MyPy is not available in PATH")
            elif tool == "drill-sergeant":
                if not self._is_command_available("drill-sergeant"):
                    self.warnings.append("Drill Sergeant is not available in PATH")
            elif tool == "pytest":
                if not self._is_command_available("pytest"):
                    self.warnings.append("Pytest is not available in PATH")

    def _validate_ai_agent(self, agent: str) -> None:
        """Validate AI agent configuration."""
        if agent == "cursor-cli":
            if not self._is_command_available("cursor"):
                self.warnings.append("Cursor CLI is not available in PATH")

    def _validate_processing_options(self, config: StomperConfig) -> None:
        """Validate processing options."""
        if config.max_retries > 10:
            self.warnings.append("max_retries is very high, this may cause long processing times")

        if config.parallel_files > 10:
            self.warnings.append("parallel_files is very high, this may cause resource issues")

    def _validate_ignore_patterns(self, patterns: list[str], project_root: Path) -> None:
        """Validate ignore file patterns."""
        for pattern in patterns:
            # Check if pattern contains valid glob characters
            if "*" in pattern or "?" in pattern or "[" in pattern:
                # This is a glob pattern, which is fine
                continue
            elif "/" in pattern or "\\" in pattern:
                # This looks like a path, check if it exists
                test_path = project_root / pattern
                if not test_path.exists():
                    self.warnings.append(f"Ignore pattern '{pattern}' does not match any files")

    def _validate_git_config(self, git_config) -> None:
        """Validate git configuration."""
        if not git_config.branch_prefix:
            self.errors.append("Git branch prefix cannot be empty")

        if git_config.commit_style not in ["conventional", "simple"]:
            self.warnings.append(f"Unknown commit style: {git_config.commit_style}")

    def _is_command_available(self, command: str) -> bool:
        """Check if a command is available in PATH."""
        import shutil

        return shutil.which(command) is not None

    def validate_cli_overrides(self, overrides: ConfigOverride) -> bool:
        """Validate CLI argument overrides.

        Args:
            overrides: CLI overrides to validate.

        Returns:
            bool: True if overrides are valid, False otherwise.
        """
        self.errors.clear()
        self.warnings.clear()

        # Validate file selection mutual exclusivity
        file_selection_count = sum(
            [
                overrides.file is not None,
                overrides.files is not None,
                overrides.directory is not None,
            ]
        )

        if file_selection_count > 1:
            self.errors.append("Only one of --file, --files, or --directory can be specified")

        # Validate file paths
        if overrides.file and not overrides.file.exists():
            self.errors.append(f"Specified file does not exist: {overrides.file}")

        if overrides.files:
            for file_path in overrides.files:
                if not file_path.exists():
                    self.errors.append(f"Specified file does not exist: {file_path}")

        if overrides.directory and not overrides.directory.exists():
            self.errors.append(f"Specified directory does not exist: {overrides.directory}")
        elif overrides.directory and not overrides.directory.is_dir():
            self.errors.append(f"Specified path is not a directory: {overrides.directory}")

        # Validate error types
        if overrides.error_type:
            # Basic validation - could be enhanced with actual error code validation
            if not overrides.error_type.isalnum():
                self.warnings.append(f"Error type '{overrides.error_type}' may not be valid")

        # Validate ignore patterns
        if overrides.ignore:
            for error_code in overrides.ignore:
                if not error_code.isalnum():
                    self.warnings.append(f"Ignore error code '{error_code}' may not be valid")

        # Report results
        if self.warnings:
            for warning in self.warnings:
                console.print(f"[yellow]Warning: {warning}[/yellow]")

        if self.errors:
            for error in self.errors:
                console.print(f"[red]Error: {error}[/red]")
            return False

        return True
