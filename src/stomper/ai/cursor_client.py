"""Cursor CLI integration for AI-powered code fixing with project context."""

import json
import logging
import os
import platform
import select
import shlex
import subprocess
import tempfile
import time
import uuid
from pathlib import Path, PureWindowsPath
from typing import Any

from .base import AgentCapabilities, AgentInfo, BaseAIAgent
from .prompt_generator import PromptGenerator

logger = logging.getLogger(__name__)


def _is_wsl() -> bool:
    """Check if currently running inside WSL.
    
    Returns:
        True if running in WSL, False otherwise
    """
    try:
        # Check for WSL-specific files/environment
        if os.path.exists("/proc/version"):
            with open("/proc/version", "r", encoding="utf-8") as f:
                return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
        return False
    except Exception:
        return False


def _is_windows() -> bool:
    """Check if running on Windows (not WSL).
    
    Returns:
        True if running on native Windows, False otherwise
    """
    return platform.system() == "Windows"


def _is_wsl_available() -> bool:
    """Check if WSL is available on Windows.
    
    Returns:
        True if WSL is installed and available, False otherwise
    """
    if not _is_windows():
        return False
    
    try:
        result = subprocess.run(
            ["wsl", "--status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def _windows_path_to_wsl(windows_path: str) -> str:
    """Convert Windows path to WSL path.
    
    Args:
        windows_path: Windows path (e.g., E:\\workspaces\\project)
    
    Returns:
        WSL path (e.g., /mnt/e/workspaces/project)
    """
    path = Path(windows_path)
    
    # Get the drive letter and path components
    parts = path.parts
    if len(parts) == 0:
        return windows_path
    
    # Extract drive letter (e.g., 'E:')
    drive = parts[0].rstrip(":\\").lower()
    
    # Convert to WSL format: /mnt/e/...
    wsl_parts = ["/mnt", drive] + list(parts[1:])
    wsl_path = "/".join(wsl_parts)
    
    return wsl_path


class CursorClient(BaseAIAgent):
    """Cursor CLI client with full project context and git sandbox support."""

    def __init__(self, sandbox_manager, api_key: str | None = None, timeout: int = 30):
        """Initialize Cursor CLI client with project context.

        Args:
            sandbox_manager: Sandbox manager instance for git operations
            api_key: Cursor API key (if None, will use environment variable)
            timeout: Timeout for cursor-cli commands in seconds
        """
        agent_info = AgentInfo(
            name="cursor-cli-project",
            version="1.0.0",
            description="Cursor CLI AI agent for automated code fixing with project context",
            capabilities=AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=True,
                can_fix_tests=True,
                max_context_length=8000,
                # Currently only Python is supported via Ruff, MyPy, and Drill Sergeant
                # Future: Could expand to other languages with additional tool integrations
                supported_languages=["python"],
            ),
        )
        super().__init__(agent_info)

        self.sandbox_manager = sandbox_manager
        self.api_key = api_key
        self.timeout = timeout
        self.prompt_generator = PromptGenerator()
        
        # Detect execution environment
        self.use_wsl = False
        if _is_windows() and not _is_wsl():
            # We're on native Windows, check if WSL is available
            if _is_wsl_available():
                self.use_wsl = True
                logger.info("🪟 Running on Windows - cursor-agent will be executed via WSL")
            else:
                logger.warning("⚠️ Running on Windows without WSL - cursor-agent may not be available")
        elif _is_wsl():
            logger.info("🐧 Running inside WSL - cursor-agent will execute natively")
        else:
            logger.info("🐧 Running on Unix/Linux - cursor-agent will execute natively")

        # Check availability during initialization
        if not self.is_available():
            raise RuntimeError("cursor-cli not available or not accessible")
        logger.info("✅ Cursor CLI available and ready")

    def _prepare_command(self, cmd: list[str], cwd: str) -> tuple[list[str], str]:
        """Prepare command for execution, wrapping with WSL if needed.
        
        Args:
            cmd: Command to execute (e.g., ["cursor-agent", "--version"])
            cwd: Working directory path
        
        Returns:
            Tuple of (prepared_command, prepared_cwd)
        """
        if self.use_wsl:
            # Convert Windows path to WSL path
            wsl_cwd = _windows_path_to_wsl(cwd)
            
            # Build shell command string with proper escaping
            # Use login shell (-l) to load PATH from profile (~/.bashrc, ~/.profile)
            # This ensures cursor-agent is found in ~/.local/bin or npm global paths
            escaped_cmd = " ".join(shlex.quote(arg) for arg in cmd)
            shell_cmd = f"cd {shlex.quote(wsl_cwd)} && {escaped_cmd}"
            
            # Wrap with WSL using bash login shell
            wsl_cmd = ["wsl", "bash", "-l", "-c", shell_cmd]
            
            # Use Windows path as cwd for subprocess
            return wsl_cmd, cwd
        else:
            # No transformation needed
            return cmd, cwd

    def generate_fix(self, error_context: dict[str, Any], code_context: str, prompt: str) -> str:
        """Generate fix using cursor-cli in sandbox.

        Args:
            error_context: Error details including type, location, message
            code_context: Surrounding code context
            prompt: Specific fix instructions

        Returns:
            Generated fix code as string
        """
        # Construct comprehensive prompt with error context
        full_prompt = self._construct_prompt(error_context, code_context, prompt)

        # Create a unique session ID for this fix
        session_id = f"cursor-fix-{uuid.uuid4().hex[:8]}"
        
        # Create a temporary sandbox for this fix
        sandbox_path = self.sandbox_manager.create_sandbox(session_id)

        # Write prompt to file to avoid shell escaping issues
        # Prompts often contain special characters (backticks, quotes, newlines)
        # that break bash -c even with proper escaping
        prompt_file = None
        wrapper_script = None
        
        try:
            # Create prompt file in sandbox
            prompt_file = sandbox_path / f".cursor-prompt-{session_id}.txt"
            prompt_file.write_text(full_prompt, encoding="utf-8")
            
            # Create wrapper script that sources profile and runs cursor-agent
            # This avoids complex escaping issues with bash -c
            wrapper_script = sandbox_path / f".cursor-run-{session_id}.sh"
            
            # Use explicit path to cursor-agent since we know where it is
            # Sourcing profile doesn't work reliably in non-interactive scripts
            wrapper_content = f"""#!/bin/bash
# Explicit PATH including common npm global locations
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

# Run cursor-agent with prompt from file
"$HOME/.local/bin/cursor-agent" -p --force "$(cat {prompt_file.name})"
"""
            # Write with Unix line endings (LF only, not CRLF)
            wrapper_script.write_text(wrapper_content, encoding="utf-8", newline="\n")
            wrapper_script.chmod(0o755)
            
            # Convert wrapper script path to WSL format if on Windows
            if self.use_wsl:
                wsl_sandbox = _windows_path_to_wsl(str(sandbox_path))
                wsl_script = f"{wsl_sandbox}/{wrapper_script.name}"
                cmd = ["wsl", "bash", wsl_script]
            else:
                cmd = [str(wrapper_script)]

            logger.debug(f"Running cursor-cli via wrapper script: {wrapper_script.name}")
            logger.debug(f"Prompt length: {len(full_prompt)} characters")

            # Run the wrapper script directly WITHOUT using _prepare_command
            # The wrapper script already handles everything (PATH, cd, cursor-agent)
            # Using _prepare_command would double-wrap with WSL which breaks
            result = self._run_wrapper_script(cmd, str(sandbox_path), timeout=self.timeout)

            if result["returncode"] != 0:
                stderr_text = "".join(result["stderr"])
                logger.error(f"cursor-cli failed: {stderr_text}")
                raise RuntimeError(f"cursor-cli execution failed: {stderr_text}")

            # Log completion info
            if result["result"]:
                logger.info("✅ Cursor-agent completed successfully!")
                logger.info(f"Duration: {result['result'].get('duration_ms', 0)}ms")
                logger.info(f"Events captured: {len(result['events'])}")

            # Get the fixed code from the sandbox
            # For now, return the code context (in a real implementation, we'd read the fixed file)
            # TODO: Read actual fixed file from sandbox
            return code_context

        finally:
            # Cleanup temporary files
            if prompt_file and prompt_file.exists():
                try:
                    prompt_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete prompt file: {e}")
            
            if wrapper_script and wrapper_script.exists():
                try:
                    wrapper_script.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete wrapper script: {e}")
            
            # Cleanup sandbox using session_id
            self.sandbox_manager.cleanup_sandbox(session_id)

    def _construct_prompt(
        self, error_context: dict[str, Any], code_context: str, prompt: str
    ) -> str:
        """Construct comprehensive prompt from error context and code.

        Args:
            error_context: Error details
            code_context: Code to fix
            prompt: Additional instructions

        Returns:
            Full prompt string
        """
        # Build comprehensive prompt
        parts = [prompt]

        # Add error context
        if error_context:
            parts.append("\n## Error Details:")
            for key, value in error_context.items():
                parts.append(f"- {key.replace('_', ' ').title()}: {value}")

        # Add code context
        if code_context:
            parts.append("\n## Code to Fix:")
            parts.append(f"```python\n{code_context}\n```")

        return "\n".join(parts)

    def validate_response(self, response: str) -> bool:
        """Validate AI response (required by BaseAIAgent interface).

        Args:
            response: AI-generated response to validate

        Returns:
            True if response is valid, False otherwise
        """
        # Check if response is empty or whitespace
        if not response or not response.strip():
            return False

        # Reject common error indicators
        error_indicators = [
            "error:",
            "exception:",
            "cannot fix",
            "unable to",
            "failed to",
            "could not",
        ]

        response_lower = response.lower()
        for indicator in error_indicators:
            if indicator in response_lower:
                return False

        # Reject responses that are only comments
        stripped = response.strip()
        return not (stripped.startswith("#") and "\n" not in stripped)

    def _run_wrapper_script(
        self, cmd: list[str], cwd: str, timeout: int = 30
    ) -> dict[str, Any]:
        """Run wrapper script directly without _prepare_command wrapping.
        
        This is used for wrapper scripts that already handle WSL, PATH, etc.
        Using _prepare_command would cause double-wrapping issues.
        
        Args:
            cmd: The command to execute (already WSL-wrapped if needed)
            cwd: Working directory
            timeout: Max runtime in seconds
            
        Returns:
            A dict with stdout, stderr, parsed events, and final result.
        """
        logger.debug(f"Executing wrapper: {' '.join(cmd)}")
        logger.debug(f"Working directory: {cwd}")
        
        return self._execute_streaming(cmd, cwd, timeout)
    
    def run_cursor_agent_streaming(
        self, cmd: list[str], cwd: str, timeout: int = 30
    ) -> dict[str, Any]:
        """Run cursor-agent headless with streaming output and JSON parsing.

        Args:
            cmd: The command to execute.
            cwd: Working directory.
            timeout: Max runtime in seconds.

        Returns:
            A dict with stdout, stderr, parsed events, and final result.
        """
        # Prepare command for WSL if needed
        prepared_cmd, prepared_cwd = self._prepare_command(cmd, cwd)
        
        logger.debug(f"Executing command: {' '.join(prepared_cmd)}")
        logger.debug(f"Working directory: {prepared_cwd}")
        
        return self._execute_streaming(prepared_cmd, prepared_cwd, timeout)
    
    def _execute_streaming(
        self, cmd: list[str], cwd: str, timeout: int = 30
    ) -> dict[str, Any]:
        """Execute command with streaming output and JSON parsing.
        
        Args:
            cmd: The command to execute (fully prepared)
            cwd: Working directory
            timeout: Max runtime in seconds
            
        Returns:
            A dict with stdout, stderr, parsed events, and final result.
        """
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        events: list[dict[str, Any]] = []
        result: dict[str, Any] | None = None

        start = time.monotonic()
        try:
            # Use select on Unix, polling on Windows
            use_select = not _is_windows()
            
            while True:
                # Stop if timeout exceeded
                if time.monotonic() - start > timeout:
                    raise subprocess.TimeoutExpired(cmd, timeout)

                # Process finished?
                if proc.poll() is not None:
                    break

                if use_select:
                    # Unix: use select for efficient I/O multiplexing
                    ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.1)
                    
                    if proc.stdout and proc.stdout in ready:
                        line = proc.stdout.readline()
                        if line:
                            stdout_lines.append(line)
                            logger.debug(f"[STDOUT] {line.rstrip()}")
                            try:
                                event = json.loads(line.strip())
                                events.append(event)
                                logger.debug(f"[JSON] {event}")
                                if event.get("type") == "result":
                                    result = event
                                    logger.info("✅ Process completed successfully!")
                                    logger.info(f"Duration: {event.get('duration_ms', 0)}ms")
                                    logger.info(f"Result: {event.get('result', 'No result')}")
                                    break  # Logical completion
                            except json.JSONDecodeError:
                                pass  # Keep raw text too

                    if proc.stderr and proc.stderr in ready:
                        line = proc.stderr.readline()
                        if line:
                            stderr_lines.append(line)
                            logger.debug(f"[STDERR] {line.rstrip()}")
                else:
                    # Windows: poll stdout/stderr directly
                    # Check if there's data available by trying non-blocking readline
                    if proc.stdout:
                        line = proc.stdout.readline()
                        if line:
                            stdout_lines.append(line)
                            logger.debug(f"[STDOUT] {line.rstrip()}")
                            try:
                                event = json.loads(line.strip())
                                events.append(event)
                                logger.debug(f"[JSON] {event}")
                                if event.get("type") == "result":
                                    result = event
                                    logger.info("✅ Process completed successfully!")
                                    logger.info(f"Duration: {event.get('duration_ms', 0)}ms")
                                    logger.info(f"Result: {event.get('result', 'No result')}")
                                    break  # Logical completion
                            except json.JSONDecodeError:
                                pass  # Keep raw text too
                    
                    if proc.stderr:
                        line = proc.stderr.readline()
                        if line:
                            stderr_lines.append(line)
                            logger.debug(f"[STDERR] {line.rstrip()}")
                    
                    # Small delay to avoid busy-waiting on Windows
                    time.sleep(0.05)

            # Read any remaining output
            if proc.stdout:
                remaining = proc.stdout.read()
                if remaining:
                    for line in remaining.splitlines(keepends=True):
                        stdout_lines.append(line)
                        logger.debug(f"[STDOUT] {line.rstrip()}")
            
            if proc.stderr:
                remaining = proc.stderr.read()
                if remaining:
                    for line in remaining.splitlines(keepends=True):
                        stderr_lines.append(line)
                        logger.debug(f"[STDERR] {line.rstrip()}")

            # Clean shutdown
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

        finally:
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()

        return {
            "stdout": stdout_lines,
            "stderr": stderr_lines,
            "events": events,
            "result": result,
            "returncode": proc.returncode if proc.returncode is not None else 0,
        }

    def get_cursor_cli_version(self) -> str:
        """Get cursor-cli version.

        Returns:
            cursor-cli version string
        """
        try:
            cmd = ["cursor-agent", "-v"]
            # For version check, use current directory
            prepared_cmd, prepared_cwd = self._prepare_command(cmd, str(Path.cwd()))
            
            result = subprocess.run(
                prepared_cmd, 
                capture_output=True, 
                text=True, 
                timeout=5,
                cwd=prepared_cwd
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "unknown"
        except Exception:
            return "unknown"

    def is_available(self) -> bool:
        """Check if cursor-cli is available and working.

        Returns:
            True if cursor-cli is available, False otherwise
        """
        try:
            cmd = ["cursor-agent", "-v"]
            # For availability check, use current directory
            prepared_cmd, prepared_cwd = self._prepare_command(cmd, str(Path.cwd()))
            
            result = subprocess.run(
                prepared_cmd, 
                capture_output=True, 
                text=True, 
                timeout=5,
                cwd=prepared_cwd
            )
            return result.returncode == 0
        except Exception:
            return False
