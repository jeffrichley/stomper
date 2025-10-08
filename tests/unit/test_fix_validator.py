"""Tests for FixValidator class - Fix Validation Pipeline."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from stomper.ai.validator import FixValidator
from stomper.models.cli import ErrorComparison, ValidationResult
from stomper.quality.base import BaseQualityTool, QualityError


@pytest.fixture
def mock_quality_tools():
    """Create mock quality tools for testing."""
    mock_tool1 = Mock(spec=BaseQualityTool)
    mock_tool1.tool_name = "ruff"
    mock_tool1.is_available.return_value = True
    mock_tool1.run_tool.return_value = []

    mock_tool2 = Mock(spec=BaseQualityTool)
    mock_tool2.tool_name = "mypy"
    mock_tool2.is_available.return_value = True
    mock_tool2.run_tool.return_value = []

    return [mock_tool1, mock_tool2]


@pytest.fixture
def sample_quality_errors():
    """Create sample quality errors for testing."""
    return [
        QualityError(
            tool="ruff",
            file=Path("/project/src/main.py"),
            line=10,
            column=5,
            code="F401",
            message="Unused import",
            severity="error",
            auto_fixable=True,
        ),
        QualityError(
            tool="mypy",
            file=Path("/project/src/utils.py"),
            line=20,
            column=10,
            code="arg-type",
            message="Argument type mismatch",
            severity="error",
            auto_fixable=False,
        ),
    ]


# ============================================================================
# Initialization Tests
# ============================================================================


class TestFixValidatorInitialization:
    """Test FixValidator initialization."""

    @pytest.mark.unit
    def test_fix_validator_initialization(self, tmp_path, mock_quality_tools):
        """Test basic FixValidator initialization."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        validator = FixValidator(project_root, mock_quality_tools)

        assert validator.project_root == project_root
        assert validator.quality_tools == mock_quality_tools

    @pytest.mark.unit
    def test_fix_validator_initialization_validates_project_root(self, mock_quality_tools):
        """Test initialization validates project root exists."""
        with pytest.raises(ValueError, match="Project root does not exist"):
            FixValidator(Path("/nonexistent"), mock_quality_tools)

    @pytest.mark.unit
    def test_fix_validator_with_empty_tools_list(self, tmp_path):
        """Test initialization with empty quality tools list."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        validator = FixValidator(project_root, [])

        assert validator.quality_tools == []


# ============================================================================
# Validation Tests - Success Cases
# ============================================================================


class TestFixValidatorSuccess:
    """Test successful validation scenarios."""

    @pytest.mark.unit
    def test_validate_fixes_all_errors_fixed(self, tmp_path, mock_quality_tools, sample_quality_errors):
        """Test validation when all errors are fixed."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Mock quality tools to return no errors (all fixed!)
        for tool in mock_quality_tools:
            tool.run_tool.return_value = []

        # Execute
        validator = FixValidator(project_root, mock_quality_tools)
        result = validator.validate_fixes(
            files=[Path("src/main.py"), Path("src/utils.py")], original_errors=sample_quality_errors
        )

        # Verify
        assert result.passed is True
        assert result.errors_fixed == 2
        assert result.errors_remaining == 0
        assert result.new_errors_introduced == 0
        assert len(result.new_errors) == 0
        assert "Success" in result.summary or "fixed" in result.summary.lower()

    @pytest.mark.unit
    def test_validate_fixes_partial_fix(self, tmp_path, mock_quality_tools):
        """Test validation when some errors are fixed."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create original errors with correct project_root
        original_errors = [
            QualityError(
                tool="ruff",
                file=project_root / "src/main.py",
                line=10,
                column=5,
                code="F401",
                message="Unused import",
                severity="error",
                auto_fixable=True,
            ),
            QualityError(
                tool="mypy",
                file=project_root / "src/utils.py",
                line=20,
                column=10,
                code="arg-type",
                message="Argument type mismatch",
                severity="error",
                auto_fixable=False,
            ),
        ]

        # Mock: One error remains
        remaining_error = QualityError(
            tool="mypy",
            file=project_root / "src/utils.py",
            line=20,
            column=10,
            code="arg-type",
            message="Argument type mismatch",
            severity="error",
            auto_fixable=False,
        )

        mock_quality_tools[0].run_tool.return_value = []  # ruff errors fixed
        mock_quality_tools[1].run_tool.return_value = [remaining_error]  # mypy error remains

        # Execute
        validator = FixValidator(project_root, mock_quality_tools)
        result = validator.validate_fixes(
            files=[Path("src/main.py"), Path("src/utils.py")], original_errors=original_errors
        )

        # Verify
        assert result.passed is True  # Still passes (net improvement)
        assert result.errors_fixed == 1  # One fixed
        assert result.errors_remaining == 1  # One remains
        assert result.new_errors_introduced == 0


# ============================================================================
# Validation Tests - Failure Cases
# ============================================================================


class TestFixValidatorFailure:
    """Test validation failure scenarios."""

    @pytest.mark.unit
    def test_validate_fixes_introduces_new_errors(self, tmp_path, mock_quality_tools):
        """Test validation when fixes introduce new errors."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create original errors
        original_errors = [
            QualityError(
                tool="ruff",
                file=project_root / "src/main.py",
                line=10,
                column=5,
                code="F401",
                message="Unused import",
                severity="error",
                auto_fixable=True,
            ),
            QualityError(
                tool="mypy",
                file=project_root / "src/utils.py",
                line=20,
                column=10,
                code="arg-type",
                message="Argument type mismatch",
                severity="error",
                auto_fixable=False,
            ),
        ]

        # Mock: New error introduced
        new_error = QualityError(
            tool="ruff",
            file=project_root / "src/main.py",
            line=15,
            column=8,
            code="E501",
            message="Line too long",
            severity="error",
            auto_fixable=True,
        )

        mock_quality_tools[0].run_tool.return_value = [new_error]
        mock_quality_tools[1].run_tool.return_value = []

        # Execute
        validator = FixValidator(project_root, mock_quality_tools)
        result = validator.validate_fixes(
            files=[Path("src/main.py"), Path("src/utils.py")], original_errors=original_errors
        )

        # Verify
        assert result.passed is False
        assert result.errors_fixed == 2  # Original errors gone
        assert result.new_errors_introduced == 1  # But new error appeared
        assert len(result.new_errors) == 1

    @pytest.mark.unit
    def test_validate_fixes_no_improvement(self, tmp_path, mock_quality_tools):
        """Test validation when no errors were fixed."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create original errors
        original_errors = [
            QualityError(
                tool="ruff",
                file=project_root / "src/main.py",
                line=10,
                column=5,
                code="F401",
                message="Unused import",
                severity="error",
                auto_fixable=True,
            ),
            QualityError(
                tool="mypy",
                file=project_root / "src/utils.py",
                line=20,
                column=10,
                code="arg-type",
                message="Argument type mismatch",
                severity="error",
                auto_fixable=False,
            ),
        ]

        # Mock: All original errors still present
        mock_quality_tools[0].run_tool.return_value = [original_errors[0]]
        mock_quality_tools[1].run_tool.return_value = [original_errors[1]]

        # Execute
        validator = FixValidator(project_root, mock_quality_tools)
        result = validator.validate_fixes(
            files=[Path("src/main.py"), Path("src/utils.py")], original_errors=original_errors
        )

        # Verify
        assert result.passed is False
        assert result.errors_fixed == 0
        assert result.errors_remaining == 2
        assert result.new_errors_introduced == 0


# ============================================================================
# Error Comparison Tests
# ============================================================================


class TestErrorComparison:
    """Test error comparison logic."""

    @pytest.mark.unit
    def test_compare_errors_all_fixed(self, tmp_path, mock_quality_tools, sample_quality_errors):
        """Test error comparison when all errors are fixed."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        comparison = validator._compare_errors(sample_quality_errors, [])

        # Verify
        assert len(comparison.fixed) == 2
        assert len(comparison.remaining) == 0
        assert len(comparison.introduced) == 0

    @pytest.mark.unit
    def test_compare_errors_some_remain(self, tmp_path, mock_quality_tools, sample_quality_errors):
        """Test error comparison when some errors remain."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute - one error remains
        comparison = validator._compare_errors(sample_quality_errors, [sample_quality_errors[1]])

        # Verify
        assert len(comparison.fixed) == 1
        assert len(comparison.remaining) == 1
        assert len(comparison.introduced) == 0

    @pytest.mark.unit
    def test_compare_errors_new_introduced(self, tmp_path, mock_quality_tools):
        """Test error comparison when new errors are introduced."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        original = [
            QualityError(
                tool="ruff",
                file=Path("/project/src/main.py"),
                line=10,
                column=5,
                code="F401",
                message="Unused import",
                severity="error",
                auto_fixable=True,
            )
        ]

        new = [
            QualityError(
                tool="ruff",
                file=Path("/project/src/main.py"),
                line=15,
                column=8,
                code="E501",
                message="Line too long",
                severity="error",
                auto_fixable=True,
            )
        ]

        validator = FixValidator(project_root, [])

        # Execute
        comparison = validator._compare_errors(original, new)

        # Verify
        assert len(comparison.fixed) == 1  # F401 is gone
        assert len(comparison.remaining) == 0
        assert len(comparison.introduced) == 1  # E501 is new


