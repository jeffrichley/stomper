# Task 5: Error Mapping and Learning System - Implementation Plan

> **Status:** Planning Complete - Ready for Implementation  
> **Created:** 2025-01-08  
> **Task Reference:** `.agent-os/specs/2024-09-25-week2-ai-agent-integration/tasks.md#L42`

## 📋 Overview

Implement an intelligent error mapping and learning system that tracks fix success patterns, calculates error-specific success rates, adapts prompting strategies based on historical data, and provides fallback strategy selection for improved fix outcomes over time.

## 🎯 Success Criteria

When complete, the system will:
- ✅ Track error patterns and fix attempts per error code
- ✅ Calculate and persist success rates per error type
- ✅ Adapt prompt generation based on historical success data
- ✅ Automatically select fallback strategies for difficult errors
- ✅ Store learning data persistently across sessions
- ✅ Achieve measurable improvement in fix success rate over time
- ✅ Provide statistics and insights via CLI/logging

## 🏗️ Architecture

### Component Structure

```
src/stomper/ai/
├── mapper.py              # NEW: Core error mapping and learning logic
└── models.py              # NEW: Data models for tracking

{project_root}/.stomper/   # NEW: Hidden directory in MAIN project (not sandbox!)
└── learning_data.json     # Persistent storage of error patterns (per-project)

tests/unit/
└── test_mapper.py         # NEW: Comprehensive mapper tests
```

**⚠️ CRITICAL: Storage Location**

Learning data is stored in the **MAIN PROJECT ROOT**, not in ephemeral sandbox worktrees:

- ✅ **Correct:** `{main_project_root}/.stomper/learning_data.json`
- ❌ **Wrong:** `{sandbox_path}/.stomper/learning_data.json` (would be lost on cleanup!)

This ensures:
- Learning persists across sandbox runs
- Project-specific patterns (not mixed with other projects)
- Survives sandbox cleanup
- Git-ignored (add `.stomper/` to `.gitignore`)

### Integration Points

```
┌─────────────────┐
│ PromptGenerator │ ───> Uses mapper for adaptive strategies
└─────────────────┘

┌─────────────────┐
│  AgentManager   │ ───> Uses mapper for fallback selection
└─────────────────┘

┌─────────────────┐
│  FixValidator   │ ───> Reports outcomes to mapper
└─────────────────┘

┌─────────────────┐
│     Mapper      │ ───> Persists to .stomper/learning_data.json
└─────────────────┘
```

---

## 📝 Task Breakdown

### Task 5.1: Write Tests for Mapper Class ✅ TDD

**Estimated Time:** 2-3 hours

**Test File:** `tests/unit/test_mapper.py`

**Test Categories:**

#### 1. Initialization Tests
```python
@pytest.mark.unit
class TestErrorMapperInitialization:
    """Test ErrorMapper initialization."""
    
    def test_creates_with_default_storage_path(self, tmp_path):
        """Test mapper initializes with default storage path in project root."""
        # Should create {project_root}/.stomper/learning_data.json by default
        mapper = ErrorMapper(project_root=tmp_path)
        assert mapper.storage_path == tmp_path / ".stomper" / "learning_data.json"
        assert mapper.project_root == tmp_path.resolve()
    
    def test_creates_with_custom_storage_path(self, tmp_path):
        """Test mapper accepts custom storage path."""
        custom_path = tmp_path / "custom" / "data.json"
        mapper = ErrorMapper(project_root=tmp_path, storage_path=custom_path)
        assert mapper.storage_path == custom_path
    
    def test_loads_existing_data_on_init(self, tmp_path):
        """Test mapper loads historical data if file exists."""
        # Create existing data file
        # Verify it's loaded on init
    
    def test_creates_empty_data_when_no_file_exists(self, tmp_path):
        """Test mapper initializes empty data structure."""
        mapper = ErrorMapper(project_root=tmp_path)
        assert mapper.data.total_attempts == 0
        assert len(mapper.data.patterns) == 0
    
    def test_handles_corrupted_data_file_gracefully(self, tmp_path):
        """Test mapper handles invalid JSON gracefully."""
        # Create corrupted file
        # Verify mapper starts fresh instead of crashing
    
    def test_storage_in_main_project_not_sandbox(self, tmp_path):
        """Test that storage is in main project root, not sandbox."""
        # CRITICAL: Ensure this works with sandbox workflow
        main_project = tmp_path / "main"
        sandbox_path = tmp_path / "sandbox"
        main_project.mkdir()
        sandbox_path.mkdir()
        
        # Mapper should use main project, not sandbox
        mapper = ErrorMapper(project_root=main_project)
        assert mapper.storage_path.is_relative_to(main_project)
        assert not mapper.storage_path.is_relative_to(sandbox_path)
```

