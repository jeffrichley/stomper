"""Configuration loading and management for Stomper."""

import os
from pathlib import Path
import tomllib
from typing import Any

from rich.console import Console

from stomper.config.models import ConfigOverride, StomperConfig

console = Console()


class ConfigLoader:
    """Loads and manages Stomper configuration."""

    def __init__(self, project_root: Path | None = None):
        """Initialize config loader.

        Args:
            project_root: Root directory of the project. If None, uses current directory.
        """
        self.project_root = project_root or Path.cwd()
        self._config: StomperConfig | None = None

    def load_config(self) -> StomperConfig:
        """Load configuration from pyproject.toml and environment variables.

        Returns:
            StomperConfig: Loaded configuration with defaults and overrides applied.
        """
        if self._config is not None:
            return self._config

        # Start with defaults
        config_data = self._get_default_config()

        # Load from pyproject.toml
        pyproject_config = self._load_pyproject_config()
        if pyproject_config:
            config_data.update(pyproject_config)

        # Apply environment variable overrides
        env_overrides = self._load_env_overrides()
        if env_overrides:
            config_data.update(env_overrides)

        # Create and validate configuration
        try:
            self._config = StomperConfig(**config_data)
        except Exception as e:
            console.print(f"[red]Configuration error: {e}[/red]")
            raise

        return self._config

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration values."""
        return {
            "quality_tools": ["ruff", "mypy"],
            "ai_agent": "cursor-cli",
            "max_retries": 3,
            "parallel_files": 1,
            "ignores": {"files": [], "errors": []},
            "files": {
                "include": ["src/**/*.py", "tests/**/*.py"],
                "exclude": ["**/migrations/**", "**/legacy/**"],
                "max_files_per_run": 100,
                "parallel_processing": True,
            },
            "git": {"branch_prefix": "stomper", "commit_style": "conventional"},
        }

    def _load_pyproject_config(self) -> dict[str, Any] | None:
        """Load configuration from pyproject.toml."""
        pyproject_path = self.project_root / "pyproject.toml"

        if not pyproject_path.exists():
            return None

        try:
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)

            # Extract stomper configuration
            stomper_config = pyproject_data.get("tool", {}).get("stomper", {})
            if not stomper_config:
                return None

            # Flatten nested configuration
            config = {}
            for key, value in stomper_config.items():
                if key in ["ignores", "git"]:
                    config[key] = value
                else:
                    config[key] = value

            return config

        except Exception as e:
            console.print(f"[yellow]Warning: Could not load pyproject.toml: {e}[/yellow]")
            return None

    def _load_env_overrides(self) -> dict[str, Any]:
        """Load configuration overrides from environment variables."""
        overrides = {}

        # Quality tools
        if tools := os.getenv("STOMPER_QUALITY_TOOLS"):
            overrides["quality_tools"] = [t.strip() for t in tools.split(",")]

        # AI agent
        if agent := os.getenv("STOMPER_AI_AGENT"):
            overrides["ai_agent"] = agent

        # Max retries
        if retries := os.getenv("STOMPER_MAX_RETRIES"):
            try:
                overrides["max_retries"] = int(retries)
            except ValueError:
                console.print(
                    f"[yellow]Warning: Invalid STOMPER_MAX_RETRIES value: {retries}[/yellow]"
                )

        # Parallel files
        if parallel := os.getenv("STOMPER_PARALLEL_FILES"):
            try:
                overrides["parallel_files"] = int(parallel)
            except ValueError:
                console.print(
                    f"[yellow]Warning: Invalid STOMPER_PARALLEL_FILES value: {parallel}[/yellow]"
                )

        # Ignore files
        if ignore_files := os.getenv("STOMPER_IGNORE_FILES"):
            overrides.setdefault("ignores", {})["files"] = [
                f.strip() for f in ignore_files.split(",")
            ]

        # Ignore errors
        if ignore_errors := os.getenv("STOMPER_IGNORE_ERRORS"):
            overrides.setdefault("ignores", {})["errors"] = [
                e.strip() for e in ignore_errors.split(",")
            ]

        # File discovery configuration
        if include_patterns := os.getenv("STOMPER_INCLUDE_PATTERNS"):
            overrides.setdefault("files", {})["include"] = [
                p.strip() for p in include_patterns.split(",")
            ]

        if exclude_patterns := os.getenv("STOMPER_EXCLUDE_PATTERNS"):
            overrides.setdefault("files", {})["exclude"] = [
                p.strip() for p in exclude_patterns.split(",")
            ]

        if max_files := os.getenv("STOMPER_MAX_FILES"):
            try:
                overrides.setdefault("files", {})["max_files_per_run"] = int(max_files)
            except ValueError:
                console.print(
                    f"[yellow]Warning: Invalid STOMPER_MAX_FILES value: {max_files}[/yellow]"
                )

        if parallel_processing := os.getenv("STOMPER_PARALLEL_PROCESSING"):
            overrides.setdefault("files", {})["parallel_processing"] = (
                parallel_processing.lower() in ("true", "1", "yes")
            )

        # Git configuration
        if branch_prefix := os.getenv("STOMPER_BRANCH_PREFIX"):
            overrides.setdefault("git", {})["branch_prefix"] = branch_prefix

        if commit_style := os.getenv("STOMPER_COMMIT_STYLE"):
            overrides.setdefault("git", {})["commit_style"] = commit_style

        return overrides

    def apply_cli_overrides(self, overrides: ConfigOverride) -> StomperConfig:
        """Apply CLI argument overrides to the loaded configuration.

        Args:
            overrides: CLI argument overrides to apply.

        Returns:
            StomperConfig: Configuration with CLI overrides applied.
        """
        if self._config is None:
            self._config = self.load_config()

        # Create a copy of the current config
        config_dict = self._config.model_dump()

        # Apply CLI overrides
        if overrides.ruff is not None:
            if overrides.ruff and "ruff" not in config_dict["quality_tools"]:
                config_dict["quality_tools"].append("ruff")
            elif not overrides.ruff and "ruff" in config_dict["quality_tools"]:
                config_dict["quality_tools"].remove("ruff")

        if overrides.mypy is not None:
            if overrides.mypy and "mypy" not in config_dict["quality_tools"]:
                config_dict["quality_tools"].append("mypy")
            elif not overrides.mypy and "mypy" in config_dict["quality_tools"]:
                config_dict["quality_tools"].remove("mypy")

        if overrides.drill_sergeant is not None:
            if overrides.drill_sergeant and "drill-sergeant" not in config_dict["quality_tools"]:
                config_dict["quality_tools"].append("drill-sergeant")
            elif not overrides.drill_sergeant and "drill-sergeant" in config_dict["quality_tools"]:
                config_dict["quality_tools"].remove("drill-sergeant")

        # Create new configuration with overrides
        try:
            return StomperConfig(**config_dict)
        except Exception as e:
            console.print(f"[red]Configuration error after CLI overrides: {e}[/red]")
            raise

    def get_config(self) -> StomperConfig:
        """Get the current configuration.

        Returns:
            StomperConfig: Current configuration.
        """
        if self._config is None:
            return self.load_config()
        return self._config
