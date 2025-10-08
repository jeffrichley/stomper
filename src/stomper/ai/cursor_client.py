"""Cursor CLI integration for AI-powered code fixing with project context."""

import json
import logging
import select
import subprocess
import time
from typing import Any

from .base import AgentCapabilities, AgentInfo, BaseAIAgent
from .prompt_generator import PromptGenerator

logger = logging.getLogger(__name__)


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

        # Check availability during initialization
        if not self.is_available():
            raise RuntimeError("cursor-cli not available or not accessible")
        logger.info("Cursor CLI available and ready")

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

        # Create a temporary sandbox for this fix
        sandbox_path, branch_name = self.sandbox_manager.create_sandbox()

        try:
            # Run cursor-cli in the sandbox directory
            cmd = [
                "cursor-agent",
                "-p",  # Print output to stdout
                "--force",  # Force allow commands
                full_prompt,  # Comprehensive prompt
            ]

            logger.debug(f"Running cursor-cli command in sandbox: {sandbox_path}")
            logger.debug(f"Prompt length: {len(full_prompt)} characters")

            # Use our streaming method
            result = self.run_cursor_agent_streaming(cmd, str(sandbox_path), timeout=self.timeout)

            if result["returncode"] != 0:
                logger.error(f"cursor-cli failed: {result['stderr']}")
                raise RuntimeError(f"cursor-cli execution failed: {result['stderr']}")

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
            # Cleanup sandbox
            self.sandbox_manager.cleanup_sandbox(sandbox_path, branch_name)

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
            while True:
                # Stop if timeout exceeded
                if time.monotonic() - start > timeout:
                    raise subprocess.TimeoutExpired(cmd, timeout)

                # Process finished?
                if proc.poll() is not None:
                    break

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
                ["cursor-agent", "--version"], capture_output=True, text=True, timeout=5
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
                ["cursor-agent", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