#### 2. Error Pattern Tracking Tests
```python
@pytest.mark.unit
class TestErrorPatternTracking:
    """Test error pattern tracking functionality."""
    
    def test_records_error_attempt(self):
        """Test recording a single error fix attempt."""
    
    def test_records_multiple_attempts_for_same_error(self):
        """Test accumulating multiple attempts for same error code."""
    
    def test_groups_by_error_code(self):
        """Test errors grouped by code (E501, F401, etc.)."""
    
    def test_groups_by_tool(self):
        """Test errors can be grouped by tool (ruff, mypy)."""
    
    def test_records_success_outcome(self):
        """Test recording successful fix outcome."""
    
    def test_records_failure_outcome(self):
        """Test recording failed fix outcome."""
    
    def test_tracks_strategy_used(self):
        """Test recording which prompt strategy was used."""
    
    def test_tracks_timestamp(self):
        """Test attempts include timestamp for trend analysis."""
```

#### 3. Success Rate Calculation Tests
```python
@pytest.mark.unit
class TestSuccessRateCalculation:
    """Test success rate calculation."""
    
    def test_calculates_success_rate_for_error_code(self):
        """Test success rate calculation per error code."""
    
    def test_handles_zero_attempts(self):
        """Test success rate returns 0.0 for zero attempts."""
    
    def test_handles_all_successes(self):
        """Test success rate returns 1.0 for all successes."""
    
    def test_handles_all_failures(self):
        """Test success rate returns 0.0 for all failures."""
    
    def test_calculates_partial_success_rate(self):
        """Test success rate for mixed outcomes."""
    
    def test_calculates_overall_success_rate(self):
        """Test overall success rate across all errors."""
    
    def test_calculates_per_tool_success_rate(self):
        """Test success rate grouped by tool."""
```

#### 4. Adaptive Prompting Tests
```python
@pytest.mark.unit
class TestAdaptivePrompting:
    """Test adaptive prompting strategy selection."""
    
    def test_returns_detailed_strategy_for_low_success_rate(self):
        """Test returns detailed prompting for difficult errors."""
    
    def test_returns_normal_strategy_for_high_success_rate(self):
        """Test returns normal prompting for easy errors."""
    
    def test_includes_successful_patterns_in_strategy(self):
        """Test strategy includes historically successful patterns."""
    
    def test_excludes_failed_patterns_from_strategy(self):
        """Test strategy avoids historically failed patterns."""
    
    def test_handles_new_error_code_with_no_history(self):
        """Test default strategy for never-seen error codes."""
    
    def test_adapts_context_based_on_history(self):
        """Test context adaptation based on historical data."""
```

#### 5. Fallback Strategy Tests
```python
@pytest.mark.unit
class TestFallbackStrategySelection:
    """Test fallback strategy selection."""
    
    def test_suggests_alternative_strategy_after_failure(self):
        """Test suggests different strategy after failed attempt."""
    
    def test_escalates_verbosity_on_retry(self):
        """Test increases prompt detail level on retry."""
    
    def test_tries_different_approaches_sequentially(self):
        """Test cycles through different fix approaches."""
    
    def test_avoids_repeating_failed_strategy(self):
        """Test doesn't repeat same failed approach."""
    
    def test_limits_fallback_attempts(self):
        """Test limits maximum fallback iterations."""
```

#### 6. Data Persistence Tests
```python
@pytest.mark.unit
class TestDataPersistence:
    """Test data persistence functionality."""
    
    def test_saves_data_to_json_file(self):
        """Test data saved to JSON file."""
    
    def test_loads_data_from_json_file(self):
        """Test data loaded from JSON file."""
    
    def test_auto_saves_after_recording_attempt(self):
        """Test auto-save after each attempt (or configurable)."""
    
    def test_handles_file_write_errors_gracefully(self):
        """Test handles I/O errors gracefully."""
    
    def test_creates_directory_if_not_exists(self):
        """Test creates .stomper directory if needed."""
    
    def test_preserves_existing_data_on_load(self):
        """Test doesn't lose data when loading."""
```

#### 7. Statistics and Reporting Tests
```python
@pytest.mark.unit
class TestStatisticsReporting:
    """Test statistics and reporting functionality."""
    
    def test_generates_summary_statistics(self):
        """Test generates summary stats for all errors."""
    
    def test_identifies_most_problematic_errors(self):
        """Test identifies errors with lowest success rates."""
    
    def test_identifies_most_successful_strategies(self):
        """Test identifies best-performing strategies."""
    
    def test_calculates_improvement_trends(self):
        """Test tracks improvement over time."""
    
    def test_formats_statistics_for_display(self):
        """Test formats stats for rich console output."""
```

