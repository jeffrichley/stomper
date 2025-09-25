"""Integration tests for CursorClient with real cursor-cli."""

import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from stomper.ai.cursor_client import CursorClient
from stomper.ai.base import AgentInfo, AgentCapabilities


class TestCursorIntegration:
    """Integration tests for CursorClient with cursor-cli."""

    def test_cursor_client_real_initialization(self):
        """Test CursorClient with real cursor-cli if available."""
        try:
            # Try to create client - this will fail if cursor-cli not available
            client = CursorClient()
            
            # If we get here, cursor-cli is available
            assert client.get_agent_info().name == "cursor-cli"
            assert client.is_available() is True
            
        except RuntimeError:
            # cursor-cli not available, skip test
            pytest.skip("cursor-cli not available")

    def test_cursor_client_real_version_check(self):
        """Test getting real cursor-cli version."""
        try:
            client = CursorClient()
            version = client.get_cursor_cli_version()
            
            # Should return actual version or "unknown"
            assert isinstance(version, str)
            assert len(version) > 0
            
        except RuntimeError:
            pytest.skip("cursor-cli not available")

    def test_cursor_client_real_availability_check(self):
        """Test real availability check."""
        try:
            client = CursorClient()
            is_available = client.is_available()
            
            # Should be True if cursor-cli is available
            assert isinstance(is_available, bool)
            
        except RuntimeError:
            pytest.skip("cursor-cli not available")

    def test_cursor_client_generate_fix_with_real_cursor(self):
        """Test fix generation with real cursor-cli (if available)."""
        try:
            client = CursorClient()
            
            # Only run if cursor-cli is available
            if not client.is_available():
                pytest.skip("cursor-cli not available")
            
            # Test with simple Python code
            error_context = {
                "error_type": "linting",
                "message": "unused import",
                "file": "test.py",
                "line": 1
            }
            code_context = "import os\nprint('hello')"
            prompt = "Remove the unused import"
            
            # This might fail if cursor-cli requires authentication
            try:
                result = client.generate_fix(error_context, code_context, prompt)
                
                # Should return some code
                assert isinstance(result, str)
                assert len(result) > 0
                
            except RuntimeError as e:
                # Expected if cursor-cli requires authentication or has other issues
                assert "cursor-cli" in str(e).lower() or "error" in str(e).lower()
                
        except RuntimeError:
            pytest.skip("cursor-cli not available")

    def test_cursor_client_validate_response_edge_cases(self):
        """Test response validation with edge cases."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Edge cases
            edge_cases = [
                ("", False),  # Empty
                ("   ", False),  # Whitespace
                ("# Comment only", False),  # Comment only
                ("def hello():", True),  # Partial function
                ("import os\n# Comment", True),  # Import with comment
                ("class MyClass:\n    pass", True),  # Class definition
                ("if True:\n    pass", True),  # Control structure
                ("try:\n    pass\nexcept:\n    pass", True),  # Exception handling
            ]
            
            for response, expected in edge_cases:
                assert client.validate_response(response) == expected

    def test_cursor_client_construct_prompt_edge_cases(self):
        """Test prompt construction with edge cases."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Test with minimal error context
            error_context = {"error_type": "linting"}
            code_context = "print('hello')"
            prompt = "Fix the error"
            
            constructed_prompt = client._construct_prompt(
                error_context, code_context, prompt
            )
            
            assert "Fix the error" in constructed_prompt
            assert "Type: linting" in constructed_prompt
            assert "print('hello')" in constructed_prompt
            
            # Test with empty error context
            error_context = {}
            constructed_prompt = client._construct_prompt(
                error_context, code_context, prompt
            )
            
            assert "Type: unknown" in constructed_prompt

    def test_cursor_client_timeout_handling(self):
        """Test timeout handling in CursorClient."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run, \
             patch('stomper.ai.cursor_client.tempfile.NamedTemporaryFile') as mock_temp:
            
            # Mock cursor-cli availability check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            # Mock temporary file
            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/test.py"
            mock_temp_file.__enter__.return_value = mock_temp_file
            mock_temp.return_value = mock_temp_file
            
            client = CursorClient(timeout=1)
            
            # Mock timeout
            mock_run.side_effect = subprocess.TimeoutExpired("cursor-agent", 1)
            
            with pytest.raises(RuntimeError, match="cursor-cli timed out"):
                client.generate_fix(
                    {"error_type": "linting"},
                    "code",
                    "prompt"
                )

    def test_cursor_client_file_operations(self):
        """Test file operations in CursorClient."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run, \
             patch('stomper.ai.cursor_client.tempfile.NamedTemporaryFile') as mock_temp, \
             patch('stomper.ai.cursor_client.Path') as mock_path:
            
            # Mock cursor-cli availability check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            # Mock temporary file
            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/test.py"
            mock_temp_file.__enter__.return_value = mock_temp_file
            mock_temp.return_value = mock_temp_file
            
            # Mock Path operations
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.parent = Path("/tmp")
            mock_path_instance.unlink.return_value = None
            mock_path.return_value = mock_path_instance
            
            client = CursorClient()
            
            # Mock successful cursor-cli execution
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""
            
            # Mock file reading with valid Python code
            with patch('builtins.open', mock_open(read_data="def hello():\n    print('world')\n")):
                result = client.generate_fix(
                    {"error_type": "linting"},
                    "print('hello')",
                    "Fix the code"
                )
                
                assert result == "def hello():\n    print('world')\n"
                # Verify file operations (may be called multiple times due to cleanup)
                assert mock_path_instance.unlink.call_count >= 1

    def test_cursor_client_error_handling(self):
        """Test error handling in CursorClient."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run, \
             patch('stomper.ai.cursor_client.tempfile.NamedTemporaryFile') as mock_temp:
            
            # Mock cursor-cli availability check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            # Mock temporary file
            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/test.py"
            mock_temp_file.__enter__.return_value = mock_temp_file
            mock_temp.return_value = mock_temp_file
            
            client = CursorClient()
            
            # Test various error scenarios
            error_scenarios = [
                (1, "cursor-cli error", "cursor-cli execution failed"),
                (2, "permission denied", "cursor-cli execution failed"),
                (127, "command not found", "cursor-cli execution failed"),
            ]
            
            for returncode, stderr, expected_error in error_scenarios:
                mock_run.return_value.returncode = returncode
                mock_run.return_value.stderr = stderr
                
                with pytest.raises(RuntimeError, match=expected_error):
                    client.generate_fix(
                        {"error_type": "linting"},
                        "code",
                        "prompt"
                    )


def mock_open(read_data=""):
    """Mock open function for file operations."""
    mock_file = MagicMock()
    mock_file.read.return_value = read_data
    mock_file.__enter__.return_value = mock_file
    mock_file.__exit__.return_value = None
    return MagicMock(return_value=mock_file)
