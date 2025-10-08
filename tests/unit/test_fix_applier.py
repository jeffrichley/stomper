"""Tests for FixApplier class - Fix Application and Validation Pipeline."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from stomper.ai.fix_applier import FixApplier
from stomper.ai.sandbox_manager import SandboxManager
from stomper.models.cli import ApplyResult, RollbackReason
from stomper.quality.base import QualityError


@pytest.fixture
def mock_sandbox_manager():
    """Create a mock sandbox manager for testing."""
    mock_mgr = Mock(spec=SandboxManager)
    mock_mgr.project_root = Path("/project")
    return mock_mgr


@pytest.fixture
def sample_quality_error():
    """Create a sample quality error for testing."""
    return QualityError(
        tool="ruff",
        file=Path("/project/src/main.py"),
        line=10,
        column=5,
        code="F401",
        message="Unused import",
        severity="error",
        auto_fixable=True,
    )


# ============================================================================
# Initialization Tests
# ============================================================================


class TestFixApplierInitialization:
    """Test FixApplier initialization."""

    @pytest.mark.unit
    def test_fix_applier_initialization(self, mock_sandbox_manager):
        """Test basic FixApplier initialization."""
        project_root = Path("/project")
        applier = FixApplier(mock_sandbox_manager, project_root)

        assert applier.sandbox_manager == mock_sandbox_manager
        assert applier.project_root == project_root

    @pytest.mark.unit
    def test_fix_applier_initialization_validates_project_root(self, mock_sandbox_manager):
        """Test initialization validates project root exists."""
        with (
            patch.object(Path, "exists", return_value=False),
            pytest.raises(ValueError, match="Project root does not exist"),
        ):
            FixApplier(mock_sandbox_manager, Path("/nonexistent"))

    @pytest.mark.unit
    def test_fix_applier_initialization_with_quality_tools(self, mock_sandbox_manager):
        """Test initialization with quality tools for validation."""
        from stomper.quality.ruff import RuffTool

        project_root = Path("/project")
        quality_tools = [RuffTool()]

        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root, quality_tools=quality_tools)

            assert applier.quality_tools == quality_tools


# ============================================================================
# Fix Application Tests - Basic Functionality
# ============================================================================


class TestFixApplierBasicApplication:
    """Test basic fix application functionality."""

    @pytest.mark.unit
    def test_apply_fixes_success_single_file(self, mock_sandbox_manager, tmp_path):
        """Test applying fix from sandbox to single source file."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        source_file = project_root / "src" / "main.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("old content\n")

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("fixed content\n")

        # Mock sandbox status to return modified file
        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify
        assert result.success is True
        assert len(result.files_applied) == 1
        assert source_file in result.files_applied
        assert len(result.files_failed) == 0
        assert source_file.read_text() == "fixed content\n"

    @pytest.mark.unit
    def test_apply_fixes_multiple_files(self, mock_sandbox_manager, tmp_path):
        """Test applying fixes to multiple files."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create source files
        files_to_fix = ["src/main.py", "src/utils.py", "tests/test_main.py"]
        for file_path in files_to_fix:
            file = project_root / file_path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(f"old content for {file_path}\n")

        # Create sandbox with fixes
        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        for file_path in files_to_fix:
            file = sandbox_path / file_path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(f"fixed content for {file_path}\n")

        # Mock sandbox status
        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": files_to_fix,
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify
        assert result.success is True
        assert len(result.files_applied) == 3
        assert len(result.files_failed) == 0

        for file_path in files_to_fix:
            source_file = project_root / file_path
            assert source_file.read_text() == f"fixed content for {file_path}\n"

    @pytest.mark.unit
    def test_apply_fixes_with_target_files_filter(self, mock_sandbox_manager, tmp_path):
        """Test applying fixes only to specific target files."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        source_file1 = project_root / "src" / "main.py"
        source_file1.parent.mkdir(parents=True)
        source_file1.write_text("old content 1\n")

        source_file2 = project_root / "src" / "utils.py"
        source_file2.write_text("old content 2\n")

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file1 = sandbox_path / "src" / "main.py"
        sandbox_file1.parent.mkdir(parents=True)
        sandbox_file1.write_text("fixed content 1\n")

        sandbox_file2 = sandbox_path / "src" / "utils.py"
        sandbox_file2.write_text("fixed content 2\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py", "src/utils.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute - only apply main.py
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path, target_files=[Path("src/main.py")])

        # Verify - only main.py was applied
        assert result.success is True
        assert len(result.files_applied) == 1
        assert source_file1.read_text() == "fixed content 1\n"
        assert source_file2.read_text() == "old content 2\n"  # Unchanged


