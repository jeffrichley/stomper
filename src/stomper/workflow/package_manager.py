"""Package manager strategy pattern for dependency installation in sandboxes."""

import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class PackageManager(ABC):
    """Abstract base class for package managers."""

    @abstractmethod
    def detect(self, project_root: Path) -> bool:
        """Detect if this package manager is used in project.
        
        Args:
            project_root: Root directory of the project
            
        Returns:
            True if this package manager is detected, False otherwise
        """
        pass

    @abstractmethod
    def install_dependencies(self, working_dir: Path) -> bool:
        """Install dependencies in working directory.
        
        Args:
            working_dir: Directory where dependencies should be installed
            
        Returns:
            True if installation succeeded, False otherwise
        """
        pass


class UvPackageManager(PackageManager):
    """UV package manager implementation."""

    def detect(self, project_root: Path) -> bool:
        """Detect if project uses UV (checks for uv.lock)."""
        return (project_root / "uv.lock").exists()

    def install_dependencies(self, working_dir: Path) -> bool:
        """Install dependencies using uv sync."""
        try:
            logger.info(f"Running 'uv sync' in {working_dir}")
            result = subprocess.run(
                ["uv", "sync"],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("✅ Dependencies installed successfully")
                return True
            else:
                logger.error(f"❌ uv sync failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ uv sync timed out after 5 minutes")
            return False
        except FileNotFoundError:
            logger.error("❌ uv command not found")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to install dependencies: {e}")
            return False


def get_package_manager(project_root: Path) -> PackageManager | None:
    """Auto-detect and return appropriate package manager.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        PackageManager instance if detected, None otherwise
    """
    managers = [
        UvPackageManager(),
        # Future: PoetryPackageManager(), PipPackageManager()
    ]
    
    for manager in managers:
        if manager.detect(project_root):
            logger.debug(f"Detected package manager: {manager.__class__.__name__}")
            return manager
    
    logger.warning("No package manager detected")
    return None

