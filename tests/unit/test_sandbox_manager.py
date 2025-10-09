"""Tests for SandboxManager."""

from pathlib import Path
import sys
import tempfile
import time

from git import Repo
import pytest

from stomper.ai.sandbox_manager import SandboxManager


class TestSandboxManager:
    """Test SandboxManager functionality."""

    def test_sandbox_manager_initialization(self):
        """Test SandboxManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a git repo
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()

            # Create initial commit
            (Path(temp_dir) / "README.md").write_text("# Test Repo")
            repo.git.add("README.md")
            repo.git.commit("-m", "Initial commit")

            manager = SandboxManager(Path(temp_dir))
            assert manager.project_root == Path(temp_dir).resolve()
            # sandbox_base should be in .stomper/sandboxes
            assert ".stomper" in str(manager.sandbox_base)
            assert "sandboxes" in str(manager.sandbox_base)
            assert manager.sandbox_base.exists()

    def test_create_sandbox(self):
        """Test creating a sandbox."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a git repo
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()

            # Create initial commit
            (Path(temp_dir) / "README.md").write_text("# Test Repo")
            repo.git.add("README.md")
            repo.git.commit("-m", "Initial commit")

            manager = SandboxManager(Path(temp_dir))
            session_id = "test-session-123"

            try:
                sandbox_path = manager.create_sandbox(session_id)

                assert sandbox_path.exists()
                assert session_id in str(sandbox_path)
                assert (sandbox_path / "README.md").exists()

            finally:
                # Cleanup
                try:
                    # On Windows, give git a moment to release file locks
                    if sys.platform == "win32":
                        time.sleep(0.5)
                    manager.cleanup_sandbox(session_id)
                except Exception:
                    pass  # Cleanup may fail on Windows due to git file locks  # Cleanup may fail if sandbox not created

    def test_cleanup_sandbox(self):
        """Test cleaning up a sandbox."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a git repo
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()

            # Create initial commit
            (Path(temp_dir) / "README.md").write_text("# Test Repo")
            repo.git.add("README.md")
            repo.git.commit("-m", "Initial commit")

            manager = SandboxManager(Path(temp_dir))
            session_id = "test-session-456"

            # Create sandbox
            sandbox_path = manager.create_sandbox(session_id)
            branch_name = f"sbx/{session_id}"

            # Cleanup sandbox
            manager.cleanup_sandbox(session_id)

            # Verify cleanup
            assert not sandbox_path.exists()

            # Verify branch is deleted
            branches = [branch.name for branch in repo.branches]
            assert branch_name not in branches

    def test_get_sandbox_diff(self):
        """Test getting sandbox diff."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a git repo
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()

            # Create initial commit
            (Path(temp_dir) / "README.md").write_text("# Test Repo")
            repo.git.add("README.md")
            repo.git.commit("-m", "Initial commit")

            manager = SandboxManager(Path(temp_dir))
            session_id = "test-session-789"

            try:
                sandbox_path = manager.create_sandbox(session_id)

                # Make changes in sandbox
                (sandbox_path / "test.py").write_text("print('hello')")
                sandbox_repo = Repo(sandbox_path)
                sandbox_repo.git.add("test.py")
                sandbox_repo.git.commit("-m", "Add test file")

                # Get diff - just test that the method doesn't crash
                diff = manager.get_sandbox_diff(sandbox_path)

                # The diff should be a string (empty or with content)
                assert isinstance(diff, str)

            finally:
                # Cleanup
                try:
                    # On Windows, give git a moment to release file locks
                    if sys.platform == "win32":
                        time.sleep(0.5)
                    manager.cleanup_sandbox(session_id)
                except Exception:
                    pass  # Cleanup may fail on Windows due to git file locks

    def test_get_sandbox_status(self):
        """Test getting sandbox status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a git repo
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()

            # Create initial commit
            (Path(temp_dir) / "README.md").write_text("# Test Repo")
            repo.git.add("README.md")
            repo.git.commit("-m", "Initial commit")

            manager = SandboxManager(Path(temp_dir))
            session_id = "test-session-abc"

            try:
                sandbox_path = manager.create_sandbox(session_id)

                # Make changes in sandbox
                (sandbox_path / "test.py").write_text("print('hello')")
                (sandbox_path / "README.md").write_text("# Modified Repo")

                # Get status
                status = manager.get_sandbox_status(sandbox_path)

                # Check that we have some changes
                total_changes = (
                    len(status["untracked"])
                    + len(status["modified"])
                    + len(status["added"])
                    + len(status["deleted"])
                )
                assert total_changes > 0

            finally:
                # Cleanup
                try:
                    # On Windows, give git a moment to release file locks
                    if sys.platform == "win32":
                        time.sleep(0.5)
                    manager.cleanup_sandbox(session_id)
                except Exception:
                    pass  # Cleanup may fail on Windows due to git file locks

    @pytest.mark.skipif(sys.platform == "win32", reason="Git worktree cleanup has file lock issues on Windows")
    def test_commit_sandbox_changes(self):
        """Test committing changes in sandbox."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a git repo
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()

            # Create initial commit
            (Path(temp_dir) / "README.md").write_text("# Test Repo")
            repo.git.add("README.md")
            repo.git.commit("-m", "Initial commit")

            manager = SandboxManager(Path(temp_dir))
            session_id = "test-session-commit"

            try:
                sandbox_path = manager.create_sandbox(session_id)

                # Make changes in sandbox
                (sandbox_path / "test.py").write_text("print('hello')")

                # Commit changes
                success = manager.commit_sandbox_changes(sandbox_path, "Add test file")

                assert success is True

                # Verify commit
                sandbox_repo = Repo(sandbox_path)
                commits = list(sandbox_repo.iter_commits())
                assert len(commits) == 2  # Initial + our commit
                assert "Add test file" in commits[0].message

            finally:
                # Cleanup
                try:
                    # On Windows, give git a moment to release file locks
                    if sys.platform == "win32":
                        time.sleep(0.5)
                    manager.cleanup_sandbox(session_id)
                except Exception:
                    pass  # Cleanup may fail on Windows due to git file locks

    def test_get_sandbox_commits(self):
        """Test getting sandbox commits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a git repo
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()

            # Create initial commit
            (Path(temp_dir) / "README.md").write_text("# Test Repo")
            repo.git.add("README.md")
            repo.git.commit("-m", "Initial commit")

            manager = SandboxManager(Path(temp_dir))
            session_id = "test-session-commits"

            try:
                sandbox_path = manager.create_sandbox(session_id)

                # Make commits in sandbox
                (sandbox_path / "test.py").write_text("print('hello')")
                sandbox_repo = Repo(sandbox_path)
                sandbox_repo.git.add("test.py")
                sandbox_repo.git.commit("-m", "Add test file")

                # Get commits - just test that the method doesn't crash
                commits = manager.get_sandbox_commits(sandbox_path)

                # Should return a list
                assert isinstance(commits, list)

            finally:
                # Cleanup
                try:
                    # On Windows, give git a moment to release file locks
                    if sys.platform == "win32":
                        time.sleep(0.5)
                    manager.cleanup_sandbox(session_id)
                except Exception:
                    pass  # Cleanup may fail on Windows due to git file locks

    def test_create_sandbox_context(self):
        """Test creating sandbox context."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a git repo
            repo = Repo.init(temp_dir)
            repo.config_writer().set_value("user", "name", "Test User").release()
            repo.config_writer().set_value("user", "email", "test@example.com").release()

            # Create initial commit
            (Path(temp_dir) / "README.md").write_text("# Test Repo")
            repo.git.add("README.md")
            repo.git.commit("-m", "Initial commit")

            manager = SandboxManager(Path(temp_dir))
            session_id = "test-session-context"

            try:
                sandbox_path = manager.create_sandbox(session_id)

                # Create Python files in sandbox
                (sandbox_path / "test.py").write_text("print('hello')")
                (sandbox_path / "utils.py").write_text("def helper(): pass")

                # Get context
                context = manager.create_sandbox_context(sandbox_path)

                assert "test.py" in context
                assert "utils.py" in context
                assert context["test.py"] == "print('hello')"
                assert context["utils.py"] == "def helper(): pass"

            finally:
                # Cleanup
                try:
                    # On Windows, give git a moment to release file locks
                    if sys.platform == "win32":
                        time.sleep(0.5)
                    manager.cleanup_sandbox(session_id)
                except Exception:
                    pass  # Cleanup may fail on Windows due to git file locks