# ============================================================================
# File Addition and Deletion Tests
# ============================================================================


class TestFixApplierFileOperations:
    """Test file additions and deletions."""

    @pytest.mark.unit
    def test_apply_fixes_handles_file_additions(self, mock_sandbox_manager, tmp_path):
        """Test applying fixes when sandbox adds new files."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        new_file = sandbox_path / "src" / "new_module.py"
        new_file.parent.mkdir(parents=True)
        new_file.write_text("# New module\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": [],
            "added": ["src/new_module.py"],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify
        assert result.success is True
        source_new_file = project_root / "src" / "new_module.py"
        assert source_new_file.exists()
        assert source_new_file.read_text() == "# New module\n"

    @pytest.mark.unit
    def test_apply_fixes_handles_file_deletions(self, mock_sandbox_manager, tmp_path):
        """Test applying fixes when sandbox deletes files."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        file_to_delete = project_root / "src" / "deprecated.py"
        file_to_delete.parent.mkdir(parents=True)
        file_to_delete.write_text("# Deprecated\n")

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": [],
            "added": [],
            "deleted": ["src/deprecated.py"],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify
        assert result.success is True
        assert not file_to_delete.exists()


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestFixApplierErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.unit
    def test_apply_fixes_source_file_missing(self, mock_sandbox_manager, tmp_path):
        """Test handling when source file doesn't exist."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("fixed content\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify - should create the file (treating as addition)
        assert result.success is True
        source_file = project_root / "src" / "main.py"
        assert source_file.exists()

    @pytest.mark.unit
    def test_apply_fixes_sandbox_file_missing(self, mock_sandbox_manager, tmp_path):
        """Test handling when sandbox file doesn't exist."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        source_file = project_root / "src" / "main.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("old content\n")

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        # Don't create sandbox file

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify - should fail for this file
        assert result.success is False
        assert len(result.files_failed) == 1
        assert Path("src/main.py") in [f.relative_to(project_root) for f in result.files_failed]

    @pytest.mark.unit
    def test_apply_fixes_permission_error(self, mock_sandbox_manager, tmp_path):
        """Test handling permission errors during file write."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("fixed content\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute with mocked permission error
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            applier = FixApplier(mock_sandbox_manager, project_root)
            result = applier.apply_fixes(sandbox_path)

            # Verify - should handle gracefully
            assert result.success is False
            assert len(result.files_failed) == 1
            assert result.error_message is not None
            assert "Permission denied" in result.error_message

    @pytest.mark.unit
    def test_apply_fixes_partial_success(self, mock_sandbox_manager, tmp_path):
        """Test applying fixes when some files succeed and some fail."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create first source file (will succeed)
        file1 = project_root / "src" / "main.py"
        file1.parent.mkdir(parents=True)
        file1.write_text("old content 1\n")

        # Create sandbox files
        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file1 = sandbox_path / "src" / "main.py"
        sandbox_file1.parent.mkdir(parents=True)
        sandbox_file1.write_text("fixed content 1\n")

        sandbox_file2 = sandbox_path / "src" / "utils.py"
        sandbox_file2.write_text("fixed content 2\n")
        # Note: source utils.py doesn't exist and sandbox shows it as modified (error case)

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py", "src/utils.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify - partial success (main.py succeeds, utils.py created as new file)
        assert result.success is True
        assert len(result.files_applied) == 2


# ============================================================================
# Sandbox Integration Tests
# ============================================================================