---

### Task 5.2: Implement Error Pattern Tracking

**Estimated Time:** 3-4 hours

**Files to Create:**
1. `src/stomper/ai/models.py` - Data models
2. `src/stomper/ai/mapper.py` - Core mapper class

#### Step 1: Create Data Models (`models.py`)

```python
"""Data models for error mapping and learning system."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

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
```

#### Step 2: Create Mapper Class (`mapper.py`)

```python
"""Error mapping and learning system for Stomper.

This module provides intelligent error pattern tracking, success rate calculation,
and adaptive prompting strategies based on historical fix outcomes.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console

from stomper.ai.models import (
    AdaptiveStrategy,
    ErrorAttempt,
    ErrorPattern,
    FixOutcome,
    LearningData,
    PromptStrategy,
)
from stomper.quality.base import QualityError

logger = logging.getLogger(__name__)
console = Console()


class ErrorMapper:
    """Maps error patterns to fix strategies and learns from outcomes."""
    
    DEFAULT_STORAGE_DIR = ".stomper"
    DEFAULT_STORAGE_FILE = "learning_data.json"
    
    def __init__(
        self,
        project_root: Path,
        storage_path: Path | None = None,
        auto_save: bool = True,
    ):
        """Initialize error mapper.
        
        Args:
            project_root: Main project root directory (NOT sandbox path!)
            storage_path: Override storage location (default: {project_root}/.stomper/learning_data.json)
            auto_save: Automatically save after each update
        
        Important:
            Always pass the MAIN project root, not the sandbox path.
            Learning data must persist across sandbox cleanup cycles.
        """
        self.project_root = Path(project_root).resolve()
        
        # Default storage in main project's .stomper directory
        if storage_path is None:
            storage_path = self.project_root / self.DEFAULT_STORAGE_DIR / self.DEFAULT_STORAGE_FILE
        
        self.storage_path = Path(storage_path)
        self.auto_save = auto_save
        self.data: LearningData = self._load_data()
        
        logger.info(f"ErrorMapper initialized with storage: {self.storage_path}")
    
    def record_attempt(
        self,
        error: QualityError,
        outcome: FixOutcome,
        strategy: PromptStrategy,
        file_path: Path | None = None,
    ) -> None:
        """Record a fix attempt for learning.
        
        Args:
            error: Quality error that was fixed
            outcome: Outcome of the fix attempt
            strategy: Prompt strategy that was used
            file_path: File that was fixed (optional)
        """
        error_code = error.code
        tool = error.tool
        
        # Get or create pattern
        pattern_key = f"{tool}:{error_code}"
        if pattern_key not in self.data.patterns:
            self.data.patterns[pattern_key] = ErrorPattern(
                error_code=error_code,
                tool=tool,
            )
        
        pattern = self.data.patterns[pattern_key]
        
        # Create attempt record
        attempt = ErrorAttempt(
            error_code=error_code,
            tool=tool,
            outcome=outcome,
            strategy=strategy,
            file_path=str(file_path) if file_path else None,
        )
        
        # Update pattern statistics
        pattern.attempts.append(attempt)
        pattern.total_attempts += 1
        
        if outcome == FixOutcome.SUCCESS:
            pattern.successes += 1
            if strategy not in pattern.successful_strategies:
                pattern.successful_strategies.append(strategy)
            self.data.total_successes += 1
        elif outcome == FixOutcome.FAILURE:
            pattern.failures += 1
            if strategy not in pattern.failed_strategies:
                pattern.failed_strategies.append(strategy)
        
        self.data.total_attempts += 1
        self.data.last_updated = datetime.now()
        
        logger.debug(
            f"Recorded {outcome} for {error_code} using {strategy} strategy "
            f"(success rate: {pattern.success_rate:.1f}%)"
        )
        
        if self.auto_save:
            self.save()
    
    def get_adaptive_strategy(
        self,
        error: QualityError,
        retry_count: int = 0,
    ) -> AdaptiveStrategy:
        """Get adaptive prompting strategy based on historical data.
        
        Args:
            error: Quality error to get strategy for
            retry_count: Number of previous retry attempts
        
        Returns:
            AdaptiveStrategy with recommended settings
        """
        pattern_key = f"{error.tool}:{error.code}"
        pattern = self.data.patterns.get(pattern_key)
        
        # No historical data - use normal strategy
        if pattern is None or pattern.total_attempts == 0:
            return AdaptiveStrategy(
                verbosity=PromptStrategy.NORMAL,
                include_examples=False,
                retry_count=retry_count,
            )
        
        # Difficult error - escalate verbosity
        if pattern.is_difficult:
            verbosity = self._escalate_verbosity(PromptStrategy.DETAILED, retry_count)
            return AdaptiveStrategy(
                verbosity=verbosity,
                include_examples=True,
                include_history=True,
                retry_count=retry_count,
                suggested_approach=self._get_successful_approach(pattern),
            )
        
        # Easy error - use minimal strategy
        if pattern.success_rate >= 80.0:
            return AdaptiveStrategy(
                verbosity=PromptStrategy.MINIMAL,
                include_examples=False,
                retry_count=retry_count,
            )
        
        # Medium difficulty - normal strategy
        return AdaptiveStrategy(
            verbosity=PromptStrategy.NORMAL,
            include_examples=pattern.success_rate < 60.0,
            retry_count=retry_count,
        )
    
    def get_fallback_strategy(
        self,
        error: QualityError,
        failed_strategies: list[PromptStrategy],
    ) -> PromptStrategy | None:
        """Get fallback strategy after failure.
        
        Args:
            error: Error that failed to fix
            failed_strategies: Strategies that have already failed
        
        Returns:
            Next strategy to try, or None if exhausted
        """
        pattern_key = f"{error.tool}:{error.code}"
        pattern = self.data.patterns.get(pattern_key)
        
        # Try successful strategies first
        if pattern and pattern.successful_strategies:
            for strategy in pattern.successful_strategies:
                if strategy not in failed_strategies:
                    logger.info(f"Using historically successful strategy: {strategy}")
                    return strategy
        
        # Escalate verbosity
        all_strategies = [
            PromptStrategy.MINIMAL,
            PromptStrategy.NORMAL,
            PromptStrategy.DETAILED,
            PromptStrategy.VERBOSE,
        ]
        
        for strategy in all_strategies:
            if strategy not in failed_strategies:
                return strategy
        
        # All strategies exhausted
        return None
    
    def get_success_rate(self, error_code: str, tool: str) -> float:
        """Get success rate for specific error code.
        
        Args:
            error_code: Error code to check
            tool: Tool name
        
        Returns:
            Success rate as percentage (0-100)
        """
        pattern_key = f"{tool}:{error_code}"
        pattern = self.data.patterns.get(pattern_key)
        
        if pattern is None:
            return 0.0
        
        return pattern.success_rate
    
    def get_statistics(self) -> dict[str, any]:
        """Get comprehensive statistics about error patterns.
        
        Returns:
            Dictionary with statistics
        """
        # Overall stats
        stats = {
            "overall_success_rate": self.data.overall_success_rate,
            "total_attempts": self.data.total_attempts,
            "total_successes": self.data.total_successes,
            "total_patterns": len(self.data.patterns),
            "last_updated": self.data.last_updated.isoformat(),
        }
        
        # Most problematic errors
        difficult_errors = [
            {
                "code": pattern.error_code,
                "tool": pattern.tool,
                "success_rate": pattern.success_rate,
                "attempts": pattern.total_attempts,
            }
            for pattern in self.data.patterns.values()
            if pattern.is_difficult
        ]
        
        stats["difficult_errors"] = sorted(
            difficult_errors,
            key=lambda x: x["success_rate"],
        )[:5]  # Top 5 most difficult
        
        # Most successful errors
        easy_errors = [
            {
                "code": pattern.error_code,
                "tool": pattern.tool,
                "success_rate": pattern.success_rate,
                "attempts": pattern.total_attempts,
            }
            for pattern in self.data.patterns.values()
            if pattern.total_attempts >= 3 and pattern.success_rate >= 80.0
        ]
        
        stats["easy_errors"] = sorted(
            easy_errors,
            key=lambda x: x["success_rate"],
            reverse=True,
        )[:5]  # Top 5 easiest
        
        return stats
    
    def save(self) -> None:
        """Save learning data to file."""
        try:
            # Create directory if needed
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict and save
            data_dict = self.data.model_dump(mode="json")
            
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data_dict, f, indent=2, default=str)
            
            logger.debug(f"Saved learning data to {self.storage_path}")
        
        except Exception as e:
            logger.error(f"Failed to save learning data: {e}")
            # Don't raise - saving is non-critical
    
    def _load_data(self) -> LearningData:
        """Load learning data from file.
        
        Returns:
            LearningData instance (empty if file doesn't exist)
        """
        if not self.storage_path.exists():
            logger.debug("No existing learning data, starting fresh")
            return LearningData()
        
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data_dict = json.load(f)
            
            # Convert back to models
            data = LearningData(**data_dict)
            logger.info(
                f"Loaded learning data: {len(data.patterns)} patterns, "
                f"{data.total_attempts} attempts, "
                f"{data.overall_success_rate:.1f}% success rate"
            )
            return data
        
        except Exception as e:
            logger.warning(f"Failed to load learning data: {e}, starting fresh")
            return LearningData()
    
    def _escalate_verbosity(
        self,
        base_verbosity: PromptStrategy,
        retry_count: int,
    ) -> PromptStrategy:
        """Escalate verbosity based on retry count.
        
        Args:
            base_verbosity: Base verbosity level
            retry_count: Number of retries
        
        Returns:
            Escalated verbosity level
        """
        escalation_map = {
            0: PromptStrategy.NORMAL,
            1: PromptStrategy.DETAILED,
            2: PromptStrategy.VERBOSE,
        }
        
        return escalation_map.get(retry_count, PromptStrategy.VERBOSE)
    
    def _get_successful_approach(self, pattern: ErrorPattern) -> str | None:
        """Extract common successful approach from pattern.
        
        Args:
            pattern: Error pattern with history
        
        Returns:
            Description of successful approach, or None
        """
        if not pattern.successful_strategies:
            return None
        
        # Simple heuristic: most common successful strategy
        most_common = max(
            set(pattern.successful_strategies),
            key=pattern.successful_strategies.count,
        )
        
        return f"Use {most_common.value} approach (historically successful)"
```

