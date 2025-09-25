"""Unit tests for quality tool integrations."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from stomper.quality.base import QualityError
from stomper.quality.manager import QualityToolManager
from stomper.quality.mypy import MyPyTool
from stomper.quality.ruff import RuffTool


@pytest.mark.unit
class TestQualityError:
    """Test QualityError dataclass."""

    def test_quality_error_creation(self):
        """Test creating a QualityError."""
        error = QualityError(
            tool="ruff",
            file=Path("test.py"),
            line=10,
            column=5,
            code="E501",
            message="Line too long",
            severity="error",
            auto_fixable=True,
        )

        assert error.tool == "ruff"
        assert error.file == Path("test.py")
        assert error.line == 10
        assert error.column == 5
        assert error.code == "E501"
        assert error.message == "Line too long"
        assert error.severity == "error"
        assert error.auto_fixable is True


@pytest.mark.unit
class TestRuffTool:
    """Test Ruff tool integration."""

    def test_ruff_tool_properties(self):
        """Test Ruff tool properties."""
        tool = RuffTool()

        assert tool.tool_name == "ruff"
        assert tool.command == "ruff"
        assert tool.json_output_flag == "--output-format=json"

    def test_parse_ruff_errors(self):
        """Test parsing Ruff JSON output."""
        tool = RuffTool()
        project_root = Path("/test")

        # Sample Ruff JSON output
        ruff_json = json.dumps(
            [
                {
                    "code": "E501",
                    "message": "Line too long (120 > 88 characters)",
                    "filename": "test.py",
                    "location": {"row": 10, "column": 89},
                    "end_location": {"row": 10, "column": 120},
                    "fix": {"message": "Fix line length", "edits": []},
                },
                {
                    "code": "F401",
                    "message": "Imported but unused",
                    "filename": "test.py",
                    "location": {"row": 1, "column": 1},
                    "end_location": {"row": 1, "column": 10},
                },
            ]
        )

        errors = tool.parse_errors(ruff_json, project_root)

        assert len(errors) == 2

        # Check first error
        assert errors[0].tool == "ruff"
        assert errors[0].file == project_root / "test.py"
        assert errors[0].line == 10
        assert errors[0].column == 89
        assert errors[0].code == "E501"
        assert errors[0].message == "Line too long (120 > 88 characters)"
        assert errors[0].severity == "error"
        assert errors[0].auto_fixable is True

        # Check second error
        assert errors[1].tool == "ruff"
        assert errors[1].file == project_root / "test.py"
        assert errors[1].line == 1
        assert errors[1].column == 1
        assert errors[1].code == "F401"
        assert errors[1].message == "Imported but unused"
        assert errors[1].severity == "error"
        assert errors[1].auto_fixable is False

    def test_parse_empty_ruff_output(self):
        """Test parsing empty Ruff output."""
        tool = RuffTool()
        project_root = Path("/test")

        errors = tool.parse_errors("", project_root)
        assert len(errors) == 0

        errors = tool.parse_errors("[]", project_root)
        assert len(errors) == 0


@pytest.mark.unit
class TestMyPyTool:
    """Test MyPy tool integration."""

    def test_mypy_tool_properties(self):
        """Test MyPy tool properties."""
        tool = MyPyTool()

        assert tool.tool_name == "mypy"
        assert tool.command == "mypy"
        assert tool.json_output_flag == "--show-error-codes"

    def test_parse_mypy_errors(self):
        """Test parsing MyPy text output."""
        # Sample MyPy text output
        mypy_output = """test.py:5: error: Incompatible types [assignment]
test.py:10: error: No overload variant matches [call-overload]"""

        tool = MyPyTool()
        project_root = Path("/test")

        errors = tool.parse_errors(mypy_output, project_root)

        assert len(errors) == 2

        # Test first error
        assert errors[0].tool == "mypy"
        assert errors[0].file == project_root / "test.py"
        assert errors[0].line == 5
        assert errors[0].column == 0  # MyPy text output doesn't provide column
        assert errors[0].code == "assignment"
        assert errors[0].message == "Incompatible types"
        assert errors[0].severity == "error"

        # Test second error
        assert errors[1].tool == "mypy"
        assert errors[1].file == project_root / "test.py"
        assert errors[1].line == 10
        assert errors[1].column == 0
        assert errors[1].code == "call-overload"
        assert errors[1].message == "No overload variant matches"
        assert errors[1].severity == "error"


@pytest.mark.unit
class TestQualityToolManager:
    """Test quality tool manager."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = QualityToolManager()

        assert "ruff" in manager.tools
        assert "mypy" in manager.tools
        assert "drill-sergeant" in manager.tools
        assert "pytest" in manager.tools

    @patch("shutil.which")
    def test_get_available_tools(self, mock_which):
        """Test getting available tools."""

        # Mock some tools as available
        def mock_which_func(cmd):
            return cmd if cmd in ["ruff", "mypy"] else None

        mock_which.side_effect = mock_which_func

        manager = QualityToolManager()
        available = manager.get_available_tools()

        assert "ruff" in available
        assert "mypy" in available
        assert "drill-sergeant" not in available
        assert "pytest" not in available

    def test_tool_summary(self):
        """Test getting tool summary."""
        manager = QualityToolManager()
        project_root = Path("/test")

        errors = [
            QualityError(
                tool="ruff",
                file=project_root / "test.py",
                line=1,
                column=1,
                code="E501",
                message="msg",
                severity="error",
                auto_fixable=True,
            ),
            QualityError(
                tool="ruff",
                file=project_root / "test.py",
                line=2,
                column=1,
                code="F401",
                message="msg",
                severity="error",
                auto_fixable=False,
            ),
            QualityError(
                tool="mypy",
                file=project_root / "test.py",
                line=3,
                column=1,
                code="E",
                message="msg",
                severity="error",
                auto_fixable=False,
            ),
        ]

        summary = manager.get_tool_summary(errors)

        assert summary["ruff"] == 2
        assert summary["mypy"] == 1

    def test_filter_errors(self):
        """Test error filtering."""
        manager = QualityToolManager()
        project_root = Path("/test")

        errors = [
            QualityError(
                tool="ruff",
                file=project_root / "test1.py",
                line=1,
                column=1,
                code="E501",
                message="msg",
                severity="error",
                auto_fixable=True,
            ),
            QualityError(
                tool="ruff",
                file=project_root / "test2.py",
                line=2,
                column=1,
                code="F401",
                message="msg",
                severity="error",
                auto_fixable=False,
            ),
            QualityError(
                tool="mypy",
                file=project_root / "test1.py",
                line=3,
                column=1,
                code="E",
                message="msg",
                severity="error",
                auto_fixable=False,
            ),
        ]

        # Filter by error types
        filtered = manager.filter_errors(errors, error_types=["E501"])
        assert len(filtered) == 1
        assert filtered[0].code == "E501"

        # Filter by ignore codes
        filtered = manager.filter_errors(errors, ignore_codes=["E501"])
        assert len(filtered) == 2
        assert all(error.code != "E501" for error in filtered)

        # Filter by files
        filtered = manager.filter_errors(errors, files=[project_root / "test1.py"])
        assert len(filtered) == 2
        assert all(error.file == project_root / "test1.py" for error in filtered)
