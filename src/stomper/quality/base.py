"""Base quality tool interface for Stomper."""

from abc import ABC, abstractmethod
from pathlib import Path
import shutil
import subprocess
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from rich.console import Console

console = Console()


def detect_project_manager(project_root: Path) -> str:
    """Detect if running in UV, Poetry, or pip project.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        Project manager type: "uv", "poetry", or "pip"
    """
    # Check for UV lock file
    if (project_root / "uv.lock").exists():
        return "uv"
    # Check for Poetry lock file
    elif (project_root / "poetry.lock").exists():
        return "poetry"
    return "pip"


class QualityError(BaseModel):
    """Represents a quality error from a tool."""

    tool: str = Field(description="Name of the quality tool that found this error")
    file: Path = Field(description="Path to the file containing the error")
    line: int = Field(ge=1, description="Line number of the error")
    column: int = Field(ge=0, description="Column number of the error")
    code: str = Field(description="Error code (e.g., E501, F401)")
    message: str = Field(description="Human-readable error message")
    severity: Literal["error", "warning", "info"] = Field(description="Error severity level")
    auto_fixable: bool = Field(description="Whether this error can be automatically fixed")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BaseQualityTool(ABC):
    """Base class for quality tools integration."""

    def __init__(self, tool_name: str):
        """Initialize the quality tool.

        Args:
            tool_name: Name of the tool (e.g., 'ruff', 'mypy')
        """
        self.tool_name = tool_name
        self._command_cache: str | None = None

    @property
    @abstractmethod
    def command(self) -> str:
        """Get the command to run this tool."""
        pass

    @property
    @abstractmethod
    def json_output_flag(self) -> str:
        """Get the flag for JSON output."""
        pass

    @abstractmethod
    def parse_errors(self, json_output: str, project_root: Path) -> list[QualityError]:
        """Parse JSON output into QualityError objects.

        Args:
            json_output: Raw JSON output from the tool
            project_root: Root directory of the project

        Returns:
            List of QualityError objects
        """
        pass

    def is_available(self) -> bool:
        """Check if the tool is available in PATH or via package manager.

        Returns:
            True if tool is available, False otherwise
        """
        # First check if tool is directly available in PATH
        if shutil.which(self.command) is not None:
            return True
        
        # Check if we can run it via uv/poetry
        # Try uv run (if uv is available)
        if shutil.which("uv") is not None:
            try:
                result = subprocess.run(
                    ["uv", "run", "--", self.command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        # Try poetry run (if poetry is available)
        if shutil.which("poetry") is not None:
            try:
                result = subprocess.run(
                    ["poetry", "run", self.command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0:
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        return False

    def _build_command(self, project_root: Path, extra_args: list[str] | None = None) -> list[str]:
        """Build the command to run the tool with appropriate package manager.
        
        Args:
            project_root: Root directory of the project
            extra_args: Additional arguments to append
            
        Returns:
            List of command parts to execute
        """
        cmd: list[str] = []
        
        # Detect project manager
        project_manager = detect_project_manager(project_root)
        
        # Check if tool is directly available
        tool_in_path = shutil.which(self.command) is not None
        
        # Build command based on availability
        if tool_in_path:
            # Tool is in PATH, use it directly
            cmd = [self.command]
        elif project_manager == "uv" and shutil.which("uv") is not None:
            # Use uv run
            cmd = ["uv", "run", "--", self.command]
        elif project_manager == "poetry" and shutil.which("poetry") is not None:
            # Use poetry run
            cmd = ["poetry", "run", self.command]
        else:
            # Fallback to direct command (will likely fail, but let it fail with clear error)
            cmd = [self.command]
        
        # Add extra args
        if extra_args:
            cmd.extend(extra_args)
        
        return cmd

    def run_tool(self, target_path: Path, project_root: Path) -> list[QualityError]:
        """Run the quality tool and return parsed errors.

        Args:
            target_path: Path to analyze (file or directory)
            project_root: Root directory of the project

        Returns:
            List of QualityError objects

        Raises:
            subprocess.CalledProcessError: If tool execution fails
            ValueError: If tool output cannot be parsed
        """
        if not self.is_available():
            console.print(f"[yellow]Warning: {self.tool_name} is not available[/yellow]")
            return []

        # Build command with package manager detection
        args = self._get_base_args() + [str(target_path)]
        cmd = self._build_command(project_root, args)

        try:
            # Run the tool
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',  # Force UTF-8 encoding (fixes Windows cp1252 issues)
                cwd=project_root,
                check=False,  # Don't raise exception on non-zero exit
            )

            # Check if tool failed unexpectedly
            if result.returncode != 0 and result.returncode != 1:
                # Exit code 1 is expected for tools that found issues
                console.print(
                    f"[red]Error running {self.tool_name}: Exit code {result.returncode}[/red]"
                )
                console.print(f"[red]Command: {' '.join(cmd)}[/red]")
                console.print(f"[red]Output: {result.stdout}[/red]")
                if result.stderr:
                    console.print(f"[red]Error: {result.stderr}[/red]")
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, result.stdout, result.stderr
                )

            # Parse output (even if exit code is 1, stdout might contain valid results)
            return self.parse_errors(result.stdout, project_root)

        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error running {self.tool_name}: {e}[/red]")
            console.print(f"[red]Command: {' '.join(cmd)}[/red]")
            console.print(f"[red]Output: {e.stdout}[/red]")
            if e.stderr:
                console.print(f"[red]Error: {e.stderr}[/red]")
            raise

    def _get_base_args(self) -> list[str]:
        """Get base arguments for the tool command.

        Returns:
            List of base arguments
        """
        return [self.json_output_flag]

    def run_tool_with_patterns(
        self, include_patterns: list[str], exclude_patterns: list[str], project_root: Path
    ) -> list[QualityError]:
        """Run tool with its own configuration (no Stomper pattern injection).

        This method respects the "don't surprise me" rule by letting tools
        use their own configuration files for discovery and exclusion.

        Args:
            include_patterns: Ignored - tools use their own configs
            exclude_patterns: Ignored - tools use their own configs
            project_root: Root directory of the project

        Returns:
            List of QualityError objects

        Raises:
            subprocess.CalledProcessError: If tool execution fails
            ValueError: If tool output cannot be parsed
        """
        if not self.is_available():
            console.print(f"[yellow]Warning: {self.tool_name} is not available[/yellow]")
            return []

        # Build command using tool's own configuration with package manager detection
        # No Stomper pattern injection - respect tool configs
        args = self._get_base_args() + self._get_tool_native_args(project_root)
        cmd = self._build_command(project_root, args)

        try:
            # Run the tool
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',  # Force UTF-8 encoding (fixes Windows cp1252 issues)
                cwd=project_root,
                check=False,  # Don't raise exception on non-zero exit
            )

            # Check if tool failed unexpectedly
            if result.returncode != 0 and result.returncode != 1:
                # Exit code 1 is expected for tools that found issues
                console.print(
                    f"[red]Error running {self.tool_name}: Exit code {result.returncode}[/red]"
                )
                console.print(f"[red]Command: {' '.join(cmd)}[/red]")
                console.print(f"[red]Output: {result.stdout}[/red]")
                if result.stderr:
                    console.print(f"[red]Error: {result.stderr}[/red]")
                raise subprocess.CalledProcessError(
                    result.returncode, cmd, result.stdout, result.stderr
                )

            # Parse output (even if exit code is 1, stdout might contain valid results)
            return self.parse_errors(result.stdout, project_root)

        except subprocess.CalledProcessError as e:
            console.print(f"[red]Error running {self.tool_name}: {e}[/red]")
            console.print(f"[red]Command: {' '.join(cmd)}[/red]")
            console.print(f"[red]Output: {e.stdout}[/red]")
            if e.stderr:
                console.print(f"[red]Error: {e.stderr}[/red]")
            raise

    def _get_tool_native_args(self, project_root: Path) -> list[str]:
        """Get tool's native arguments (respects tool's own configuration).

        Args:
            project_root: Root directory of the project

        Returns:
            List of command arguments using tool's own configuration
        """
        # Check for tool's configuration file
        config_file = self.discover_tool_config(project_root)

        if config_file:
            # Tool has its own config - use it with no Stomper overrides
            return ["."]  # Let tool use its own discovery
        else:
            # No tool config found - use Stomper's baseline
            return self._get_stomper_baseline_args(project_root)

    def discover_tool_config(self, project_root: Path) -> Path | None:
        """Discover tool's configuration file using tool's own discovery logic.

        Args:
            project_root: Root directory of the project

        Returns:
            Path to configuration file if found, None otherwise
        """
        # Default implementation - check for common config files
        # Override in subclasses for tool-specific discovery logic
        return None

    def _get_stomper_baseline_args(self, project_root: Path) -> list[str]:
        """Get Stomper's baseline configuration arguments.

        Args:
            project_root: Root directory of the project

        Returns:
            List of command arguments using Stomper's baseline configuration
        """
        # Default implementation - use current directory
        # Override in subclasses for tool-specific baseline configuration
        return ["."]

    def _get_pattern_args(
        self, include_patterns: list[str], exclude_patterns: list[str]
    ) -> list[str]:
        """Get pattern-specific arguments for the tool (DEPRECATED).

        This method is deprecated in favor of _get_tool_native_args() to respect
        the "don't surprise me" rule.

        Args:
            include_patterns: Patterns to include
            exclude_patterns: Patterns to exclude

        Returns:
            List of command arguments for pattern-based execution
        """
        # Default implementation - use current directory
        # Override in subclasses for tool-specific pattern handling
        return ["."]

    def get_config_file(self, project_root: Path) -> Path | None:
        """Get the configuration file for this tool.

        Args:
            project_root: Root directory of the project

        Returns:
            Path to config file if found, None otherwise
        """
        # Default implementation - override in subclasses
        return None