---

### Task 5.3: Add Success Rate Calculation

**Estimated Time:** 1-2 hours

**Already implemented in models!** ✅

Success rate calculation is built into the `ErrorPattern` model:

```python
@property
def success_rate(self) -> float:
    """Calculate success rate as percentage."""
    if self.total_attempts == 0:
        return 0.0
    return (self.successes / self.total_attempts) * 100
```

**Additional work needed:**
- Add per-tool success rate aggregation
- Add time-based trend analysis (optional enhancement)

---

### Task 5.4: Implement Adaptive Prompting

**Estimated Time:** 2-3 hours

**Integration:** Modify `PromptGenerator` to use `ErrorMapper`

```python
# src/stomper/ai/prompt_generator.py

class PromptGenerator:
    """Generates prompts for AI agents based on quality errors and code context."""
    
    def __init__(
        self,
        template_dir: str = "templates",
        errors_dir: str = "errors",
        project_root: Path | None = None,  # NEW
        mapper: ErrorMapper | None = None,  # NEW
    ):
        """Initialize the PromptGenerator.
        
        Args:
            template_dir: Directory containing Jinja2 templates
            errors_dir: Directory containing error mapping files
            project_root: Main project root (for mapper initialization)
            mapper: Error mapper for adaptive strategies (optional, created if not provided)
        """
        self.template_dir = Path(template_dir)
        self.errors_dir = Path(errors_dir)
        
        # Create mapper if not provided (requires project_root)
        if mapper is None:
            if project_root is None:
                raise ValueError("Either 'mapper' or 'project_root' must be provided")
            self.mapper = ErrorMapper(project_root=project_root)
        else:
            self.mapper = mapper
        
        # Initialize Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(template_dir))
    
    def generate_prompt(
        self,
        errors: list[QualityError],
        code_context: str,
        retry_count: int = 0,  # NEW
    ) -> str:
        """Generate a prompt for AI agents based on errors and code context.
        
        Args:
            errors: List of quality errors to fix
            code_context: Surrounding code context
            retry_count: Number of retry attempts (for adaptive strategies)
        
        Returns:
            Generated prompt string
        """
        if not errors:
            logger.warning("No errors provided to PromptGenerator")
            return self._generate_empty_prompt()
        
        # Get adaptive strategy for primary error
        primary_error = errors[0]
        adaptive_strategy = self.mapper.get_adaptive_strategy(
            primary_error,
            retry_count=retry_count,
        )
        
        # Extract error context
        error_context = self._extract_error_context(errors)
        
        # Load error-specific advice (enhanced with adaptive strategy)
        error_advice = self._load_error_advice(errors, adaptive_strategy)
        
        # Process code context (adapt based on strategy)
        processed_code_context = self._process_code_context(
            code_context,
            adaptive_strategy,
        )
        
        # Add adaptive strategy context
        error_context["adaptive_strategy"] = {
            "verbosity": adaptive_strategy.verbosity.value,
            "retry_count": adaptive_strategy.retry_count,
            "suggested_approach": adaptive_strategy.suggested_approach,
        }
        
        # Generate prompt using template
        try:
            template = self.env.get_template("fix_prompt.j2")
            prompt = template.render(
                error_context=error_context,
                error_advice=error_advice,
                code_context=processed_code_context,
                adaptive_strategy=adaptive_strategy,  # NEW
            )
            
            return prompt
        
        except TemplateNotFound:
            logger.error(f"Template file not found in {self.template_dir}")
            raise FileNotFoundError(f"Template file not found in {self.template_dir}")
    
    def _load_error_advice(
        self,
        errors: list[QualityError],
        adaptive_strategy: AdaptiveStrategy,  # NEW
    ) -> dict[str, str]:
        """Load error-specific advice from mapping files.
        
        Args:
            errors: List of quality errors
            adaptive_strategy: Adaptive strategy for this fix
        
        Returns:
            Dictionary mapping error codes to advice
        """
        advice = {}
        
        for error in errors:
            error_code = error.code
            tool = error.tool
            
            # Try to load advice file
            advice_file = self._get_advice_file_path(tool, error_code)
            if advice_file and advice_file.exists():
                try:
                    base_advice = advice_file.read_text(encoding="utf-8")
                    
                    # Enhance advice with adaptive strategy
                    if adaptive_strategy.suggested_approach:
                        enhanced_advice = (
                            f"{base_advice}\n\n"
                            f"**Recommended Approach (based on history):**\n"
                            f"{adaptive_strategy.suggested_approach}"
                        )
                        advice[error_code] = enhanced_advice
                    else:
                        advice[error_code] = base_advice
                
                except Exception as e:
                    logger.warning(f"Failed to read advice file {advice_file}: {e}")
                    advice[error_code] = f"Fix {error_code}: {error.message}"
            else:
                # Fallback to generic advice
                advice[error_code] = f"Fix {error_code}: {error.message}"
        
        return advice
    
    def _process_code_context(
        self,
        code_context: str,
        adaptive_strategy: AdaptiveStrategy,  # NEW
    ) -> str:
        """Process code context for inclusion in prompts.
        
        Args:
            code_context: Raw code context
            adaptive_strategy: Strategy for this fix
        
        Returns:
            Processed code context
        """
        if not code_context or not code_context.strip():
            return "No code context available"
        
        # For detailed/verbose strategies, include more context
        if adaptive_strategy.verbosity in [PromptStrategy.DETAILED, PromptStrategy.VERBOSE]:
            # Return full context without truncation
            return code_context
        
        # For minimal strategy, could truncate (but keeping full for now)
        return code_context
```

