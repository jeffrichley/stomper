"""Git-based file discovery for Stomper."""

from pathlib import Path
from typing import Optional, Set

from git import Repo, InvalidGitRepositoryError
from rich.console import Console

console = Console()


class GitError(Exception):
    """Exception raised for git-related errors."""
    pass


class GitDiscovery:
    """Git-based file discovery for finding changed, staged, or diff files."""
    
    def __init__(self, project_root: Path):
        """Initialize git discovery for the given project root."""
        self.project_root = project_root
        self._validate_git_repo()
    
    def _validate_git_repo(self) -> None:
        """Validate that we're in a git repository."""
        try:
            self.repo = Repo(self.project_root)
        except InvalidGitRepositoryError:
            raise GitError("Not in a git repository")
    
    def get_changed_files(self) -> Set[Path]:
        """Get files that have been changed (modified, added, deleted) but not staged."""
        try:
            # Get unstaged changes (working tree vs index)
            changed_items = self.repo.index.diff(None)
            files = set()
            
            for item in changed_items:
                file_path = self.project_root / item.a_path
                if file_path.is_file():
                    files.add(file_path)
            
            return files
        except Exception as e:
            raise GitError(f"Failed to get changed files: {e}")
    
    def get_staged_files(self) -> Set[Path]:
        """Get files that are staged for commit."""
        try:
            # Get staged changes (index vs HEAD)
            staged_items = self.repo.index.diff("HEAD")
            files = set()
            
            for item in staged_items:
                file_path = self.project_root / item.a_path
                if file_path.is_file():
                    files.add(file_path)
            
            return files
        except Exception as e:
            raise GitError(f"Failed to get staged files: {e}")
    
    def get_diff_files(self, branch: str = "main") -> Set[Path]:
        """Get files that differ between current branch and the specified branch."""
        try:
            # Check if branch exists (try origin/ prefix first, then direct)
            try:
                self.repo.git.rev_parse(f"origin/{branch}")
                branch_ref = f"origin/{branch}"
            except:
                try:
                    self.repo.git.rev_parse(branch)
                    branch_ref = branch
                except:
                    raise GitError(f"Branch '{branch}' not found")
            
            # Get diff between current branch and the specified branch
            diff_output = self.repo.git.diff("--name-only", "--diff-filter=ACDMR", f"{branch_ref}...HEAD")
            
            if not diff_output.strip():
                return set()
            
            files = set()
            for line in diff_output.strip().split('\n'):
                if line.strip():
                    file_path = self.project_root / line.strip()
                    if file_path.is_file():
                        files.add(file_path)
            
            return files
        except Exception as e:
            if "Branch" in str(e):
                raise e
            raise GitError(f"Failed to get diff files: {e}")
    
    def get_all_changed_files(self) -> Set[Path]:
        """Get all changed files (both staged and unstaged)."""
        staged_files = self.get_staged_files()
        changed_files = self.get_changed_files()
        return staged_files | changed_files
    
    def get_untracked_files(self) -> Set[Path]:
        """Get untracked files."""
        try:
            untracked_files = set()
            for file_path in self.repo.untracked_files:
                full_path = self.project_root / file_path
                if full_path.is_file():
                    untracked_files.add(full_path)
            return untracked_files
        except Exception as e:
            raise GitError(f"Failed to get untracked files: {e}")
    
    def filter_python_files(self, files: Set[Path]) -> Set[Path]:
        """Filter to only Python files."""
        return {f for f in files if f.suffix == '.py'}
    
    def get_file_status(self, file_path: Path) -> str:
        """Get the git status of a specific file."""
        try:
            relative_path = file_path.relative_to(self.project_root)
            
            # Check if file is staged
            try:
                staged_items = self.repo.index.diff("HEAD")
                for item in staged_items:
                    if item.a_path == str(relative_path):
                        return "staged"
            except:
                pass
            
            # Check if file is modified (unstaged)
            try:
                changed_items = self.repo.index.diff(None)
                for item in changed_items:
                    if item.a_path == str(relative_path):
                        return "modified"
            except:
                pass
            
            # Check if file is untracked
            if str(relative_path) in self.repo.untracked_files:
                return "untracked"
            
            return "clean"
        except Exception:
            return "unknown"
    
    def is_dirty(self, include_untracked: bool = True) -> bool:
        """Check if the repository has any changes."""
        try:
            return self.repo.is_dirty(untracked_files=include_untracked)
        except Exception:
            return False


def discover_git_files(
    project_root: Path,
    git_changed: bool = False,
    git_staged: bool = False,
    git_diff: Optional[str] = None,
    python_only: bool = True
) -> Set[Path]:
    """
    Discover files based on git status.
    
    Args:
        project_root: Root of the project
        git_changed: Include changed (unstaged) files
        git_staged: Include staged files
        git_diff: Include files changed vs specified branch
        python_only: Only return Python files
    
    Returns:
        Set of file paths
    """
    try:
        git_discovery = GitDiscovery(project_root)
        files = set()
        
        if git_changed:
            files.update(git_discovery.get_changed_files())
        
        if git_staged:
            files.update(git_discovery.get_staged_files())
        
        if git_diff:
            files.update(git_discovery.get_diff_files(git_diff))
        
        if python_only:
            files = git_discovery.filter_python_files(files)
        
        return files
        
    except GitError as e:
        console.print(f"[red]Git Error: {e}[/red]")
        console.print("[yellow]Falling back to processing all files in project[/yellow]")
        return set()


def print_git_summary(files: Set[Path], git_changed: bool, git_staged: bool, git_diff: Optional[str]) -> None:
    """Print a summary of git-based file discovery."""
    if not files:
        console.print("[yellow]No git-tracked files found to process[/yellow]")
        return
    
    # Group files by status
    try:
        git_discovery = GitDiscovery(Path.cwd())
        staged_files = []
        changed_files = []
        unknown_files = []
        
        for file_path in files:
            status = git_discovery.get_file_status(file_path)
            if status == "staged":
                staged_files.append(file_path)
            elif status == "modified":
                changed_files.append(file_path)
            else:
                unknown_files.append(file_path)
        
        # Create summary
        summary_parts = []
        if git_changed and changed_files:
            summary_parts.append(f"{len(changed_files)} changed files")
        if git_staged and staged_files:
            summary_parts.append(f"{len(staged_files)} staged files")
        if git_diff and unknown_files:
            summary_parts.append(f"{len(unknown_files)} diff files vs {git_diff}")
        
        if summary_parts:
            summary = " + ".join(summary_parts)
            console.print(f"[green]Git Discovery: Found {len(files)} files ({summary})[/green]")
        else:
            console.print(f"[green]Git Discovery: Found {len(files)} files[/green]")
            
    except GitError:
        console.print(f"[green]Git Discovery: Found {len(files)} files[/green]")
