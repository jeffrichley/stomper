"""CLI data models for Stomper."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class FixOptions(BaseModel):
    """Options for the fix command."""

    # Quality tool flags
    ruff: bool = Field(default=True, description="Enable Ruff linting")
    mypy: bool = Field(default=True, description="Enable MyPy type checking")
    drill_sergeant: bool = Field(default=False, description="Enable Drill Sergeant")

    # File selection
    file: Path | None = Field(default=None, description="Specific file to process")
    files: list[Path] | None = Field(default=None, description="Multiple files to process")

    # Error filtering
    error_type: str | None = Field(default=None, description="Specific error types to fix")
    ignore: list[str] | None = Field(default=None, description="Error codes to ignore")

    # Processing options
    max_errors: int = Field(default=100, description="Maximum errors to fix per iteration")
    dry_run: bool = Field(default=False, description="Show what would be fixed without changes")
    verbose: bool = Field(default=False, description="Verbose output")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class QualityTool(BaseModel):
    """Configuration for a quality tool."""

    name: str = Field(description="Tool name")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    command: str = Field(description="Command to execute")
    args: list[str] = Field(default_factory=list, description="Additional arguments")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ProcessingStats(BaseModel):
    """Statistics for processing session."""

    total_files: int = Field(default=0, description="Total files processed")
    total_errors: int = Field(default=0, description="Total errors found")
    fixed_errors: int = Field(default=0, description="Errors successfully fixed")
    failed_fixes: int = Field(default=0, description="Failed fix attempts")
    skipped_errors: int = Field(default=0, description="Errors skipped")

    @property
    def success_rate(self) -> float:
        """Calculate success rate of fixes."""
        if self.total_errors == 0:
            return 0.0
        return (self.fixed_errors / self.total_errors) * 100
