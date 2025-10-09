"""Configuration data models for Stomper."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IgnoreConfig(BaseModel):
    """Configuration for ignoring files and errors."""

    files: list[str] = Field(default_factory=list, description="File patterns to ignore")
    errors: list[str] = Field(default_factory=list, description="Error codes to ignore")

    model_config = ConfigDict(extra="forbid")


class FilesConfig(BaseModel):
    """Configuration for file discovery and filtering."""

    include: list[str] = Field(
        default_factory=lambda: ["src/**/*.py", "tests/**/*.py"],
        description="Include patterns for file discovery",
    )
    exclude: list[str] = Field(
        default_factory=lambda: ["**/migrations/**", "**/legacy/**"],
        description="Exclude patterns for file discovery",
    )
    max_files_per_run: int = Field(
        default=100, ge=1, description="Maximum files to process per run"
    )
    parallel_processing: bool = Field(default=True, description="Enable parallel file processing")

    model_config = ConfigDict(extra="forbid")


class GitConfig(BaseModel):
    """Configuration for Git integration."""

    branch_prefix: str = Field(default="stomper", description="Prefix for auto-generated branches")
    commit_style: str = Field(default="conventional", description="Commit message style")

    model_config = ConfigDict(extra="forbid")


class WorkflowConfig(BaseModel):
    """Workflow execution configuration."""

    use_sandbox: bool = Field(
        default=True, description="Use git worktree sandbox for isolated execution"
    )
    run_tests: bool = Field(
        default=True, description="Run tests after fixes to validate no regressions"
    )
    max_retries: int = Field(default=3, ge=1, description="Maximum retry attempts per file")
    processing_strategy: str = Field(
        default="batch_errors",
        description="Processing strategy: batch_errors, one_error_type, all_errors",
    )
    agent_name: str = Field(default="cursor-cli", description="AI agent to use")

    # Per-file worktree architecture settings (NEW)
    test_validation: Literal["full", "quick", "final", "none"] = Field(
        default="full",
        description="Test validation mode: full=all tests per file, quick=affected tests, final=once at end, none=skip"
    )
    files_per_worktree: int = Field(
        default=1,
        ge=1,
        description="Files per worktree (1=per-file isolation, >1=batched)"
    )
    continue_on_error: bool = Field(
        default=True,
        description="Continue processing other files after a file fails"
    )

    # Parallel processing settings (Phase 2)
    max_parallel_files: int = Field(
        default=4,  # Good default: conservative but parallel
        ge=1,
        le=32,  # Increased limit for powerful machines
        description="Maximum files to process in parallel (1=sequential, 4=good balance, 0=auto-detect CPUs)"
    )

    model_config = ConfigDict(extra="forbid")


class StomperConfig(BaseModel):
    """Main configuration for Stomper."""

    # Quality tools
    quality_tools: list[Literal["ruff", "mypy", "drill-sergeant", "pytest"]] = Field(
        default=["ruff", "mypy"], description="Quality tools to run"
    )
    ai_agent: Literal["cursor-cli"] = Field(
        default="cursor-cli", description="AI agent to use for fixing"
    )

    # Processing options
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts for failed fixes")
    parallel_files: int = Field(
        default=1, ge=1, description="Number of files to process in parallel"
    )

    # Configuration sections
    ignores: IgnoreConfig = Field(default_factory=IgnoreConfig, description="Ignore configuration")
    files: FilesConfig = Field(
        default_factory=FilesConfig, description="File discovery configuration"
    )
    git: GitConfig = Field(default_factory=GitConfig, description="Git configuration")
    workflow: WorkflowConfig = Field(
        default_factory=WorkflowConfig, description="Workflow configuration"
    )

    model_config = ConfigDict(extra="forbid")


class ConfigOverride(BaseModel):
    """Configuration overrides from CLI arguments."""

    # Quality tool overrides
    ruff: bool | None = None
    mypy: bool | None = None
    drill_sergeant: bool | None = None

    # File selection overrides
    file: Path | None = None
    files: list[Path] | None = None
    directory: Path | None = None

    # Error filtering overrides
    error_type: str | None = None
    ignore: list[str] | None = None

    # Processing overrides
    max_errors: int | None = Field(
        default=None, ge=1, description="Maximum errors to fix per iteration"
    )
    dry_run: bool | None = None
    verbose: bool | None = None

    # Workflow overrides
    use_sandbox: bool | None = None
    run_tests: bool | None = None
    max_retries: int | None = Field(default=None, ge=1, description="Maximum retry attempts")
    processing_strategy: str | None = None
    agent_name: str | None = None

    # Per-file worktree architecture overrides (NEW)
    test_validation: Literal["full", "quick", "final", "none"] | None = None
    continue_on_error: bool | None = None

    # Parallel processing overrides (Phase 2)
    max_parallel_files: int | None = Field(default=None, ge=1, le=32, description="Max parallel files")

    model_config = ConfigDict(arbitrary_types_allowed=True)
