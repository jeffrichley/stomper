"""Fix application and validation pipeline for Stomper.

This module handles applying AI-generated fixes from git sandbox to source files,
with backup, validation, and rollback capabilities.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from git.exc import GitCommandError

from stomper.ai.sandbox_manager import SandboxManager
from stomper.models.cli import ApplyResult, FixApplicationResult, RollbackReason, ValidationResult
from stomper.quality.base import BaseQualityTool, QualityError

if TYPE_CHECKING:
    from typing import Protocol

    class FixValidator(Protocol):
        """Protocol for fix validator (to be implemented in Task 4.4)."""

        def validate_fixes(
            self, files: list[Path], original_errors: list[QualityError]
        ) -> ValidationResult: ...

logger = logging.getLogger(__name__)


class FixApplier:
    """Applies AI-generated fixes from sandbox to source files with validation and rollback."""

    # Patterns to exclude from fix application
    EXCLUDED_PATTERNS: ClassVar[list[str]] = [
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".tox",
        "build",
        "dist",
        "*.egg-info",
    ]

    def __init__(
        self,
        sandbox_manager: SandboxManager,
        project_root: Path,
        quality_tools: list[BaseQualityTool] | None = None,
    ):
        """Initialize fix applier.

        Args:
            sandbox_manager: Sandbox manager instance for git operations
            project_root: Root path of the project
            quality_tools: Optional list of quality tools for validation

        Raises:
            ValueError: If project root doesn't exist
        """
        if not project_root.exists():
            raise ValueError(f"Project root does not exist: {project_root}")

        self.sandbox_manager = sandbox_manager
        self.project_root = project_root.resolve()  # Get absolute path
        self.quality_tools = quality_tools or []

    def apply_fixes(
        self,
        sandbox_path: Path,
        target_files: list[Path] | None = None,
        dry_run: bool = False,
    ) -> ApplyResult:
        """Apply fixes from sandbox to source files using git patch.

        Args:
            sandbox_path: Path to sandbox worktree
            target_files: Optional list of specific files to apply (if None, apply all)
            dry_run: If True, report what would be changed without modifying files

        Returns:
            ApplyResult with success status and applied files list
        """
        try:
            # Get changed files from sandbox
            changed_files = self._get_changed_files(sandbox_path)

            # Filter to target files if specified
            if target_files:
                # Convert target files to relative paths
                target_relative = {
                    f if not f.is_absolute() else f.relative_to(self.project_root) for f in target_files
                }
                changed_files = [f for f in changed_files if f in target_relative]

            # Filter out excluded patterns
            filtered_files = [f for f in changed_files if not self._should_exclude(f)]

            # Validate path safety
            safe_files = [f for f in filtered_files if self._is_safe_path(f)]
            unsafe_files = [f for f in filtered_files if not self._is_safe_path(f)]

            if unsafe_files:
                logger.warning(f"Skipping {len(unsafe_files)} unsafe paths")

            if not safe_files:
                return ApplyResult(
                    success=True,
                    files_applied=[],
                    files_failed=list(unsafe_files),
                    error_message="No safe files to apply" if unsafe_files else None,
                )

            # Handle dry run mode (report changes without applying)
            if dry_run:
                logger.info(f"[DRY RUN] Would apply changes to {len(safe_files)} files")
                files_to_apply = [self.project_root / f for f in safe_files]
                return ApplyResult(success=True, files_applied=files_to_apply, files_failed=[])

            # Try git patch approach first (ideal for atomicity and metadata preservation)
            diff_content = self.sandbox_manager.get_sandbox_diff(sandbox_path, "HEAD")

            if diff_content.strip():
                logger.debug("Using git patch approach for fix application")

                # Apply the patch using GitPython
                success = self.sandbox_manager.apply_sandbox_patch(
                    self.sandbox_manager.repo, diff_content
                )

                if success:
                    applied_files = [self.project_root / f for f in safe_files]
                    logger.info(f"✅ Successfully applied fixes to {len(applied_files)} files via git patch")
                    return ApplyResult(success=True, files_applied=applied_files, files_failed=[])
                else:
                    logger.warning("Git patch failed, falling back to manual file operations")

            # Fallback: Manual file operations (for edge cases, testing, or when git patch unavailable)
            logger.debug("Using manual file operations for fix application")
            return self._apply_fixes_manually(sandbox_path, safe_files, dry_run=False)

        except Exception as e:
            logger.error(f"Failed to apply fixes: {e}")
            return ApplyResult(
                success=False,
                files_applied=[],
                files_failed=[],
                error_message=str(e),
            )

    def _apply_fixes_manually(
        self, sandbox_path: Path, safe_files: list[Path], dry_run: bool
    ) -> ApplyResult:
        """Apply fixes manually by copying files (fallback when git patch unavailable).

        Args:
            sandbox_path: Path to sandbox
            safe_files: List of safe files to apply
            dry_run: Whether to perform dry run

        Returns:
            ApplyResult with application status
        """
        files_applied: list[Path] = []
        files_failed: list[Path] = []
        error_messages: list[str] = []

        # Get status to determine operation type for each file
        status = self.sandbox_manager.get_sandbox_status(sandbox_path)
        deleted_files = set(status.get("deleted", []))

        for relative_path in safe_files:
            try:
                sandbox_file = sandbox_path / relative_path
                source_file = self.project_root / relative_path

                # Normalize path for comparison (handle both Path and string, forward/backslash)
                relative_normalized = str(relative_path).replace("\\", "/")
                is_deletion = any(
                    str(deleted).replace("\\", "/") == relative_normalized for deleted in deleted_files
                )

                # Handle deletions
                if is_deletion:
                    if source_file.exists() and not dry_run:
                        source_file.unlink()
                        logger.info(f"Deleted: {relative_path}")
                    files_applied.append(source_file)
                    continue

                # For modifications/additions, sandbox file must exist
                if not sandbox_file.exists():
                    error_msg = f"Sandbox file missing for modification: {relative_path}"
                    logger.error(error_msg)
                    error_messages.append(error_msg)
                    files_failed.append(self.project_root / relative_path)
                    continue

                # Handle additions and modifications
                # Try text first, fallback to binary for non-UTF8 files
                try:
                    content = sandbox_file.read_text(encoding="utf-8")
                    if not dry_run:
                        source_file.parent.mkdir(parents=True, exist_ok=True)
                        # Preserve executable bit if it was set
                        preserve_exec = source_file.exists() and self._is_executable(source_file)
                        source_file.write_text(content, encoding="utf-8")
                        if preserve_exec:
                            self._make_executable(source_file)
                        logger.info(f"Applied: {relative_path}")
                    files_applied.append(source_file)
                except UnicodeDecodeError:
                    # Handle as binary file
                    if not dry_run:
                        source_file.parent.mkdir(parents=True, exist_ok=True)
                        import shutil

                        shutil.copy2(sandbox_file, source_file)
                        logger.info(f"Applied (binary): {relative_path}")
                    files_applied.append(source_file)

            except (OSError, PermissionError) as e:
                error_msg = f"Failed to apply {relative_path}: {e}"
                logger.error(error_msg)
                error_messages.append(error_msg)
                files_failed.append(self.project_root / relative_path)

        success = len(files_failed) == 0
        error_message = "; ".join(error_messages) if error_messages else None

        return ApplyResult(
            success=success,
            files_applied=files_applied,
            files_failed=files_failed,
            error_message=error_message,
        )

    def _get_changed_files(self, sandbox_path: Path) -> list[Path]:
        """Get list of files changed in sandbox.

        Args:
            sandbox_path: Path to sandbox worktree

        Returns:
            List of relative file paths that changed
        """
        status = self.sandbox_manager.get_sandbox_status(sandbox_path)

        # Combine modified, added, and deleted (but not untracked)
        changed_files = []
        changed_files.extend([Path(f) for f in status.get("modified", [])])
        changed_files.extend([Path(f) for f in status.get("added", [])])
        changed_files.extend([Path(f) for f in status.get("deleted", [])])

        return changed_files

    def _read_sandbox_file(self, sandbox_path: Path, relative_path: Path) -> str:
        """Read file content from sandbox.

        Note: This method is kept for backwards compatibility and testing,
        but apply_fixes() now uses git patch which is more robust.

        Args:
            sandbox_path: Path to sandbox worktree
            relative_path: Relative path to file within sandbox

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist in sandbox
            UnicodeDecodeError: If file is not valid UTF-8 text
        """
        sandbox_file = sandbox_path / relative_path
        return sandbox_file.read_text(encoding="utf-8")

    def _is_safe_path(self, file_path: Path) -> bool:
        """Validate that file path is safe (within project root).

        Args:
            file_path: Path to validate

        Returns:
            True if path is safe, False otherwise
        """
        # If absolute path, check it's within project root
        if file_path.is_absolute():
            try:
                file_path.relative_to(self.project_root)
                return True
            except ValueError:
                return False

        # If relative path, check for path traversal
        # Resolve the path and ensure it stays within project root
        try:
            resolved = (self.project_root / file_path).resolve()
            resolved.relative_to(self.project_root)
            return True
        except ValueError:
            return False

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from fix application.

        Args:
            file_path: Path to check

        Returns:
            True if file should be excluded
        """
        path_str = str(file_path)
        return any(pattern in path_str for pattern in self.EXCLUDED_PATTERNS)

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary.

        Args:
            file_path: Path to file

        Returns:
            True if file appears to be binary
        """
        try:
            # Try to read as text - if it fails, it's likely binary
            file_path.read_text(encoding="utf-8")
            return False
        except UnicodeDecodeError:
            return True
        except Exception:
            return False

    def _is_executable(self, file_path: Path) -> bool:
        """Check if file has executable permission.

        Args:
            file_path: Path to file

        Returns:
            True if file is executable
        """
        import stat

        try:
            return bool(file_path.stat().st_mode & stat.S_IEXEC)
        except Exception:
            return False

    def _make_executable(self, file_path: Path) -> None:
        """Make file executable.

        Args:
            file_path: Path to file
        """
        import stat

        try:
            current_mode = file_path.stat().st_mode
            file_path.chmod(current_mode | stat.S_IEXEC)
        except Exception as e:
            logger.warning(f"Failed to set executable bit on {file_path}: {e}")

    def _validate_no_concurrent_modification(self, file_path: Path) -> bool:
        """Validate that file hasn't been modified concurrently.

        Args:
            file_path: Path to validate

        Returns:
            True if no concurrent modification detected
        """
        # For now, always return True
        # Future: Could track mtimes or use git to detect changes
        return True

    def backup_files(self, files: list[Path]) -> str | None:
        """Create git stash backup of files before modification.

        Args:
            files: List of files to backup

        Returns:
            Stash reference (e.g., "stash@{0}") or None if no backup needed
        """
        if not files:
            return None

        try:
            # Use repo from sandbox manager
            repo = self.sandbox_manager.repo

            # Create stash with message
            stash_msg = f"stomper-backup-{len(files)}-files"

            # Check if there are changes to stash
            if repo.is_dirty(untracked_files=True):
                repo.git.stash("push", "-u", "-m", stash_msg)
                # Get the stash reference
                stash_list = repo.git.stash("list")
                if stash_list:
                    # Parse first stash reference
                    first_line = stash_list.split("\n")[0]
                    stash_ref: str = first_line.split(":")[0]
                    logger.info(f"Created backup: {stash_ref}")
                    return stash_ref

            return None

        except GitCommandError as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def restore_files(self, stash_ref: str) -> bool:
        """Restore files from git stash.

        Args:
            stash_ref: Stash reference to restore

        Returns:
            True if restoration successful, False otherwise
        """
        try:
            # Use repo from sandbox manager
            repo = self.sandbox_manager.repo

            # Apply and drop the stash
            repo.git.stash("pop", stash_ref)
            logger.info(f"Restored from backup: {stash_ref}")
            return True

        except GitCommandError as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False

    def apply_and_validate(
        self,
        sandbox_path: Path,
        validator: "FixValidator",
        original_errors: list[QualityError],
    ) -> FixApplicationResult:
        """Apply fixes with automatic validation and rollback.

        Workflow:
        1. Backup current state
        2. Apply fixes from sandbox
        3. Validate fixes
        4. If validation fails, rollback automatically
        5. Return comprehensive result

        Args:
            sandbox_path: Path to sandbox with fixes
            validator: Validator instance
            original_errors: Errors before fixing

        Returns:
            FixApplicationResult with all operation details
        """
        backup_ref = None
        rolled_back = False
        rollback_reason = None

        try:
            # Step 1: Get files to apply
            files_to_apply = self._get_changed_files(sandbox_path)
            absolute_files = [self.project_root / f for f in files_to_apply]

            # Step 2: Backup current state
            backup_ref = self.backup_files(absolute_files)
            logger.info(f"Backup created: {backup_ref}")

            # Step 3: Apply fixes
            apply_result = self.apply_fixes(sandbox_path)
            if not apply_result.success:
                logger.error("Fix application failed")
                # Restore backup
                if backup_ref:
                    rolled_back = self.restore_files(backup_ref)
                    rollback_reason = RollbackReason.VALIDATION_FAILED

                return FixApplicationResult(
                    success=False,
                    applied=apply_result,
                    validation=None,
                    rolled_back=rolled_back,
                    rollback_reason=rollback_reason,
                )

            # Step 4: Validate fixes
            validation_result = validator.validate_fixes(apply_result.files_applied, original_errors)

            # Step 5: Check if rollback needed
            should_rollback, reason = self._should_rollback(validation_result)

            if should_rollback:
                logger.warning(f"Validation failed: {reason}. Rolling back changes...")
                if backup_ref:
                    rolled_back = self.restore_files(backup_ref)
                    rollback_reason = reason

                return FixApplicationResult(
                    success=False,
                    applied=apply_result,
                    validation=validation_result,
                    rolled_back=rolled_back,
                    rollback_reason=rollback_reason,
                )

            # Success - drop backup
            logger.info("✅ Fixes applied and validated successfully!")
            return FixApplicationResult(
                success=True,
                applied=apply_result,
                validation=validation_result,
                rolled_back=False,
                rollback_reason=None,
            )

        except Exception as e:
            logger.error(f"Error during apply and validate: {e}")

            # Attempt rollback on any error
            if backup_ref:
                rolled_back = self.restore_files(backup_ref)
                rollback_reason = RollbackReason.VALIDATION_FAILED

            return FixApplicationResult(
                success=False,
                applied=ApplyResult(success=False, error_message=str(e)),
                validation=None,
                rolled_back=rolled_back,
                rollback_reason=rollback_reason,
            )

    def _should_rollback(self, validation: ValidationResult) -> tuple[bool, RollbackReason | None]:
        """Determine if rollback is needed based on validation result.

        Args:
            validation: Validation result to check

        Returns:
            Tuple of (should_rollback, reason)
        """
        # Rollback if new errors were introduced
        if validation.new_errors_introduced > 0:
            return True, RollbackReason.NEW_ERRORS_INTRODUCED

        # Rollback if validation failed
        if not validation.passed:
            return True, RollbackReason.VALIDATION_FAILED

        # No rollback needed
        return False, None

