"""Git worktree sandbox manager for safe AI agent execution."""

import tempfile
import uuid
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

from git import Repo, GitCommandError
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
        self.sandbox_base = Path("/tmp/stomper")
        self.sandbox_base.mkdir(exist_ok=True)
    
    def create_sandbox(self, base_branch: str = "HEAD") -> Tuple[Path, str]:
        """Create a new git worktree sandbox.
        
        Args:
            base_branch: Branch to base sandbox on (default: HEAD)
            
        Returns:
            Tuple of (sandbox_path, branch_name)
        """
        sandbox_id = f"sbx_{uuid.uuid4().hex[:8]}"
        branch_name = f"sbx/{sandbox_id}"
        sandbox_path = self.sandbox_base / sandbox_id
        
        try:
            # Create worktree with new branch
            self.repo.git.worktree("add", str(sandbox_path), "-b", branch_name, base_branch)
            
            logger.info(f"Created sandbox: {sandbox_path} (branch: {branch_name})")
            return sandbox_path, branch_name
            
        except GitCommandError as e:
            logger.error(f"Failed to create sandbox: {e}")
            raise RuntimeError(f"Failed to create git worktree: {e}")
    
    def cleanup_sandbox(self, sandbox_path: Path, branch_name: str) -> None:
        """Clean up sandbox worktree and branch.
        
        Args:
            sandbox_path: Path to sandbox directory
            branch_name: Name of the sandbox branch
        """
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
            diff = sandbox_repo.git.diff(base_branch)
            return diff
            
        except GitCommandError as e:
            logger.error(f"Failed to get sandbox diff: {e}")
            return ""
    
    def get_sandbox_status(self, sandbox_path: Path) -> Dict[str, List[str]]:
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
            
            for line in status.split('\n'):
                if not line.strip():
                    continue
                    
                status_code = line[:2]
                filename = line[3:]
                
                if status_code.startswith('M'):
                    modified.append(filename)
                elif status_code.startswith('A'):
                    added.append(filename)
                elif status_code.startswith('D'):
                    deleted.append(filename)
                elif status_code.startswith('??'):
                    untracked.append(filename)
            
            return {
                "modified": modified,
                "added": added,
                "deleted": deleted,
                "untracked": untracked
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
    
    def get_sandbox_commits(self, sandbox_path: Path, base_branch: str = "HEAD") -> List[Dict]:
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
                commit_list.append({
                    "hash": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "date": commit.committed_datetime.isoformat()
                })
            
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
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as patch_file:
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
    
    def create_sandbox_context(self, sandbox_path: Path) -> Dict[str, str]:
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


class ProjectAwareCursorClient:
    """CursorClient that works with git worktree sandboxes."""
    
    def __init__(self, sandbox_manager: SandboxManager):
        """Initialize project-aware cursor client.
        
        Args:
            sandbox_manager: Sandbox manager instance
        """
        self.sandbox_manager = sandbox_manager
        self.base_client = None  # Will be set to CursorClient instance
    
    def generate_fix_with_project_context(
        self,
        target_file: Path,
        error_context: Dict[str, Any],
        prompt: str,
        sandbox_path: Path
    ) -> str:
        """Generate fix with full project context in sandbox.
        
        Args:
            target_file: Target file to fix
            error_context: Error context information
            prompt: Fix prompt
            sandbox_path: Path to sandbox directory
            
        Returns:
            Fixed code content
        """
        # Ensure we have a base client
        if self.base_client is None:
            from .cursor_client import CursorClient
            self.base_client = CursorClient()
        
        # Handle path resolution - if target_file is already in sandbox, use it directly
        if str(target_file).startswith(str(sandbox_path)):
            sandbox_target = target_file
        else:
            # Try to resolve relative path
            try:
                sandbox_target = sandbox_path / target_file.relative_to(self.sandbox_manager.project_root)
            except ValueError:
                # If relative path fails, assume target_file is already the correct path
                sandbox_target = target_file
        
        # Construct enhanced prompt with project context
        project_context = self.sandbox_manager.create_sandbox_context(sandbox_path)
        enhanced_prompt = self._enhance_prompt_with_context(prompt, error_context, project_context)
        
        # Run cursor-cli directly in the sandbox directory
        import subprocess
        import tempfile
        
        try:
            # Run cursor-cli in the sandbox directory with non-interactive flags
            # Format: cursor-agent --print -f --output-format text agent "prompt" file_path
            cmd = [
                "cursor-agent", 
                "--print",  # Non-interactive mode (print responses)
                "-f",  # Force allow commands
                "--output-format", "text",  # Use text output format for non-interactive use
                "agent",  # Start the Cursor Agent
                enhanced_prompt,  # Prompt as positional argument
                str(sandbox_target)  # Target file path
            ]
            
            # Debug: print the command being run
            logger.info(f"Running cursor-agent command: {' '.join(cmd)}")
            logger.info(f"Working directory: {sandbox_path}")
            logger.info(f"Prompt: {enhanced_prompt[:100]}...")
            
            # Use Popen for better subprocess handling (as recommended in search results)
            process = subprocess.Popen(
                cmd,
                cwd=sandbox_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Use communicate with timeout
            try:
                stdout, stderr = process.communicate(timeout=120)
                result = type('Result', (), {
                    'returncode': process.returncode,
                    'stdout': stdout,
                    'stderr': stderr
                })()
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise subprocess.TimeoutExpired(cmd, 120)
            
            # Debug: print the result
            logger.info(f"cursor-agent return code: {result.returncode}")
            logger.info(f"cursor-agent stdout: {result.stdout[:200]}...")
            logger.info(f"cursor-agent stderr: {result.stderr[:200]}...")
            
            if result.returncode != 0:
                raise RuntimeError(f"cursor-cli execution failed: {result.stderr}")
            
            # Read the modified file
            if sandbox_target.exists():
                fixed_code = sandbox_target.read_text()
                logger.info(f"Successfully read modified file: {len(fixed_code)} characters")
            else:
                raise RuntimeError("cursor-cli did not produce output file")
            
            return fixed_code
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("cursor-cli timed out after 120 seconds")
        except Exception as e:
            raise RuntimeError(f"Error running cursor-cli: {e}")

    
    def _enhance_prompt_with_context(
        self, 
        prompt: str, 
        error_context: Dict[str, Any], 
        project_context: Dict[str, str]
    ) -> str:
        """Enhance prompt with project context information.
        
        Args:
            prompt: Original prompt
            error_context: Error context
            project_context: Project file context
            
        Returns:
            Enhanced prompt with context
        """
        context_info = []
        
        # Add relevant files to context
        for file_path, content in project_context.items():
            if len(content) < 1000:  # Only include smaller files
                context_info.append(f"File: {file_path}\n```python\n{content}\n```")
        
        enhanced_prompt = f"""
{prompt}

Project Context:
{chr(10).join(context_info)}

Error Details:
- Type: {error_context.get('error_type', 'unknown')}
- Message: {error_context.get('message', '')}
- File: {error_context.get('file', '')}
- Line: {error_context.get('line', '')}

Please fix the error while considering the full project context.
"""
        
        return enhanced_prompt.strip()