class TestFixApplierSandboxIntegration:
    """Test integration with SandboxManager."""

    @pytest.mark.unit
    def test_get_changed_files_from_sandbox(self, mock_sandbox_manager):
        """Test extracting changed files from sandbox status."""
        # Setup
        project_root = Path("/project")
        sandbox_path = Path("/sandbox")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py", "src/utils.py"],
            "added": ["src/new_file.py"],
            "deleted": ["src/deprecated.py"],
            "untracked": ["temp.py"],
        }

        # Execute
        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)
            changed_files = applier._get_changed_files(sandbox_path)

            # Verify - should return modified, added, and deleted files (not untracked)
            assert len(changed_files) == 4
            assert Path("src/main.py") in changed_files
            assert Path("src/utils.py") in changed_files
            assert Path("src/new_file.py") in changed_files
            assert Path("src/deprecated.py") in changed_files
            assert Path("temp.py") not in changed_files

    @pytest.mark.unit
    def test_read_file_from_sandbox(self, mock_sandbox_manager, tmp_path):
        """Test reading file content from sandbox."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        test_content = "# Fixed code\ndef main():\n    pass\n"
        sandbox_file.write_text(test_content)

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        content = applier._read_sandbox_file(sandbox_path, Path("src/main.py"))

        # Verify
        assert content == test_content

    @pytest.mark.unit
    def test_validate_file_path_safety(self, mock_sandbox_manager):
        """Test validation that file paths are safe (within project root)."""
        # Setup
        project_root = Path("/project")

        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)

            # Test valid paths
            assert applier._is_safe_path(Path("src/main.py")) is True
            assert applier._is_safe_path(Path("tests/test_main.py")) is True

            # Test invalid paths (outside project root)
            assert applier._is_safe_path(Path("../outside/file.py")) is False
            assert applier._is_safe_path(Path("/etc/passwd")) is False

    @pytest.mark.unit
    def test_skip_excluded_patterns(self, mock_sandbox_manager, tmp_path):
        """Test skipping files matching excluded patterns."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()

        # Create files in sandbox
        files = [
            "src/main.py",  # Should apply
            ".venv/lib/module.py",  # Should skip (venv)
            ".git/config",  # Should skip (git)
            "__pycache__/main.pyc",  # Should skip (cache)
        ]

        for file_path in files:
            file = sandbox_path / file_path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("content\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": files,
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify - only src/main.py should be applied
        assert result.success is True
        assert len(result.files_applied) == 1
        assert any("main.py" in str(f) for f in result.files_applied)


# ============================================================================
# Backup and Restore Tests
# ============================================================================


class TestFixApplierBackupRestore:
    """Test file backup and restoration functionality."""

    @pytest.mark.unit
    def test_backup_files_creates_git_stash(self, mock_sandbox_manager):
        """Test creating git stash backup before applying fixes."""
        # Setup
        project_root = Path("/project")
        files_to_backup = [Path("src/main.py"), Path("src/utils.py")]

        mock_repo = Mock()
        mock_repo.git.stash.return_value = "Saved working directory"
        mock_sandbox_manager.repo = mock_repo

        # Execute
        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)
            stash_ref = applier.backup_files(files_to_backup)

            # Verify
            assert stash_ref is not None
            assert "stash@{" in stash_ref or stash_ref.startswith("WIP")

    @pytest.mark.unit
    def test_restore_files_from_git_stash(self, mock_sandbox_manager):
        """Test restoring files from git stash."""
        # Setup
        project_root = Path("/project")
        stash_ref = "stash@{0}"

        mock_repo = Mock()
        mock_repo.git.stash.return_value = None
        mock_sandbox_manager.repo = mock_repo

        # Execute
        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)
            success = applier.restore_files(stash_ref)

            # Verify
            assert success is True
            # Should call git stash pop or apply
            mock_repo.git.stash.assert_called()

    @pytest.mark.unit
    def test_backup_with_no_files(self, mock_sandbox_manager):
        """Test backup handles empty file list gracefully."""
        # Setup
        project_root = Path("/project")

        # Execute
        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)
            stash_ref = applier.backup_files([])

            # Verify - should return None or skip backup
            assert stash_ref is None

    @pytest.mark.unit
    def test_restore_handles_stash_conflicts(self, mock_sandbox_manager):
        """Test handling conflicts during stash restoration."""
        # Setup
        project_root = Path("/project")
        stash_ref = "stash@{0}"

        from git.exc import GitCommandError

        mock_repo = Mock()
        mock_repo.git.stash.side_effect = GitCommandError("stash pop", "CONFLICT")
        mock_sandbox_manager.repo = mock_repo

        # Execute
        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)
            success = applier.restore_files(stash_ref)

            # Verify - should handle gracefully
            assert success is False