---

### Task 5.5: Add Fallback Strategy Selection

**Estimated Time:** 2-3 hours

**Integration:** Enhance `AgentManager` and fix workflow

```python
# src/stomper/ai/agent_manager.py (additions)

class AgentManager:
    """Manager for AI agent selection, fallback, and coordination."""
    
    def __init__(
        self,
        project_root: Path | None = None,  # NEW
        mapper: ErrorMapper | None = None,  # MODIFIED
    ):
        """Initialize agent manager.
        
        Args:
            project_root: Main project root (for mapper initialization)
            mapper: Error mapper instance (optional, created if not provided)
        """
        self._agents: dict[str, AIAgent] = {}
        self._fallback_order: list[str] = []
        self._default_agent: str | None = None
        
        # Create mapper if not provided (requires project_root)
        if mapper is None:
            if project_root is None:
                raise ValueError("Either 'mapper' or 'project_root' must be provided")
            self.mapper = ErrorMapper(project_root=project_root)
        else:
            self.mapper = mapper
    
    def generate_fix_with_intelligent_fallback(  # NEW METHOD
        self,
        primary_agent_name: str,
        error: QualityError,
        error_context: dict[str, Any],
        code_context: str,
        prompt: str,
        max_retries: int = 3,
    ) -> str:
        """Generate fix with intelligent fallback based on error history.
        
        Args:
            primary_agent_name: Name of primary agent to try
            error: Quality error being fixed
            error_context: Error context
            code_context: Code context
            prompt: Fix prompt
            max_retries: Maximum retry attempts
        
        Returns:
            Generated fix from successful attempt
        
        Raises:
            RuntimeError: If all retries exhausted
        """
        failed_strategies = []
        
        for retry_count in range(max_retries):
            # Get adaptive strategy
            adaptive_strategy = self.mapper.get_adaptive_strategy(
                error,
                retry_count=retry_count,
            )
            
            # Try to get fallback strategy if we've failed
            if retry_count > 0:
                fallback_strategy = self.mapper.get_fallback_strategy(
                    error,
                    failed_strategies,
                )
                
                if fallback_strategy is None:
                    logger.warning("All fallback strategies exhausted")
                    break
                
                logger.info(
                    f"Retry #{retry_count}: Using fallback strategy {fallback_strategy}"
                )
            
            # Try to generate fix
            try:
                if primary_agent_name in self._agents:
                    agent = self._agents[primary_agent_name]
                    logger.info(
                        f"Attempting fix with {primary_agent_name} "
                        f"(strategy: {adaptive_strategy.verbosity})"
                    )
                    
                    result = agent.generate_fix(error_context, code_context, prompt)
                    
                    # Record success
                    self.mapper.record_attempt(
                        error,
                        FixOutcome.SUCCESS,
                        adaptive_strategy.verbosity,
                    )
                    
                    return result
            
            except Exception as e:
                logger.warning(
                    f"Attempt {retry_count + 1} failed with {primary_agent_name}: {e}"
                )
                
                # Record failure
                self.mapper.record_attempt(
                    error,
                    FixOutcome.FAILURE,
                    adaptive_strategy.verbosity,
                )
                
                failed_strategies.append(adaptive_strategy.verbosity)
        
        # All retries exhausted
        raise RuntimeError(
            f"All {max_retries} retry attempts failed for {error.code}"
        )
```

