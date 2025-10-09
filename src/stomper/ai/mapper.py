"""Error mapping and learning system for Stomper.

This module provides intelligent error pattern tracking, success rate calculation,
and adaptive prompting strategies based on historical fix outcomes.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

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

    def get_statistics(self) -> dict[str, Any]:
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
            with open(self.storage_path, encoding="utf-8") as f:
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
        # For first attempt (retry_count=0), use base verbosity
        # For retries, escalate further
        if retry_count == 0:
            return base_verbosity
        elif retry_count == 1:
            return PromptStrategy.DETAILED
        else:
            return PromptStrategy.VERBOSE

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
