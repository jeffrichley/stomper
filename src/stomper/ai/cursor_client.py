"""Cursor CLI integration for AI-powered code fixing."""

import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .base import BaseAIAgent, AgentInfo, AgentCapabilities


logger = logging.getLogger(__name__)


class CursorClient(BaseAIAgent):
    """Cursor CLI client implementing AIAgent protocol."""
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """Initialize Cursor CLI client.
        
        Args:
            api_key: Cursor API key (if None, will use environment variable)
            timeout: Timeout for cursor-cli commands in seconds
        """
        agent_info = AgentInfo(
            name="cursor-cli",
            version="1.0.0",
            description="Cursor CLI AI agent for automated code fixing",
            capabilities=AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=True,
                can_fix_tests=True,
                max_context_length=8000,
                supported_languages=["python", "javascript", "typescript", "go", "rust"]
            )
        )
        super().__init__(agent_info)
        
        self.api_key = api_key
        self.timeout = timeout
        self._check_cursor_cli_availability()
    
    def _check_cursor_cli_availability(self) -> None:
        """Check if cursor-cli is available and accessible."""
        try:
            result = subprocess.run(
                ["cursor-agent", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError(f"cursor-cli not available: {result.stderr}")
            logger.info(f"Cursor CLI available: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"cursor-cli not found or not accessible: {e}")
    
    def generate_fix(
        self, 
        error_context: Dict[str, Any], 
        code_context: str, 
        prompt: str
    ) -> str:
        """Generate fix using cursor-cli headless mode.
        
        Args:
            error_context: Error details including type, location, message
            code_context: Surrounding code context
            prompt: Specific fix instructions
            
        Returns:
            Generated fix code
        """
        # Validate inputs
        if not code_context or not code_context.strip():
            raise ValueError("code_context cannot be empty")
        
        if not prompt or not prompt.strip():
            raise ValueError("prompt cannot be empty")
        
        # Sanitize inputs
        sanitized_code = self._sanitize_code(code_context)
        sanitized_prompt = self._sanitize_prompt(prompt)
        
        try:
            # Create a temporary file with the code context
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(sanitized_code)
                temp_file_path = Path(temp_file.name)
            
            # Construct the cursor-cli command
            full_prompt = self._construct_prompt(error_context, sanitized_code, sanitized_prompt)
            
            # Run cursor-cli in headless mode
            cmd = [
                "cursor-agent",
                "-p", full_prompt,
                "--force",  # Allow file modifications
                str(temp_file_path)
            ]
            
            logger.debug(f"Running cursor-cli command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=temp_file_path.parent
            )
            
            if result.returncode != 0:
                logger.error(f"cursor-cli failed: {result.stderr}")
                raise RuntimeError(f"cursor-cli execution failed: {result.stderr}")
            
            # Read the modified file
            if temp_file_path.exists():
                with open(temp_file_path, 'r') as f:
                    fixed_code = f.read()
            else:
                raise RuntimeError("cursor-cli did not produce output file")
            
            # Validate the response
            if not self.validate_response(fixed_code):
                logger.warning("cursor-cli response failed validation")
                raise RuntimeError("cursor-cli response failed validation")
            
            # Clean up temporary file
            temp_file_path.unlink()
            
            return fixed_code
            
        except subprocess.TimeoutExpired:
            logger.error(f"cursor-cli timed out after {self.timeout} seconds")
            raise RuntimeError(f"cursor-cli timed out after {self.timeout} seconds")
        except Exception as e:
            logger.error(f"Error running cursor-cli: {e}")
            raise RuntimeError(f"Error running cursor-cli: {e}")
        finally:
            # Ensure cleanup
            try:
                if 'temp_file_path' in locals() and temp_file_path.exists():
                    temp_file_path.unlink()
            except Exception:
                pass
    
    def validate_response(self, response: str) -> bool:
        """Validate cursor-cli response.
        
        Args:
            response: AI-generated response to validate
            
        Returns:
            True if response is valid, False otherwise
        """
        if not response or not response.strip():
            return False
        
        response_lower = response.lower()
        
        # Check for obvious error patterns first
        error_patterns = [
            'error:', 'exception:', 'traceback:', 'failed to',
            'cannot', 'unable to', 'invalid', 'malformed',
            'syntax error', 'indentation error', 'name error',
            'type error', 'attribute error', 'value error'
        ]
        
        has_error_patterns = any(pattern in response_lower for pattern in error_patterns)
        if has_error_patterns:
            return False
        
        # Check if response looks like code
        code_indicators = [
            'def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ',
            'return ', 'yield ', 'async ', 'await ', 'try:', 'except:',
            'finally:', 'with ', 'lambda ', '=', '(', ')', '[', ']', '{', '}',
            'print(', 'len(', 'str(', 'int(', 'float(', 'list(', 'dict(',
            'set(', 'tuple(', 'range(', 'enumerate(', 'zip('
        ]
        
        has_code_indicators = any(indicator in response_lower for indicator in code_indicators)
        
        # Additional validation for Python-specific patterns
        python_patterns = [
            'if __name__', 'def main(', 'if __main__',
            'import ', 'from ', 'as ', 'in ', 'not in ',
            'and ', 'or ', 'not ', 'is ', 'is not '
        ]
        
        has_python_patterns = any(pattern in response_lower for pattern in python_patterns)
        
        # Must have code indicators and not be just comments
        comment_only = response.strip().startswith('#') and not any(
            line.strip() and not line.strip().startswith('#') 
            for line in response.split('\n')
        )
        
        return has_code_indicators and not comment_only and (has_python_patterns or has_code_indicators)
    
    def _construct_prompt(
        self, 
        error_context: Dict[str, Any], 
        code_context: str, 
        prompt: str
    ) -> str:
        """Construct comprehensive prompt for cursor-cli.
        
        Args:
            error_context: Error details
            code_context: Code context
            prompt: Base prompt
            
        Returns:
            Constructed prompt for cursor-cli
        """
        error_type = error_context.get('error_type', 'unknown')
        error_message = error_context.get('message', '')
        file_path = error_context.get('file', '')
        line_number = error_context.get('line', '')
        
        constructed_prompt = f"""
{prompt}

Error Details:
- Type: {error_type}
- Message: {error_message}
- File: {file_path}
- Line: {line_number}

Code Context:
```python
{code_context}
```

Please fix the {error_type} error while maintaining code quality and following Python best practices.
The fix should be minimal and focused on resolving the specific error.
"""
        
        return constructed_prompt.strip()
    
    def _sanitize_code(self, code: str) -> str:
        """Sanitize code input to prevent security issues.
        
        Args:
            code: Code to sanitize
            
        Returns:
            Sanitized code
        """
        if not code:
            return ""
        
        # Only sanitize truly dangerous patterns
        dangerous_patterns = [
            'exec(', 'eval(', '__import__', 'compile(',
            'input(', 'raw_input('
        ]
        
        sanitized = code
        for pattern in dangerous_patterns:
            if pattern in sanitized.lower():
                logger.warning(f"Potentially dangerous pattern detected: {pattern}")
                # Replace with safe alternative or remove
                sanitized = sanitized.replace(pattern, f"# {pattern} # REMOVED FOR SECURITY")
        
        return sanitized
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Sanitize prompt input to prevent injection attacks.
        
        Args:
            prompt: Prompt to sanitize
            
        Returns:
            Sanitized prompt
        """
        if not prompt:
            return ""
        
        # Remove potential injection patterns
        injection_patterns = [
            '`', '$(', '${', 'exec(', 'eval(',
            'import os', 'import sys', 'subprocess'
        ]
        
        sanitized = prompt
        for pattern in injection_patterns:
            if pattern in sanitized:
                logger.warning(f"Potential injection pattern detected: {pattern}")
                sanitized = sanitized.replace(pattern, "")
        
        return sanitized.strip()
    
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