---

### Task 5.6: Verify All Tests Pass

**Estimated Time:** 1-2 hours

**Checklist:**

- [ ] All unit tests in `test_mapper.py` pass
- [ ] Integration tests with `PromptGenerator` pass
- [ ] Integration tests with `AgentManager` pass
- [ ] Integration tests with `FixValidator` pass
- [ ] No regressions in existing tests
- [ ] Test coverage ≥ 80% for new code
- [ ] No linting errors
- [ ] No type errors from mypy
- [ ] Documentation strings complete

**Test command:**
```bash
just test tests/unit/test_mapper.py
```

---

## 🔄 Integration with Existing Components

### 0. Sandbox Workflow Integration ⚠️ CRITICAL

**Correct Usage Pattern:**

```python
# In your main fix workflow (NOT in sandbox!)
from stomper.ai.mapper import ErrorMapper
from stomper.ai.sandbox_manager import SandboxManager

# Main project root (where your actual codebase lives)
main_project_root = Path("/path/to/your/project")

# Create mapper with MAIN project root
mapper = ErrorMapper(project_root=main_project_root)

# Create sandbox for AI agent to work in
sandbox_manager = SandboxManager(project_root=main_project_root)
sandbox_path, branch = sandbox_manager.create_sandbox()

# AI agent works in sandbox, mapper records outcomes
# Learning data saved to {main_project_root}/.stomper/learning_data.json

# After sandbox cleanup, learning data persists!
sandbox_manager.cleanup_sandbox(sandbox_path, branch)
```