# ============================================================================
# Validation Integration Tests
# ============================================================================


class TestFixApplierValidation:
    """Test fix validation integration."""

    @pytest.mark.unit
    def test_apply_and_validate_success(self, mock_sandbox_manager, tmp_path, sample_quality_error):
        """Test successful application with validation."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        source_file = project_root / "src" / "main.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("import unused\n")

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("# Fixed - import removed\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Mock validator
        mock_validator = Mock()
        mock_validator.validate_fixes.return_value = Mock(
            passed=True, errors_fixed=1, errors_remaining=0, new_errors_introduced=0
        )

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_and_validate(
            sandbox_path, validator=mock_validator, original_errors=[sample_quality_error]
        )

        # Verify
        assert result.success is True
        assert result.applied.success is True
        assert result.validation.passed is True
        assert result.rolled_back is False

    @pytest.mark.unit
    def test_apply_and_validate_with_rollback(self, mock_sandbox_manager, tmp_path, sample_quality_error):
        """Test automatic rollback when validation fails."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        source_file = project_root / "src" / "main.py"
        source_file.parent.mkdir(parents=True)
        original_content = "original content\n"
        source_file.write_text(original_content)

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("broken fix\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Mock validator to fail
        mock_validator = Mock()
        mock_validator.validate_fixes.return_value = Mock(
            passed=False, errors_fixed=0, errors_remaining=1, new_errors_introduced=2
        )

        # Mock git operations for backup/restore
        mock_repo = Mock()
        mock_repo.git.stash.return_value = "Saved"
        mock_sandbox_manager.repo = mock_repo

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)

        with (
            patch.object(applier, "backup_files", return_value="stash@{0}"),
            patch.object(applier, "restore_files", return_value=True) as mock_restore,
        ):
            result = applier.apply_and_validate(
                sandbox_path, validator=mock_validator, original_errors=[sample_quality_error]
            )

            # Verify
            assert result.success is False
            assert result.rolled_back is True
            assert result.rollback_reason == RollbackReason.NEW_ERRORS_INTRODUCED
            mock_restore.assert_called_once()


# ============================================================================
# Edge Cases
# ============================================================================


class TestFixApplierEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_apply_fixes_empty_sandbox(self, mock_sandbox_manager, tmp_path):
        """Test applying fixes when sandbox has no changes."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": [],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify
        assert result.success is True
        assert len(result.files_applied) == 0
        assert len(result.files_failed) == 0

    @pytest.mark.unit
    def test_apply_fixes_only_untracked_files(self, mock_sandbox_manager, tmp_path):
        """Test when sandbox only has untracked files."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": [],
            "added": [],
            "deleted": [],
            "untracked": ["temp.py", "debug.log"],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify - untracked files should be ignored
        assert result.success is True
        assert len(result.files_applied) == 0

    @pytest.mark.unit
    def test_apply_fixes_handles_binary_files(self, mock_sandbox_manager, tmp_path):
        """Test handling of binary files (should skip or error gracefully)."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        binary_file = sandbox_path / "image.png"
        binary_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["image.png"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify - should skip binary files
        assert len(result.files_failed) == 0 or len(result.files_applied) == 1
        # Implementation can either skip or apply binary files

    @pytest.mark.unit
    def test_apply_fixes_concurrent_modification(self, mock_sandbox_manager, tmp_path):
        """Test handling when source file is modified during fix application."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        source_file = project_root / "src" / "main.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("original content\n")

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("fixed content\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute - simulate concurrent modification detection
        applier = FixApplier(mock_sandbox_manager, project_root)

        # Validate concurrent modification check
        with patch.object(applier, "_validate_no_concurrent_modification", return_value=True):
            result = applier.apply_fixes(sandbox_path)

            # Should succeed with validation
            assert result.success is True

    @pytest.mark.unit
    def test_apply_fixes_preserves_file_permissions(self, mock_sandbox_manager, tmp_path):
        """Test that file permissions are preserved when applying fixes."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        source_file = project_root / "src" / "script.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("#!/usr/bin/env python\nprint('hello')\n")

        # Make executable
        import stat

        source_file.chmod(source_file.stat().st_mode | stat.S_IEXEC)
        original_mode = source_file.stat().st_mode

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "script.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("#!/usr/bin/env python\nprint('hello world')\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/script.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify - permissions should be preserved
        assert result.success is True
        new_mode = source_file.stat().st_mode
        assert (new_mode & stat.S_IEXEC) == (original_mode & stat.S_IEXEC)


# ============================================================================
# Dry Run Tests
# ============================================================================


class TestFixApplierDryRun:
    """Test dry run functionality."""

    @pytest.mark.unit
    def test_apply_fixes_dry_run_no_changes(self, mock_sandbox_manager, tmp_path):
        """Test dry run mode doesn't modify files."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        source_file = project_root / "src" / "main.py"
        source_file.parent.mkdir(parents=True)
        original_content = "original content\n"
        source_file.write_text(original_content)

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("fixed content\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute in dry run mode
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path, dry_run=True)

        # Verify - should report what would be changed but not actually change files
        assert result.success is True
        assert len(result.files_applied) == 1  # Would apply this file
        assert source_file.read_text() == original_content  # But file unchanged

    @pytest.mark.unit
    def test_dry_run_reports_all_changes(self, mock_sandbox_manager, tmp_path):
        """Test dry run reports all changes that would be made."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py", "src/utils.py"],
            "added": ["src/new.py"],
            "deleted": ["src/old.py"],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path, dry_run=True)

        # Verify - should report all changes
        assert result.success is True
        # Should account for all file operations
        total_operations = len(result.files_applied) + len(result.files_failed)
        assert total_operations >= 3  # modified + added + deleted


# ============================================================================
# Integration with Apply and Validate
# ============================================================================


class TestFixApplierFullWorkflow:
    """Test complete fix application workflow with all components."""

    @pytest.mark.unit
    def test_full_workflow_success_path(self, mock_sandbox_manager, tmp_path, sample_quality_error):
        """Test complete workflow: backup -> apply -> validate -> keep changes."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        source_file = project_root / "src" / "main.py"
        source_file.parent.mkdir(parents=True)
        source_file.write_text("import unused\n")

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("# Fixed\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        mock_validator = Mock()
        mock_validator.validate_fixes.return_value = Mock(
            passed=True, errors_fixed=1, errors_remaining=0, new_errors_introduced=0, summary="Success"
        )

        mock_repo = Mock()
        mock_repo.git.stash.return_value = "Saved"
        mock_sandbox_manager.repo = mock_repo

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_and_validate(
            sandbox_path, validator=mock_validator, original_errors=[sample_quality_error]
        )

        # Verify
        assert result.success is True
        assert result.applied.success is True
        assert result.validation.passed is True
        assert result.rolled_back is False
        assert source_file.read_text() == "# Fixed\n"

    @pytest.mark.unit
    def test_full_workflow_rollback_path(self, mock_sandbox_manager, tmp_path, sample_quality_error):
        """Test complete workflow: backup -> apply -> validate FAIL -> rollback."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        source_file = project_root / "src" / "main.py"
        source_file.parent.mkdir(parents=True)
        original_content = "original content\n"
        source_file.write_text(original_content)

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_file = sandbox_path / "src" / "main.py"
        sandbox_file.parent.mkdir(parents=True)
        sandbox_file.write_text("broken fix\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Mock validator to fail (introduced new errors)
        mock_validator = Mock()
        mock_validator.validate_fixes.return_value = Mock(
            passed=False,
            errors_fixed=1,
            errors_remaining=0,
            new_errors_introduced=3,
            summary="Introduced new errors",
        )

        mock_repo = Mock()
        mock_sandbox_manager.repo = mock_repo

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)

        with (
            patch.object(applier, "backup_files", return_value="stash@{0}") as mock_backup,
            patch.object(applier, "restore_files", return_value=True) as mock_restore,
        ):
            result = applier.apply_and_validate(
                sandbox_path, validator=mock_validator, original_errors=[sample_quality_error]
            )

            # Verify
            assert result.success is False
            assert result.rolled_back is True
            assert result.rollback_reason == RollbackReason.NEW_ERRORS_INTRODUCED
            mock_backup.assert_called_once()
            mock_restore.assert_called_once_with("stash@{0}")

    @pytest.mark.unit
    def test_rollback_reason_selection(self, mock_sandbox_manager, tmp_path):
        """Test correct rollback reason is selected based on validation result."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": [],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        applier = FixApplier(mock_sandbox_manager, project_root)

        # Test different validation failures
        test_cases = [
            # (passed, new_errors, expected_reason)
            (False, 0, RollbackReason.VALIDATION_FAILED),
            (False, 2, RollbackReason.NEW_ERRORS_INTRODUCED),
            (True, 0, None),  # No rollback
        ]

        for passed, new_errors, expected_reason in test_cases:
            mock_validation = Mock(passed=passed, new_errors_introduced=new_errors)
            should_rollback, reason = applier._should_rollback(mock_validation)

            if expected_reason is None:
                assert should_rollback is False
                assert reason is None
            else:
                assert should_rollback is True
                assert reason == expected_reason

    @pytest.mark.unit
    def test_apply_fixes_with_symbolic_links(self, mock_sandbox_manager, tmp_path):
        """Test handling of symbolic links in sandbox."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create a real file
        real_file = project_root / "src" / "real.py"
        real_file.parent.mkdir(parents=True)
        real_file.write_text("real content\n")

        # Create symbolic link in project
        link_file = project_root / "src" / "link.py"
        link_file.symlink_to(real_file)

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        sandbox_link = sandbox_path / "src" / "link.py"
        sandbox_link.parent.mkdir(parents=True)
        sandbox_link.write_text("modified via link\n")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/link.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify - should handle symbolic links appropriately
        # Either follow the link or skip it, but shouldn't crash
        assert isinstance(result.success, bool)

    @pytest.mark.unit
    def test_apply_fixes_large_file_handling(self, mock_sandbox_manager, tmp_path):
        """Test handling of large files."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        large_file = sandbox_path / "src" / "large.py"
        large_file.parent.mkdir(parents=True)

        # Create a large file (1MB)
        large_content = "# Large file\n" + ("x" * 1_000_000)
        large_file.write_text(large_content)

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/large.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify - should handle large files
        assert isinstance(result.success, bool)
        # Should either succeed or fail gracefully

    @pytest.mark.unit
    def test_apply_fixes_unicode_content(self, mock_sandbox_manager, tmp_path):
        """Test handling files with unicode characters."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()
        unicode_file = sandbox_path / "src" / "unicode.py"
        unicode_file.parent.mkdir(parents=True)
        unicode_content = "# 测试 emoji 🎉\ndef hello():\n    print('Hello 世界')\n"
        unicode_file.write_text(unicode_content, encoding="utf-8")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/unicode.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        applier = FixApplier(mock_sandbox_manager, project_root)
        result = applier.apply_fixes(sandbox_path)

        # Verify
        assert result.success is True
        source_file = project_root / "src" / "unicode.py"
        assert source_file.read_text(encoding="utf-8") == unicode_content


# ============================================================================
# Path Safety and Security Tests
# ============================================================================


class TestFixApplierSecurity:
    """Test security and path safety features."""

    @pytest.mark.unit
    def test_reject_path_traversal_attempts(self, mock_sandbox_manager, tmp_path):
        """Test rejection of path traversal attempts."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()

        # Mock sandbox status with malicious paths
        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["../../../etc/passwd", "../../outside.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)
            result = applier.apply_fixes(sandbox_path)

            # Verify - should reject all path traversal attempts
            assert len(result.files_failed) == 2
            assert not (tmp_path.parent / "outside.py").exists()

    @pytest.mark.unit
    def test_reject_absolute_paths_outside_project(self, mock_sandbox_manager, tmp_path):
        """Test rejection of absolute paths outside project root."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        sandbox_path = tmp_path / "sandbox"
        sandbox_path.mkdir()

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["/etc/passwd", "/tmp/malicious.py"],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        # Execute
        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)
            result = applier.apply_fixes(sandbox_path)

            # Verify - should reject absolute paths outside project
            assert len(result.files_failed) == 2


# ============================================================================
# Helper Method Tests
# ============================================================================


class TestFixApplierHelperMethods:
    """Test helper methods in FixApplier."""

    @pytest.mark.unit
    def test_get_changed_files_excludes_untracked(self, mock_sandbox_manager):
        """Test _get_changed_files excludes untracked files."""
        # Setup
        project_root = Path("/project")
        sandbox_path = Path("/sandbox")

        mock_sandbox_manager.get_sandbox_status.return_value = {
            "modified": ["src/main.py"],
            "added": ["src/new.py"],
            "deleted": ["src/old.py"],
            "untracked": ["temp.py", "debug.log"],
        }

        # Execute
        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)
            changed_files = applier._get_changed_files(sandbox_path)

            # Verify
            assert Path("src/main.py") in changed_files
            assert Path("src/new.py") in changed_files
            assert Path("src/old.py") in changed_files
            assert Path("temp.py") not in changed_files
            assert Path("debug.log") not in changed_files

    @pytest.mark.unit
    def test_is_safe_path_validation(self, mock_sandbox_manager):
        """Test path safety validation logic."""
        # Setup
        project_root = Path("/project")

        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)

            # Test safe paths (relative within project)
            assert applier._is_safe_path(Path("src/main.py")) is True
            assert applier._is_safe_path(Path("src/sub/util.py")) is True
            assert applier._is_safe_path(Path("tests/test_main.py")) is True

            # Test unsafe paths (path traversal)
            assert applier._is_safe_path(Path("../outside.py")) is False
            assert applier._is_safe_path(Path("../../etc/passwd")) is False

            # Test unsafe paths (absolute outside project)
            assert applier._is_safe_path(Path("/etc/passwd")) is False
            assert applier._is_safe_path(Path("/tmp/file.py")) is False

    @pytest.mark.unit
    def test_should_rollback_decision_logic(self, mock_sandbox_manager):
        """Test rollback decision logic with various validation results."""
        # Setup
        project_root = Path("/project")

        with patch.object(Path, "exists", return_value=True):
            applier = FixApplier(mock_sandbox_manager, project_root)

            # Case 1: Validation passed - no rollback
            validation = Mock(passed=True, new_errors_introduced=0)
            should_rollback, reason = applier._should_rollback(validation)
            assert should_rollback is False
            assert reason is None

            # Case 2: Validation failed - rollback
            validation = Mock(passed=False, new_errors_introduced=0)
            should_rollback, reason = applier._should_rollback(validation)
            assert should_rollback is True
            assert reason == RollbackReason.VALIDATION_FAILED

            # Case 3: New errors introduced - rollback
            validation = Mock(passed=False, new_errors_introduced=2)
            should_rollback, reason = applier._should_rollback(validation)
            assert should_rollback is True
            assert reason == RollbackReason.NEW_ERRORS_INTRODUCED


# ============================================================================
# Result Model Tests
# ============================================================================


class TestApplyResultModel:
    """Test ApplyResult model."""

    @pytest.mark.unit
    def test_apply_result_creation(self):
        """Test creating ApplyResult."""
        result = ApplyResult(
            success=True,
            files_applied=[Path("src/main.py"), Path("src/utils.py")],
            files_failed=[],
            backup_ref="stash@{0}",
        )

        assert result.success is True
        assert len(result.files_applied) == 2
        assert len(result.files_failed) == 0
        assert result.backup_ref == "stash@{0}"
        assert result.error_message is None

    @pytest.mark.unit
    def test_apply_result_with_failures(self):
        """Test ApplyResult with failures."""
        result = ApplyResult(
            success=False,
            files_applied=[Path("src/main.py")],
            files_failed=[Path("src/broken.py")],
            error_message="Failed to apply some files",
        )

        assert result.success is False
        assert len(result.files_applied) == 1
        assert len(result.files_failed) == 1
        assert "Failed to apply" in result.error_message

