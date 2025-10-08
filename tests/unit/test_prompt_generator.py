"""Tests for PromptGenerator class - focused on non-brittle testing."""

from pathlib import Path

import pytest

from stomper.quality.base import QualityError


def create_sample_error(
    tool: str = "ruff",
    file: str = "test.py",
    line: int = 1,
    column: int = 0,
    code: str = "E501",
    message: str = "Line too long",
    severity: str = "error",
    auto_fixable: bool = True,
) -> QualityError:
    """Factory for creating test errors without hardcoded strings."""
    return QualityError(
        tool=tool,
        file=Path(file),
        line=line,
        column=column,
        code=code,
        message=message,
        severity=severity,
        auto_fixable=auto_fixable,
    )


def create_sample_errors() -> list[QualityError]:
    """Create a set of sample errors for testing."""
    return [
        create_sample_error(code="E501", message="Line too long"),
        create_sample_error(code="F401", message="Unused import"),
        create_sample_error(
            tool="mypy", code="missing-return-type", message="Missing return type annotation"
        ),
    ]


class TestPromptGenerator:
    """Test cases for PromptGenerator class."""

    def test_generates_prompt_with_errors(self):
        """Test that prompt is generated when errors are provided."""
        # Import here to avoid circular imports during test discovery
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = [create_sample_error()]

        prompt = generator.generate_prompt(errors, "some code")

        # Test behavior, not content
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "error" in prompt.lower()  # Should contain error-related content

    def test_handles_empty_errors_gracefully(self):
        """Test behavior with no errors."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()

        prompt = generator.generate_prompt([], "some code")

        assert isinstance(prompt, str)
        # Should still generate a prompt, even if empty

    def test_includes_error_codes_in_prompt(self):
        """Test that error codes are included in the prompt."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = [create_sample_error(code="E501")]

        prompt = generator.generate_prompt(errors, "some code")

        assert "E501" in prompt  # Error code should be present

    def test_includes_line_numbers_in_prompt(self):
        """Test that line numbers are included."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = [create_sample_error(line=42)]

        prompt = generator.generate_prompt(errors, "some code")

        assert "42" in prompt  # Line number should be present

    def test_template_rendering_works(self):
        """Test that Jinja2 template rendering works without content validation."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = create_sample_errors()

        # This should not raise an exception
        prompt = generator.generate_prompt(errors, "some code")

        # Test that template variables are substituted
        assert "{{" not in prompt  # No unrendered template variables
        assert "}}" not in prompt

    def test_handles_missing_template_gracefully(self):
        """Test behavior when template file is missing."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator(template_dir="nonexistent")
        errors = create_sample_errors()

        with pytest.raises(FileNotFoundError):
            generator.generate_prompt(errors, "some code")

    def test_extracts_error_context_correctly(self):
        """Test that error context is extracted into proper structure."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = create_sample_errors()

        context = generator._extract_error_context(errors)

        # Test structure, not content
        assert "error_count" in context
        assert "error_groups" in context
        assert "tool_outputs" in context

        assert context["error_count"] == len(errors)
        assert isinstance(context["error_groups"], list)

    def test_groups_errors_by_tool(self):
        """Test that errors are grouped by tool type."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = [
            create_sample_error(tool="ruff", code="E501"),
            create_sample_error(tool="ruff", code="F401"),
            create_sample_error(tool="mypy", code="missing-return-type"),
        ]

        context = generator._extract_error_context(errors)

        # Should have 2 groups: ruff and mypy
        assert len(context["error_groups"]) == 2
        ruff_group = next(g for g in context["error_groups"] if g["tool"] == "ruff")
        mypy_group = next(g for g in context["error_groups"] if g["tool"] == "mypy")

        assert len(ruff_group["errors"]) == 2
        assert len(mypy_group["errors"]) == 1

    def test_loads_error_advice_from_files(self):
        """Test that error advice is loaded from mapping files."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = [create_sample_error(code="E501")]

        advice = generator._load_error_advice(errors)

        # Test structure, not content
        assert isinstance(advice, dict)
        assert "E501" in advice
        assert isinstance(advice["E501"], str)
        assert len(advice["E501"]) > 0

    def test_handles_missing_advice_files_gracefully(self):
        """Test behavior when advice files are missing."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator(errors_dir="nonexistent")
        errors = [create_sample_error(code="E501")]

        advice = generator._load_error_advice(errors)

        # Should return empty dict or default advice
        assert isinstance(advice, dict)
        # Don't test specific content, just that it doesn't crash

    def test_includes_code_context_in_prompt(self):
        """Test that code context is NOT included in the prompt (available in worktree)."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = create_sample_errors()
        code_context = "def hello():\n    print('world')"

        prompt = generator.generate_prompt(errors, code_context)

        # Code context should NOT be in prompt - it's in the git worktree
        assert "def hello()" not in prompt
        assert "available in the git worktree" in prompt

    def test_handles_large_code_context(self):
        """Test behavior with large code context."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = create_sample_errors()
        large_code = "def func():\n" + "    pass\n" * 1000  # 1000 lines

        prompt = generator.generate_prompt(errors, large_code)

        # Should not crash and should include some context
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_includes_full_code_context(self):
        """Test that code context is NOT included (even when large)."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = create_sample_errors()
        large_code = "def func():\n" + "    pass\n" * 1000  # 1000 lines

        prompt = generator.generate_prompt(errors, large_code)

        # Code should NOT be in prompt - it's in the git worktree
        assert "def func():" not in prompt
        assert "available in the git worktree" in prompt
        # Prompt should be reasonably sized
        assert len(prompt) < 10000  # Should be much smaller without code

    def test_generates_complete_prompts(self):
        """Test that complete prompts are generated without artificial size limits."""
        from stomper.ai.prompt_generator import PromptGenerator

        generator = PromptGenerator()
        errors = create_sample_errors()

        prompt = generator.generate_prompt(errors, "some code")

        # Should generate a complete prompt
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Should not contain truncation markers
        assert "... (truncated)" not in prompt