**❌ WRONG - Don't Do This:**

```python
# DON'T create mapper with sandbox path!
mapper = ErrorMapper(project_root=sandbox_path)  # ❌ Data will be lost!
```

### 1. PromptGenerator Integration

**Changes needed:**
- Add `mapper` parameter to constructor
- Add `project_root` parameter (to pass to mapper)
- Pass `retry_count` to `generate_prompt()`
- Use adaptive strategies when loading advice
- Enhance prompts based on historical data

### 2. AgentManager Integration

**Changes needed:**
- Add `mapper` parameter to constructor
- Use `generate_fix_with_intelligent_fallback()` in workflows
- Record outcomes after each attempt
- Report learning statistics

### 3. FixValidator Integration

**Changes needed:**
- Report validation results to mapper
- Record success/failure outcomes
- Track which fixes worked vs. failed

### 4. CLI Integration

**Changes needed:**
- Display learning statistics in verbose mode
- Add `--show-stats` flag to show mapper statistics
- Log adaptive strategy decisions

---

## 📊 Success Metrics

### Quantitative Metrics

- **Test Coverage:** ≥ 80% for mapper module
- **Success Rate Improvement:** Track before/after fix success rates
- **Data Persistence:** No data loss across sessions
- **Performance:** < 50ms overhead per fix attempt

### Qualitative Metrics

- **Code Quality:** No linting/type errors
- **Documentation:** All public methods documented
- **Logging:** Rich console output for insights
- **Maintainability:** Clean, testable code following project conventions

---

## 🚀 Implementation Order

Follow this sequence for optimal TDD workflow:

