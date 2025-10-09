"""Data models for error mapping and learning system."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PromptStrategy(str, Enum):
    """Prompt strategy types."""

    NORMAL = "normal"
    DETAILED = "detailed"
    VERBOSE = "verbose"
    MINIMAL = "minimal"


class FixOutcome(str, Enum):
    """Outcome of a fix attempt."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class ErrorAttempt(BaseModel):
    """Record of a single fix attempt."""

    error_code: str = Field(description="Error code (e.g., E501, F401)")
    tool: str = Field(description="Quality tool that reported error")
    outcome: FixOutcome = Field(description="Outcome of fix attempt")
    strategy: PromptStrategy = Field(description="Prompt strategy used")
    timestamp: datetime = Field(default_factory=datetime.now, description="When attempt occurred")
    file_path: str | None = Field(default=None, description="File that was fixed")

    model_config = {"use_enum_values": True}


class ErrorPattern(BaseModel):
    """Pattern tracking for a specific error code."""

    error_code: str = Field(description="Error code")
    tool: str = Field(description="Tool name")
    total_attempts: int = Field(default=0, description="Total fix attempts")
    successes: int = Field(default=0, description="Successful fixes")
    failures: int = Field(default=0, description="Failed fixes")
    attempts: list[ErrorAttempt] = Field(default_factory=list, description="History of attempts")
    successful_strategies: list[PromptStrategy] = Field(
        default_factory=list, description="Strategies that succeeded"
    )
    failed_strategies: list[PromptStrategy] = Field(
        default_factory=list, description="Strategies that failed"
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successes / self.total_attempts) * 100

    @property
    def is_difficult(self) -> bool:
        """Check if this error is difficult (low success rate)."""
        return self.success_rate < 50.0 and self.total_attempts >= 3


class AdaptiveStrategy(BaseModel):
    """Adaptive prompting strategy based on historical data."""

    verbosity: PromptStrategy = Field(description="Verbosity level")
    include_examples: bool = Field(default=False, description="Include code examples")
    include_history: bool = Field(default=False, description="Include historical context")
    retry_count: int = Field(default=0, description="Number of retries for this error")
    suggested_approach: str | None = Field(default=None, description="Suggested fix approach")


class LearningData(BaseModel):
    """Complete learning data structure."""

    version: str = Field(default="1.0.0", description="Data format version")
    patterns: dict[str, ErrorPattern] = Field(
        default_factory=dict, description="Error patterns keyed by error_code"
    )
    total_attempts: int = Field(default=0, description="Total attempts across all errors")
    total_successes: int = Field(default=0, description="Total successes across all errors")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update time")

    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_attempts == 0:
            return 0.0
        return (self.total_successes / self.total_attempts) * 100
