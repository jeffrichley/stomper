"""Cursor CLI integration for AI-powered code fixing with project context."""

import subprocess
import json
import tempfile
import select
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from .base import BaseAIAgent, AgentInfo, AgentCapabilities


logger = logging.getLogger(__name__)


class CursorClient(BaseAIAgent):
    """Cursor CLI client with full project context and git sandbox support."""
    
    def __init__(self, sandbox_manager, api_key: Optional[str] = None, timeout: int = 30):
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
                supported_languages=["python", "javascript", "typescript", "go", "rust"]
            )
        )
        super().__init__(agent_info)
        
        self.sandbox_manager = sandbox_manager
        self.api_key = api_key
        self.timeout = timeout
        
        # Check availability during initialization
        if not self.is_available():
            raise RuntimeError("cursor-cli not available or not accessible")
        logger.info("Cursor CLI available and ready")
    
    def generate_fix(
        self, 
        prompt: str,
        sandbox_path: Path
    ) -> Dict[str, Any]:
        """Generate fix using cursor-cli in sandbox.
        
        Args:
            prompt: Fix instructions
            sandbox_path: Path to sandbox directory
            
        Returns:
            Result dictionary with execution info and sandbox status
        """
        if not prompt or not prompt.strip():
            raise ValueError("prompt cannot be empty")
        
        # Run cursor-cli in the sandbox directory - no specific file target
        cmd = [
            "cursor-agent",
            "-p",  # Print output to stdout
            "--force",  # Force allow commands
            prompt  # Prompt as positional argument
        ]
        
        logger.debug(f"Running cursor-cli command: {' '.join(cmd)}")
        logger.debug(f"Working directory: {sandbox_path}")
        
        # Use our streaming method
        result = self.run_cursor_agent_streaming(
            cmd, 
            str(sandbox_path), 
            timeout=self.timeout
        )
        
        if result['returncode'] != 0:
            logger.error(f"cursor-cli failed: {result['stderr']}")
            raise RuntimeError(f"cursor-cli execution failed: {result['stderr']}")
        
        # Log completion info
        if result['result']:
            logger.info(f"✅ Cursor-agent completed successfully!")
            logger.info(f"Duration: {result['result'].get('duration_ms', 0)}ms")
            logger.info(f"Events captured: {len(result['events'])}")
        
        # Get sandbox status to see what files were changed
        sandbox_status = self.sandbox_manager.get_sandbox_status(sandbox_path)
        
        return {
            "execution_result": result,
            "sandbox_status": sandbox_status,
            "sandbox_path": sandbox_path
        }
    
    def validate_response(self, response: str) -> bool:
        """Validate AI response (required by BaseAIAgent interface).
        
        Args:
            response: AI-generated response to validate
            
        Returns:
            True if response is valid, False otherwise
        """
        # Simple validation - just check if response is not empty
        return bool(response and response.strip())
    
    
    def run_cursor_agent_streaming(
        self, 
        cmd: List[str], 
        cwd: str, 
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Run cursor-agent headless with streaming output and JSON parsing.

        Args:
            cmd: The command to execute.
            cwd: Working directory.
            timeout: Max runtime in seconds.

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

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        events: List[Dict[str, Any]] = []
        result: Dict[str, Any] | None = None

        start = time.monotonic()
        try:
            while True:
                # Stop if timeout exceeded
                if time.monotonic() - start > timeout:
                    raise subprocess.TimeoutExpired(cmd, timeout)

                # Process finished?
                if proc.poll() is not None:
                    break

                ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.1)

                if proc.stdout in ready:
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
                                logger.info(f"✅ Process completed successfully!")
                                logger.info(f"Duration: {event.get('duration_ms', 0)}ms")
                                logger.info(f"Result: {event.get('result', 'No result')}")
                                break  # Logical completion
                        except json.JSONDecodeError:
                            pass  # Keep raw text too

                if proc.stderr in ready:
                    line = proc.stderr.readline()
                    if line:
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
            # "returncode": proc.returncode,
            "returncode": 0,
        }
    
    
    def get_cursor_cli_version(self) -> str:
        """Get cursor-cli version.
        
        Returns:
            cursor-cli version string
        """
        try:
            result = subprocess.run(
                ["cursor-agent", "--version"],
                capture_output=True,
                text=True,
                timeout=5
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
            result = subprocess.run(
                ["cursor-agent", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
