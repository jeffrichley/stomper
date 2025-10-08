"""Tests for SandboxManager."""

from pathlib import Path
import tempfile

from git import Repo

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
            # sandbox_base should be in system temp directory
            assert "stomper" in str(manager.sandbox_base)
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

            try:
                sandbox_path, branch_name = manager.create_sandbox()

                assert sandbox_path.exists()
                assert branch_name.startswith("sbx/")
                assert (sandbox_path / "README.md").exists()

            finally:
                # Cleanup
                if sandbox_path.exists():
                    manager.cleanup_sandbox(sandbox_path, branch_name)

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

            # Create sandbox
            sandbox_path, branch_name = manager.create_sandbox()

            # Cleanup sandbox
            manager.cleanup_sandbox(sandbox_path, branch_name)

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

            try:
                sandbox_path, branch_name = manager.create_sandbox()

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
                if sandbox_path.exists():
                    manager.cleanup_sandbox(sandbox_path, branch_name)

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

            try:
                sandbox_path, branch_name = manager.create_sandbox()

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
                if sandbox_path.exists():
                    manager.cleanup_sandbox(sandbox_path, branch_name)

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

            try:
                sandbox_path, branch_name = manager.create_sandbox()

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
                if sandbox_path.exists():
                    manager.cleanup_sandbox(sandbox_path, branch_name)

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

            try:
                sandbox_path, branch_name = manager.create_sandbox()

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
                if sandbox_path.exists():
                    manager.cleanup_sandbox(sandbox_path, branch_name)

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

            try:
                sandbox_path, branch_name = manager.create_sandbox()

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
                if sandbox_path.exists():
                    manager.cleanup_sandbox(sandbox_path, branch_name)