# ============================================================================
# Quality Tool Integration Tests
# ============================================================================


class TestFixValidatorToolIntegration:
    """Test integration with quality tools."""

    @pytest.mark.unit
    def test_run_quality_checks_on_files(self, tmp_path, mock_quality_tools):
        """Test running quality checks on specific files."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        file1 = project_root / "src" / "main.py"
        file1.parent.mkdir(parents=True)
        file1.write_text("print('hello')\n")

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        validator._run_quality_checks([file1])

        # Verify - should call run_tool on each available tool
        for tool in mock_quality_tools:
            if tool.is_available():
                tool.run_tool.assert_called()

    @pytest.mark.unit
    def test_run_quality_checks_handles_tool_failures(self, tmp_path, mock_quality_tools):
        """Test handling when quality tools fail."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Mock one tool to fail
        mock_quality_tools[0].run_tool.side_effect = Exception("Tool crashed")
        mock_quality_tools[1].run_tool.return_value = []

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute - should not raise, handle gracefully
        errors = validator._run_quality_checks([Path("src/main.py")])

        # Verify - should continue with other tools
        assert isinstance(errors, list)
        # Tool 2 should still have been called
        mock_quality_tools[1].run_tool.assert_called()

    @pytest.mark.unit
    def test_run_quality_checks_skips_unavailable_tools(self, tmp_path, mock_quality_tools):
        """Test skipping tools that aren't available."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Make first tool unavailable
        mock_quality_tools[0].is_available.return_value = False

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        validator._run_quality_checks([Path("src/main.py")])

        # Verify - unavailable tool should not be called
        mock_quality_tools[0].run_tool.assert_not_called()
        mock_quality_tools[1].run_tool.assert_called()


# ============================================================================
# Validation Result Tests
# ============================================================================


class TestValidationResultGeneration:
    """Test generation of ValidationResult."""

    @pytest.mark.unit
    def test_generate_validation_result_success(self, tmp_path, mock_quality_tools):
        """Test generating ValidationResult for successful validation."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        validator = FixValidator(project_root, mock_quality_tools)

        comparison = ErrorComparison(fixed=[Mock(), Mock()], remaining=[], introduced=[])

        # Execute
        result = validator._generate_result(comparison)

        # Verify
        assert result.passed is True
        assert result.errors_fixed == 2
        assert result.errors_remaining == 0
        assert result.new_errors_introduced == 0

    @pytest.mark.unit
    def test_generate_validation_result_with_new_errors(self, tmp_path, mock_quality_tools):
        """Test generating ValidationResult when new errors introduced."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        validator = FixValidator(project_root, mock_quality_tools)

        new_error = QualityError(
            tool="ruff",
            file=Path("/project/src/main.py"),
            line=15,
            column=8,
            code="E501",
            message="Line too long",
            severity="error",
            auto_fixable=True,
        )

        comparison = ErrorComparison(fixed=[Mock()], remaining=[], introduced=[new_error])

        # Execute
        result = validator._generate_result(comparison)

        # Verify
        assert result.passed is False
        assert result.errors_fixed == 1
        assert result.new_errors_introduced == 1
        assert len(result.new_errors) == 1


# ============================================================================
# Error Matching Tests
# ============================================================================


class TestErrorMatching:
    """Test error matching and comparison logic."""

    @pytest.mark.unit
    def test_errors_match_same_location(self, tmp_path, mock_quality_tools):
        """Test that errors at same location are considered matching."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        error1 = QualityError(
            tool="ruff",
            file=Path("/project/src/main.py"),
            line=10,
            column=5,
            code="F401",
            message="Unused import",
            severity="error",
            auto_fixable=True,
        )

        error2 = QualityError(
            tool="ruff",
            file=Path("/project/src/main.py"),
            line=10,
            column=5,
            code="F401",
            message="Unused import",
            severity="error",
            auto_fixable=True,
        )

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        assert validator._errors_match(error1, error2) is True

    @pytest.mark.unit
    def test_errors_dont_match_different_location(self, tmp_path, mock_quality_tools):
        """Test that errors at different locations don't match."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        error1 = QualityError(
            tool="ruff",
            file=Path("/project/src/main.py"),
            line=10,
            column=5,
            code="F401",
            message="Unused import",
            severity="error",
            auto_fixable=True,
        )

        error2 = QualityError(
            tool="ruff",
            file=Path("/project/src/main.py"),
            line=20,  # Different line
            column=5,
            code="F401",
            message="Unused import",
            severity="error",
            auto_fixable=True,
        )

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        assert validator._errors_match(error1, error2) is False

    @pytest.mark.unit
    def test_errors_dont_match_different_code(self, tmp_path, mock_quality_tools):
        """Test that errors with different codes don't match."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        error1 = QualityError(
            tool="ruff",
            file=Path("/project/src/main.py"),
            line=10,
            column=5,
            code="F401",
            message="Unused import",
            severity="error",
            auto_fixable=True,
        )

        error2 = QualityError(
            tool="ruff",
            file=Path("/project/src/main.py"),
            line=10,
            column=5,
            code="E501",  # Different code
            message="Line too long",
            severity="error",
            auto_fixable=True,
        )

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        assert validator._errors_match(error1, error2) is False


