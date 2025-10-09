"""LangGraph state definitions for Stomper workflow."""

from enum import Enum
from operator import add
from pathlib import Path
from typing import Annotated, TypedDict

from pydantic import BaseModel


class ProcessingStatus(str, Enum):
    """Status of file processing."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class ErrorInfo(BaseModel):
    """Information about a quality error."""

    tool: str
    code: str
    message: str
    file_path: Path
    line_number: int
    column: int | None = None
    severity: str = "error"
    auto_fixable: bool = False


class FileState(BaseModel):
    """State of a single file being processed."""

    file_path: Path
    status: ProcessingStatus = ProcessingStatus.PENDING
    errors: list[ErrorInfo] = []
    fixed_errors: list[ErrorInfo] = []
    attempts: int = 0
    max_attempts: int = 3
    last_error: str | None = None
    backup_path: Path | None = None


class TestValidation(str, Enum):
    """Test validation mode."""

    FULL = "full"  # Full suite after each file (safest, slowest)
    QUICK = "quick"  # Affected tests only (faster, less safe)
    FINAL = "final"  # Once at session end (fastest, risky)
    NONE = "none"  # Skip tests (dangerous)


class StomperState(TypedDict, total=False):
    """Complete state for Stomper workflow."""

    # Session info
    session_id: str
    branch_name: str
    sandbox_path: Path | None
    project_root: Path

    # Configuration
    enabled_tools: list[str]
    processing_strategy: str
    max_errors_per_iteration: int
    run_tests: bool
    use_sandbox: bool
    test_validation: str  # TestValidation mode
    continue_on_error: bool  # Continue processing other files on error

    # Current processing state
    files: list[FileState]  # Queue of files to process (for fan-out)

    # Per-file processing state (for parallel branches)
    current_file: FileState | None  # Current file being processed (in parallel branch)
    current_prompt: str  # Generated prompt for current file
    current_diff: str | None  # Extracted diff from current worktree
    current_worktree_id: str | None  # ID of current worktree

    # Results (with Annotated reducers for parallel processing support!)
    # Annotated[list, add] tells LangGraph to concatenate results from parallel branches
    successful_fixes: Annotated[list[str], add]  # Auto-concatenate from parallel files
    failed_fixes: Annotated[list[str], add]  # Auto-concatenate from parallel files
    total_errors_fixed: Annotated[int, lambda x, y: x + y]  # Auto-sum from parallel files

    # Control flow
    should_continue: bool
    status: ProcessingStatus
    error_message: str | None

    # Components (not serialized)
    agent_manager: object  # AgentManager instance
    prompt_generator: object  # PromptGenerator instance
    mapper: object  # ErrorMapper instance
