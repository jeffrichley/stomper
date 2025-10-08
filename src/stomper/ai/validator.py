"""Fix validation pipeline for Stomper.

This module validates AI-generated fixes by running quality tools and comparing
error states before and after fixes are applied.
"""

import logging
from pathlib import Path

from stomper.models.cli import ErrorComparison, ValidationResult
from stomper.quality.base import BaseQualityTool, QualityError
from stomper.quality.manager import QualityToolManager

logger = logging.getLogger(__name__)


class FixValidator:
    """Validates AI-generated fixes using quality tools."""

    def __init__(
        self,
        project_root: Path,
        quality_tools: list[BaseQualityTool] | QualityToolManager | None = None,
    ):
        """Initialize fix validator.

        Args:
            project_root: Root path of the project
            quality_tools: List of quality tools OR QualityToolManager instance.
                          If None, creates new QualityToolManager.

        Raises:
            ValueError: If project root doesn't exist
        """
        if not project_root.exists():
            raise ValueError(f"Project root does not exist: {project_root}")

        self.project_root = project_root

        # Accept either QualityToolManager or list of tools (backwards compatible)
        if isinstance(quality_tools, QualityToolManager):
            self.tool_manager: QualityToolManager | None = quality_tools
            self.quality_tools: list[BaseQualityTool] = []  # Keep for backwards compat
        elif quality_tools is None:
            self.tool_manager = QualityToolManager()
            self.quality_tools = []
        else:
            # Legacy: list of tools - create manager with those tools
            self.quality_tools = quality_tools
            self.tool_manager = None  # Will use manual tool running

    def validate_fixes(
        self, files: list[Path], original_errors: list[QualityError]
    ) -> ValidationResult:
        """Validate that fixes resolve errors without introducing new ones.

        Args:
            files: Files that were fixed
            original_errors: Original errors before fixing

        Returns:
            ValidationResult with pass/fail status and details
        """
        # Handle empty file list
        if not files:
            return ValidationResult(
                passed=True,
                errors_fixed=0,
                errors_remaining=0,
                new_errors_introduced=0,
                summary="No files to validate",
            )

        # Run quality checks on fixed files
        logger.info(f"Running quality checks on {len(files)} fixed files...")
        new_errors = self._run_quality_checks(files)

        # Compare error sets
        comparison = self._compare_errors(original_errors, new_errors)

        # Generate result
        result = self._generate_result(comparison)

        logger.info(f"Validation: {result.summary}")
        return result

    def _run_quality_checks(self, files: list[Path]) -> list[QualityError]:
        """Run quality tools on fixed files.

        Args:
            files: List of files to check

        Returns:
            List of QualityError objects found
        """
        # Use QualityToolManager if available (preferred - reuses existing infrastructure)
        if self.tool_manager:
            # Run tools on project root (they handle their own file filtering)
            # Get all available tools from the manager
            available_tool_names = self.tool_manager.get_available_tools()

            logger.debug(f"Using QualityToolManager with tools: {available_tool_names}")
            all_errors = self.tool_manager.run_tools(
                target_path=self.project_root,
                project_root=self.project_root,
                enabled_tools=available_tool_names,
                max_errors=10000,  # Don't limit errors during validation
            )

            # Filter to only errors in our fixed files
            filtered_errors = self._filter_errors_to_files(all_errors, files)
            logger.debug(f"Filtered to {len(filtered_errors)} errors in {len(files)} fixed files")
            return filtered_errors

        # Legacy fallback: Manual tool running (for backwards compatibility with tests)
        return self._run_tools_manually(files)

    def _run_tools_manually(self, files: list[Path]) -> list[QualityError]:
        """Run quality tools manually (legacy/testing fallback).

        Args:
            files: List of files to check

        Returns:
            List of QualityError objects found
        """
        all_errors: list[QualityError] = []

        # Run each available tool
        for tool in self.quality_tools:
            if not tool.is_available():
                logger.debug(f"Skipping unavailable tool: {tool.tool_name}")
                continue

            try:
                # Run tool on project root
                errors = tool.run_tool(self.project_root, self.project_root)

                # Filter to only errors in our fixed files
                filtered_errors = self._filter_errors_to_files(errors, files)
                all_errors.extend(filtered_errors)
                logger.debug(f"{tool.tool_name}: {len(filtered_errors)} errors in fixed files")

            except Exception as e:
                logger.error(f"Error running {tool.tool_name}: {e}")
                # Continue with other tools

        return all_errors

    def _filter_errors_to_files(
        self, errors: list[QualityError], files: list[Path]
    ) -> list[QualityError]:
        """Filter errors to only those in specified files.

        Args:
            errors: All errors from quality tools
            files: Files to filter to

        Returns:
            Filtered list of errors
        """
        # Build set of file paths (both absolute and relative) for matching
        file_set_absolute = {
            f.resolve() if f.is_absolute() else (self.project_root / f).resolve() for f in files
        }
        file_set_relative = {
            f.relative_to(self.project_root)
            if f.is_absolute() and f.is_relative_to(self.project_root)
            else f
            for f in files
        }

        filtered_errors = []
        for e in errors:
            # Try to match by absolute path
            if e.file.resolve() in file_set_absolute:
                filtered_errors.append(e)
                continue

            # Try to match by relative path
            try:
                error_relative = (
                    e.file.relative_to(self.project_root) if e.file.is_absolute() else e.file
                )
                if error_relative in file_set_relative:
                    filtered_errors.append(e)
            except ValueError:
                # File not in project root
                pass

        return filtered_errors

    def _compare_errors(
        self, original: list[QualityError], new: list[QualityError]
    ) -> ErrorComparison:
        """Compare error lists to determine improvement.

        Args:
            original: Original errors before fixing
            new: New errors after fixing

        Returns:
            ErrorComparison with fixed, remaining, and introduced errors
        """
        fixed: list[QualityError] = []
        remaining: list[QualityError] = []
        introduced: list[QualityError] = []

        # Find errors that were fixed (in original but not in new)
        for orig_error in original:
            if not any(self._errors_match(orig_error, new_error) for new_error in new):
                fixed.append(orig_error)
            else:
                remaining.append(orig_error)

        # Find errors that were introduced (in new but not in original)
        for new_error in new:
            if not any(self._errors_match(new_error, orig_error) for orig_error in original):
                introduced.append(new_error)

        return ErrorComparison(fixed=fixed, remaining=remaining, introduced=introduced)

    def _errors_match(self, error1: QualityError, error2: QualityError) -> bool:
        """Check if two errors are the same.

        Args:
            error1: First error to compare
            error2: Second error to compare

        Returns:
            True if errors match (same file, line, code)
        """
        # Errors match if they're at the same location with the same code
        return (
            error1.file.resolve() == error2.file.resolve()
            and error1.line == error2.line
            and error1.code == error2.code
            and error1.tool == error2.tool
        )

    def _generate_result(self, comparison: ErrorComparison) -> ValidationResult:
        """Generate ValidationResult from error comparison.

        Args:
            comparison: Error comparison data

        Returns:
            ValidationResult with pass/fail determination
        """
        errors_fixed = len(comparison.fixed)
        errors_remaining = len(comparison.remaining)
        new_errors_introduced = len(comparison.introduced)

        # Validation passes if:
        # 1. No new errors introduced AND at least some progress made (errors_fixed > 0 OR errors_remaining == 0)
        # 2. If there were original errors and none were fixed, that's a failure
        if new_errors_introduced > 0:
            # New errors introduced - always fail
            passed = False
        elif errors_fixed == 0 and errors_remaining > 0:
            # No progress made - fail
            passed = False
        else:
            # Either made progress or clean state - pass
            passed = True

        # Generate summary
        if passed:
            if errors_fixed > 0:
                summary = f"✅ Success: {errors_fixed} error(s) fixed"
                if errors_remaining > 0:
                    summary += f", {errors_remaining} remaining"
            else:
                summary = "✅ No errors found"
        else:
            if new_errors_introduced > 0:
                summary = f"❌ Validation failed: {new_errors_introduced} new error(s) introduced"
                if errors_fixed > 0:
                    summary += f" ({errors_fixed} fixed)"
            else:
                summary = f"❌ No improvement: {errors_remaining} error(s) remain unfixed"

        return ValidationResult(
            passed=passed,
            errors_fixed=errors_fixed,
            errors_remaining=errors_remaining,
            new_errors_introduced=new_errors_introduced,
            new_errors=comparison.introduced,
            summary=summary,
        )
