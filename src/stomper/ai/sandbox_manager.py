"""Git worktree sandbox manager for safe AI agent execution."""

import logging
from pathlib import Path
import tempfile

from git import Repo
from git.exc import GitCommandError

logger = logging.getLogger(__name__)


class SandboxManager:
    """Manages git worktree sandboxes for safe AI agent execution."""

    def __init__(self, project_root: Path):
        """Initialize sandbox manager.

        Args:
            project_root: Root path of the git repository
        """
        self.project_root = Path(project_root).resolve()
        self.repo = Repo(self.project_root)
        self.sandbox_base = self.project_root / ".stomper" / "sandboxes"
        self.sandbox_base.mkdir(parents=True, exist_ok=True)
        # Track session_id to path/branch mappings
        self._session_map: dict[str, tuple[Path, str]] = {}

    def create_sandbox(self, session_id: str, base_branch: str = "HEAD") -> Path:
        """Create a new git worktree sandbox.

        Args:
            session_id: Unique session identifier
            base_branch: Branch to base sandbox on (default: HEAD)

        Returns:
            Path to sandbox directory
        """
        branch_name = f"sbx/{session_id}"
        sandbox_path = self.sandbox_base / session_id

        try:
            # Create worktree with new branch
            self.repo.git.worktree("add", str(sandbox_path), "-b", branch_name, base_branch)

            # Store mapping
            self._session_map[session_id] = (sandbox_path, branch_name)

            logger.info(f"Created sandbox: {sandbox_path} (branch: {branch_name})")
            return sandbox_path

        except GitCommandError as e:
            logger.error(f"Failed to create sandbox: {e}")
            raise RuntimeError(f"Failed to create git worktree: {e}")

    def cleanup_sandbox(self, session_id: str) -> None:
        """Clean up sandbox worktree and branch.

        Args:
            session_id: Session identifier
        """
        # Get sandbox info from mapping
        if session_id not in self._session_map:
            sandbox_path = self.sandbox_base / session_id
            branch_name = f"sbx/{session_id}"
        else:
            sandbox_path, branch_name = self._session_map[session_id]

        try:
            # Remove worktree
            self.repo.git.worktree("remove", str(sandbox_path), "--force")
            logger.info(f"Removed worktree: {sandbox_path}")

        except GitCommandError as e:
            logger.warning(f"Failed to remove worktree: {e}")

        try:
            # Delete branch
            self.repo.git.branch("-D", branch_name)
            logger.info(f"Deleted branch: {branch_name}")

        except GitCommandError as e:
            logger.warning(f"Failed to delete branch {branch_name}: {e}")

        # Remove from mapping
        if session_id in self._session_map:
            del self._session_map[session_id]

    def get_sandbox_diff(self, sandbox_path: Path, base_branch: str = "HEAD") -> str:
        """Get diff between sandbox and base branch.

        Args:
            sandbox_path: Path to sandbox directory
            base_branch: Base branch to compare against

        Returns:
            Git diff as string
        """
        try:
            sandbox_repo = Repo(sandbox_path)
            diff: str = sandbox_repo.git.diff(base_branch)
            return diff

        except GitCommandError as e:
            logger.error(f"Failed to get sandbox diff: {e}")
            return ""

    def get_sandbox_status(self, sandbox_path: Path) -> dict[str, list[str]]:
        """Get status of files in sandbox.

        Args:
            sandbox_path: Path to sandbox directory

        Returns:
            Dictionary with status categories and file lists
        """
        try:
            sandbox_repo = Repo(sandbox_path)
            status = sandbox_repo.git.status("--porcelain")

            # Parse status output
            modified = []
            added = []
            deleted = []
            untracked = []

            for line in status.split("\n"):
                if not line.strip():
                    continue

                status_code = line[:2]
                filename = line[3:]

                # Git status codes: first char = index, second char = working tree
                # M = modified, A = added, D = deleted, ?? = untracked
                if "M" in status_code:
                    modified.append(filename)
                elif "A" in status_code:
                    added.append(filename)
                elif "D" in status_code:
                    deleted.append(filename)
                elif status_code == "??":
                    untracked.append(filename)

            return {
                "modified": modified,
                "added": added,
                "deleted": deleted,
                "untracked": untracked,
            }

        except GitCommandError as e:
            logger.error(f"Failed to get sandbox status: {e}")
            return {"modified": [], "added": [], "deleted": [], "untracked": []}

    def commit_sandbox_changes(self, sandbox_path: Path, message: str) -> bool:
        """Commit changes in sandbox.

        Args:
            sandbox_path: Path to sandbox directory
            message: Commit message

        Returns:
            True if commit successful, False otherwise
        """
        try:
            sandbox_repo = Repo(sandbox_path)

            # Add all changes
            sandbox_repo.git.add(".")

            # Check if there are changes to commit
            if not sandbox_repo.is_dirty() and not sandbox_repo.untracked_files:
                logger.info("No changes to commit in sandbox")
                return False

            # Commit changes
            sandbox_repo.git.commit("-m", message)
            logger.info(f"Committed changes in sandbox: {message}")
            return True

        except GitCommandError as e:
            logger.error(f"Failed to commit sandbox changes: {e}")
            return False

    def get_sandbox_commits(self, sandbox_path: Path, base_branch: str = "HEAD") -> list[dict]:
        """Get commits made in sandbox since base branch.

        Args:
            sandbox_path: Path to sandbox directory
            base_branch: Base branch to compare against

        Returns:
            List of commit dictionaries
        """
        try:
            sandbox_repo = Repo(sandbox_path)

            # Get commits between base and current
            commits = list(sandbox_repo.iter_commits(f"{base_branch}..HEAD"))

            commit_list = []
            for commit in commits:
                commit_list.append(
                    {
                        "hash": commit.hexsha,
                        "message": commit.message.strip(),
                        "author": commit.author.name,
                        "date": commit.committed_datetime.isoformat(),
                    }
                )

            return commit_list

        except GitCommandError as e:
            logger.error(f"Failed to get sandbox commits: {e}")
            return []

    def apply_sandbox_patch(self, target_repo: Repo, patch_content: str) -> bool:
        """Apply patch from sandbox to target repository.

        Args:
            target_repo: Target repository to apply patch to
            patch_content: Patch content as string

        Returns:
            True if patch applied successfully, False otherwise
        """
        try:
            # Create temporary patch file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as patch_file:
                patch_file.write(patch_content)
                patch_path = patch_file.name

            try:
                # Apply patch
                target_repo.git.apply(patch_path)
                logger.info("Successfully applied sandbox patch")
                return True

            finally:
                # Clean up patch file
                Path(patch_path).unlink()

        except GitCommandError as e:
            logger.error(f"Failed to apply sandbox patch: {e}")
            return False

    def create_sandbox_context(self, sandbox_path: Path) -> dict[str, str]:
        """Create context map of files in sandbox.

        Args:
            sandbox_path: Path to sandbox directory

        Returns:
            Dictionary mapping file paths to content
        """
        context = {}

        # Get all Python files in sandbox
        for py_file in sandbox_path.rglob("*.py"):
            try:
                relative_path = py_file.relative_to(sandbox_path)
                context[str(relative_path)] = py_file.read_text()
            except Exception as e:
                logger.warning(f"Failed to read file {py_file}: {e}")

        return context

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup any remaining sandboxes."""
        # This could be enhanced to track and cleanup sandboxes
        pass