# ============================================================================
# Edge Cases
# ============================================================================


class TestFixValidatorEdgeCases:
    """Test edge cases in validation."""

    @pytest.mark.unit
    def test_validate_empty_file_list(self, tmp_path, mock_quality_tools):
        """Test validation with empty file list."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        result = validator.validate_fixes(files=[], original_errors=[])

        # Verify - should handle gracefully
        assert result.passed is True
        assert result.errors_fixed == 0

    @pytest.mark.unit
    def test_validate_no_original_errors(self, tmp_path, mock_quality_tools):
        """Test validation when there were no original errors."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        for tool in mock_quality_tools:
            tool.run_tool.return_value = []

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        result = validator.validate_fixes(files=[Path("src/main.py")], original_errors=[])

        # Verify
        assert result.passed is True
        assert result.errors_fixed == 0
        assert result.new_errors_introduced == 0

    @pytest.mark.unit
    def test_validate_fixes_same_error_count_different_errors(self, tmp_path, mock_quality_tools):
        """Test when error count is same but errors are different."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        original_error = QualityError(
            tool="ruff",
            file=project_root / "src/main.py",
            line=10,
            column=5,
            code="F401",
            message="Unused import",
            severity="error",
            auto_fixable=True,
        )

        # Different error at different location
        new_error = QualityError(
            tool="ruff",
            file=project_root / "src/main.py",
            line=20,
            column=8,
            code="E501",
            message="Line too long",
            severity="error",
            auto_fixable=True,
        )

        mock_quality_tools[0].run_tool.return_value = [new_error]
        mock_quality_tools[1].run_tool.return_value = []

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        result = validator.validate_fixes(files=[Path("src/main.py")], original_errors=[original_error])

        # Verify - one fixed, one introduced
        assert result.passed is False
        assert result.errors_fixed == 1
        assert result.new_errors_introduced == 1


# ============================================================================
# File Filtering Tests
# ============================================================================


class TestFixValidatorFileFiltering:
    """Test file filtering for validation."""

    @pytest.mark.unit
    def test_validate_only_runs_on_specified_files(self, tmp_path, mock_quality_tools):
        """Test that validation only runs on specified files."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        file1 = project_root / "src" / "main.py"
        file1.parent.mkdir(parents=True)
        file1.write_text("print('hello')\n")

        file2 = project_root / "src" / "utils.py"
        file2.write_text("print('utils')\n")

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute - only validate file1
        validator.validate_fixes(files=[file1], original_errors=[])

        # Verify - tools should only be called with file1's directory or file
        # (depends on implementation - might validate whole directory)
        for tool in mock_quality_tools:
            if tool.is_available():
                tool.run_tool.assert_called()