1. ✅ **Write all tests first** (Task 5.1) - 2-3 hours
2. ✅ **Create data models** (`models.py`) - 1 hour
3. ✅ **Implement mapper core** (`mapper.py`) - 2-3 hours
4. ✅ **Run tests, iterate until green** - 1-2 hours
5. ✅ **Integrate with PromptGenerator** (Task 5.4) - 2-3 hours
6. ✅ **Integrate with AgentManager** (Task 5.5) - 2-3 hours
7. ✅ **Add CLI statistics display** - 1 hour
8. ✅ **Final testing and verification** (Task 5.6) - 1-2 hours

**Total Estimated Time:** 12-17 hours (2-3 days)

---

## 📝 Notes and Considerations

### Storage Location - CRITICAL ⚠️

**Always use the MAIN project root, never the sandbox path:**

```python
# ✅ CORRECT
main_project = Path("/home/user/myproject")
mapper = ErrorMapper(project_root=main_project)
# Stores to: /home/user/myproject/.stomper/learning_data.json

# ❌ WRONG - Will lose data when sandbox is cleaned up!
sandbox = Path("/tmp/stomper/sbx_abc123")
mapper = ErrorMapper(project_root=sandbox)
# Stores to: /tmp/stomper/sbx_abc123/.stomper/learning_data.json (EPHEMERAL!)
```

**Why this matters:**
- Sandboxes are ephemeral (created in `/tmp/stomper/`)
- Sandboxes are cleaned up after each run
- Learning data MUST persist to improve over time
- Project-specific patterns stay isolated

### .gitignore Configuration (Optional)

You can **optionally** add to your `.gitignore`:

```gitignore
# Stomper learning data (optional - can be committed if desired)
.stomper/
```

**Option A: Commit learning data (default)**
- ✅ Team shares learned patterns
- ✅ Consistent fix strategies across developers
- ✅ Faster learning on fresh clones
- ⚠️ May include environment-specific patterns

**Option B: Ignore learning data**
- ✅ Each developer learns independently
- ✅ No shared state in version control
- ⚠️ Slower learning on each machine
- ⚠️ Similar to `.venv/` or `__pycache__/`

**Recommendation:** Start by committing `.stomper/` to share learnings, then add to `.gitignore` if you notice environment-specific issues.

### Pydantic Configuration

Use `model_config = {"use_enum_values": True}` for enums to serialize cleanly to JSON.

### Rich Logging

Use Rich console for colorful, informative output:

```python
from rich.console import Console
from rich.table import Table

console = Console()

# Display statistics
table = Table(title="Error Mapping Statistics")
table.add_column("Error Code", style="cyan")
table.add_column("Success Rate", style="green")
table.add_column("Attempts", style="yellow")

for pattern in mapper.data.patterns.values():
    table.add_row(
        pattern.error_code,
        f"{pattern.success_rate:.1f}%",
        str(pattern.total_attempts),
    )

console.print(table)
```

### Avoid Magic Strings

All static values use enums (`PromptStrategy`, `FixOutcome`).

### Error Handling

- Gracefully handle missing/corrupted data files
- Log warnings but don't crash on save failures
- Continue operation even if mapper unavailable

### Future Enhancements (Phase 2)

- YAML-based configuration for strategies
- Machine learning for pattern recognition
- Multi-project learning (shared knowledge base)
- Web dashboard for visualization
- A/B testing of prompt strategies

---

## ✅ Acceptance Criteria

Task 5 is complete when:

- [ ] All tests in `test_mapper.py` pass (≥ 30 tests)
- [ ] `ErrorMapper` class tracks patterns and success rates
- [ ] Data persists across sessions in `{project_root}/.stomper/learning_data.json`
- [ ] Storage is in MAIN project root, not sandbox (verified by tests)
- [ ] Learning data survives sandbox cleanup cycles
- [ ] `.stomper/` git handling decided (commit or ignore - both valid)
- [ ] `PromptGenerator` uses adaptive strategies
- [ ] `AgentManager` uses intelligent fallback
- [ ] CLI displays learning statistics (with `--verbose` or `--show-stats`)
- [ ] No regressions in existing functionality
- [ ] Code follows project style guide
- [ ] All public methods have docstrings
- [ ] Test coverage ≥ 80% for new code
- [ ] Documentation clearly warns about project_root vs sandbox_path

---

## 🎯 Ready to Implement!

This plan provides a complete roadmap for implementing Task 5. Follow the TDD approach, write tests first, and iterate until all tests pass. The mapper will provide intelligent learning that improves fix success rates over time! 🚀

