"""Tests for CursorClient AI agent integration."""

import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from stomper.ai.cursor_client import CursorClient
from stomper.ai.base import AgentInfo, AgentCapabilities


class TestCursorClient:
    """Test CursorClient implementation."""

    def test_cursor_client_initialization(self):
        """Test CursorClient initialization."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            assert client.api_key is None
            assert client.timeout == 30
            assert client.get_agent_info().name == "cursor-cli"
            assert client.get_agent_info().version == "1.0.0"

    def test_cursor_client_initialization_with_api_key(self):
        """Test CursorClient initialization with API key."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient(api_key="test-key", timeout=60)
            
            assert client.api_key == "test-key"
            assert client.timeout == 60

    def test_cursor_client_initialization_cursor_not_available(self):
        """Test CursorClient initialization when cursor-cli not available."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("cursor-agent not found")
            
            with pytest.raises(RuntimeError, match="cursor-cli not found"):
                CursorClient()

    def test_cursor_client_initialization_cursor_fails(self):
        """Test CursorClient initialization when cursor-cli fails."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "cursor-agent error"
            
            with pytest.raises(RuntimeError, match="cursor-cli not available"):
                CursorClient()

    def test_cursor_client_agent_info(self):
        """Test CursorClient agent info."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            info = client.get_agent_info()
            
            assert info.name == "cursor-cli"
            assert info.version == "1.0.0"
            assert info.description == "Cursor CLI AI agent for automated code fixing"
            assert info.capabilities.can_fix_linting is True
            assert info.capabilities.can_fix_types is True
            assert info.capabilities.can_fix_tests is True
            assert info.capabilities.max_context_length == 8000
            assert "python" in info.capabilities.supported_languages

    def test_cursor_client_generate_fix_success(self):
        """Test successful fix generation."""
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
            mock_path.return_value = mock_path_instance
            
            # Mock file reading with valid Python code
            with patch('builtins.open', mock_open(read_data="print('hello world')\n")):
                client = CursorClient()
                
                # Mock successful cursor-cli execution
                mock_run.return_value.returncode = 0
                mock_run.return_value.stderr = ""
                
                result = client.generate_fix(
                    {"error_type": "linting", "message": "unused import"},
                    "print('hello')",
                    "Fix the linting error"
                )
                
                assert result == "print('hello world')\n"
                mock_run.assert_called()

    def test_cursor_client_generate_fix_cursor_fails(self):
        """Test fix generation when cursor-cli fails."""
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
            
            # Mock cursor-cli failure
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "cursor-cli error"
            
            with pytest.raises(RuntimeError, match="cursor-cli execution failed"):
                client.generate_fix(
                    {"error_type": "linting"},
                    "code",
                    "prompt"
                )

    def test_cursor_client_generate_fix_timeout(self):
        """Test fix generation timeout."""
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

    def test_cursor_client_validate_response_valid(self):
        """Test response validation with valid response."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Valid code response
            valid_responses = [
                "def hello():\n    print('world')",
                "import os\nfrom pathlib import Path",
                "class MyClass:\n    def __init__(self):\n        pass",
                "if x > 0:\n    return True",
                "for item in items:\n    process(item)"
            ]
            
            for response in valid_responses:
                assert client.validate_response(response) is True

    def test_cursor_client_validate_response_invalid(self):
        """Test response validation with invalid response."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Invalid responses
            invalid_responses = [
                "",  # Empty
                "   ",  # Whitespace only
                "Error: Something went wrong",  # Error message
                "Exception: Failed to process",  # Exception
                "Cannot fix this error",  # Error indicator
                "Unable to generate fix",  # Error indicator
            ]
            
            for response in invalid_responses:
                assert client.validate_response(response) is False

    def test_cursor_client_construct_prompt(self):
        """Test prompt construction."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            error_context = {
                "error_type": "linting",
                "message": "unused import 'os'",
                "file": "test.py",
                "line": 5
            }
            code_context = "import os\nprint('hello')"
            prompt = "Fix the linting error"
            
            constructed_prompt = client._construct_prompt(
                error_context, code_context, prompt
            )
            
            assert "Fix the linting error" in constructed_prompt
            assert "Type: linting" in constructed_prompt
            assert "Message: unused import 'os'" in constructed_prompt
            assert "File: test.py" in constructed_prompt
            assert "Line: 5" in constructed_prompt
            assert "import os\nprint('hello')" in constructed_prompt

    def test_cursor_client_get_cursor_cli_version(self):
        """Test getting cursor-cli version."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            # Mock availability check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Mock version check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 2.0.0"
            
            version = client.get_cursor_cli_version()
            assert version == "cursor-agent 2.0.0"

    def test_cursor_client_get_cursor_cli_version_fails(self):
        """Test getting cursor-cli version when it fails."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            # Mock availability check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Mock version check failure
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "error"
            
            version = client.get_cursor_cli_version()
            assert version == "unknown"

    def test_cursor_client_is_available(self):
        """Test checking if cursor-cli is available."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            # Mock availability check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Test available
            mock_run.return_value.returncode = 0
            assert client.is_available() is True
            
            # Test not available
            mock_run.return_value.returncode = 1
            assert client.is_available() is False

    def test_cursor_client_is_available_exception(self):
        """Test checking availability when exception occurs."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            # Mock availability check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Mock exception
            mock_run.side_effect = Exception("error")
            assert client.is_available() is False

    def test_cursor_client_can_handle_error_type(self):
        """Test error type handling capabilities."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Test supported error types
            assert client.can_handle_error_type("linting") is True
            assert client.can_handle_error_type("ruff") is True
            assert client.can_handle_error_type("type") is True
            assert client.can_handle_error_type("mypy") is True
            assert client.can_handle_error_type("test") is True
            assert client.can_handle_error_type("pytest") is True
            
            # Test unsupported error type
            assert client.can_handle_error_type("unknown") is False

    def test_cursor_client_can_handle_language(self):
        """Test language handling capabilities."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            # Test supported languages
            assert client.can_handle_language("python") is True
            assert client.can_handle_language("javascript") is True
            assert client.can_handle_language("typescript") is True
            assert client.can_handle_language("go") is True
            assert client.can_handle_language("rust") is True
            
            # Test unsupported language
            assert client.can_handle_language("c++") is False

    def test_cursor_client_get_max_context_length(self):
        """Test getting maximum context length."""
        with patch('stomper.ai.cursor_client.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "cursor-agent 1.0.0"
            
            client = CursorClient()
            
            max_length = client.get_max_context_length()
            assert max_length == 8000


def mock_open(read_data=""):
    """Mock open function for file operations."""
    mock_file = MagicMock()
    mock_file.read.return_value = read_data
    mock_file.__enter__.return_value = mock_file
    mock_file.__exit__.return_value = None
    return MagicMock(return_value=mock_file)