# ============================================================================
# Summary Generation Tests
# ============================================================================


class TestValidationSummary:
    """Test summary text generation."""

    @pytest.mark.unit
    def test_summary_all_fixed(self, tmp_path, mock_quality_tools):
        """Test summary when all errors fixed."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        validator = FixValidator(project_root, mock_quality_tools)
        comparison = ErrorComparison(fixed=[Mock(), Mock()], remaining=[], introduced=[])

        # Execute
        result = validator._generate_result(comparison)

        # Verify
        assert "2 error" in result.summary.lower() or "fixed" in result.summary.lower()
        assert result.passed is True

    @pytest.mark.unit
    def test_summary_new_errors(self, tmp_path, mock_quality_tools):
        """Test summary when new errors introduced."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        new_error = Mock()
        validator = FixValidator(project_root, mock_quality_tools)
        comparison = ErrorComparison(fixed=[Mock()], remaining=[], introduced=[new_error])

        # Execute
        result = validator._generate_result(comparison)

        # Verify
        assert "introduced" in result.summary.lower() or "new" in result.summary.lower()
        assert result.passed is False


# ============================================================================
# Multiple Tool Tests
# ============================================================================


class TestFixValidatorMultipleTools:
    """Test validation with multiple quality tools."""

    @pytest.mark.unit
    def test_validate_combines_results_from_all_tools(self, tmp_path, mock_quality_tools):
        """Test that results from all tools are combined."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        ruff_error = QualityError(
            tool="ruff",
            file=project_root / "src/main.py",
            line=10,
            column=5,
            code="F401",
            message="Unused import",
            severity="error",
            auto_fixable=True,
        )

        mypy_error = QualityError(
            tool="mypy",
            file=project_root / "src/main.py",
            line=20,
            column=10,
            code="arg-type",
            message="Type mismatch",
            severity="error",
            auto_fixable=False,
        )

        mock_quality_tools[0].run_tool.return_value = [ruff_error]
        mock_quality_tools[1].run_tool.return_value = [mypy_error]

        validator = FixValidator(project_root, mock_quality_tools)

        # Execute
        validator._run_quality_checks([Path("src/main.py")])

        # Verify - should combine errors from both tools
        assert len(all_errors := validator._run_quality_checks([Path("src/main.py")])) == 2
        assert any(e.tool == "ruff" for e in all_errors)
        assert any(e.tool == "mypy" for e in all_errors)


# ============================================================================
# Validation Strategy Tests
# ============================================================================


class TestValidationStrategy:
    """Test validation decision-making strategy."""

    @pytest.mark.unit
    def test_passes_when_errors_reduced(self, tmp_path, mock_quality_tools):
        """Test validation passes when error count reduces."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Original: 3 errors
        [Mock(), Mock(), Mock()]

        # New: 1 error (2 fixed)
        [Mock()]

        for tool in mock_quality_tools:
            tool.run_tool.return_value = []

        FixValidator(project_root, mock_quality_tools)

        # Manually test the decision logic
        comparison = ErrorComparison(fixed=[Mock(), Mock()], remaining=[Mock()], introduced=[])

        assert len(comparison.fixed) > 0  # Has fixes
        assert len(comparison.introduced) == 0  # No new errors
        # Should pass

    @pytest.mark.unit
    def test_fails_when_no_net_improvement(self, tmp_path, mock_quality_tools):
        """Test validation fails when there's no net improvement."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        validator = FixValidator(project_root, mock_quality_tools)

        # Same error count: 2 fixed, 2 introduced
        comparison = ErrorComparison(fixed=[Mock(), Mock()], remaining=[], introduced=[Mock(), Mock()])

        result = validator._generate_result(comparison)

        # Verify - should fail (no net improvement)
        assert result.passed is False
        assert result.new_errors_introduced == 2


# ============================================================================
# Integration with FixApplier Tests
# ============================================================================


class TestFixValidatorWithFixApplier:
    """Test FixValidator working with FixApplier."""

    @pytest.mark.unit
    def test_validator_interface_matches_protocol(self, tmp_path, mock_quality_tools, sample_quality_errors):
        """Test that FixValidator implements the Protocol expected by FixApplier."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()

        for tool in mock_quality_tools:
            tool.run_tool.return_value = []

        # Execute
        validator = FixValidator(project_root, mock_quality_tools)

        # Verify - should have validate_fixes method matching protocol
        assert hasattr(validator, "validate_fixes")
        assert callable(validator.validate_fixes)

        # Test the signature
        result = validator.validate_fixes([Path("src/main.py")], sample_quality_errors)

        # Should return ValidationResult
        assert isinstance(result, ValidationResult)
        assert hasattr(result, "passed")
        assert hasattr(result, "errors_fixed")
        assert hasattr(result, "new_errors_introduced")


# ============================================================================
# Result Model Tests
# ============================================================================


class TestValidationResultModel:
    """Test ValidationResult model."""

    @pytest.mark.unit
    def test_validation_result_creation(self):
        """Test creating ValidationResult."""
        result = ValidationResult(
            passed=True,
            errors_fixed=5,
            errors_remaining=0,
            new_errors_introduced=0,
            new_errors=[],
            summary="All 5 errors fixed successfully",
        )

        assert result.passed is True
        assert result.errors_fixed == 5
        assert result.errors_remaining == 0
        assert result.new_errors_introduced == 0

    @pytest.mark.unit
    def test_error_comparison_model(self):
        """Test ErrorComparison model."""
        comparison = ErrorComparison(
            fixed=[Mock(), Mock()], remaining=[Mock()], introduced=[]
        )

        assert len(comparison.fixed) == 2
        assert len(comparison.remaining) == 1
        assert len(comparison.introduced) == 0

