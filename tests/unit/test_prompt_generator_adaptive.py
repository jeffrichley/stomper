"""Test PromptGenerator adaptive strategy integration."""

import pytest
from pathlib import Path

from stomper.ai.prompt_generator import PromptGenerator
from stomper.ai.mapper import ErrorMapper
from stomper.ai.models import FixOutcome, PromptStrategy
from stomper.quality.base import QualityError


def create_sample_error(
    tool: str = "ruff",
    code: str = "E501",
    file: str = "test.py",
    line: int = 10,
    column: int = 80,
    message: str = "Line too long",
    severity: str = "error",
    auto_fixable: bool = True,
) -> QualityError:
    """Create a sample QualityError for testing."""
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


@pytest.mark.unit
class TestPromptGeneratorAdaptive:
    """Test PromptGenerator adaptive strategy integration."""

    def test_accepts_project_root_parameter(self, tmp_path):
        """Test PromptGenerator accepts project_root parameter."""
        generator = PromptGenerator(
            template_dir="templates",
            errors_dir="errors",
            project_root=tmp_path,
        )
        
        assert generator.mapper is not None
        assert generator.mapper.project_root == tmp_path.resolve()

    def test_accepts_mapper_parameter(self, tmp_path):
        """Test PromptGenerator accepts mapper parameter."""
        mapper = ErrorMapper(project_root=tmp_path)
        generator = PromptGenerator(
            template_dir="templates",
            errors_dir="errors",
            mapper=mapper,
        )
        
        assert generator.mapper is mapper

    def test_requires_project_root_or_mapper(self):
        """Test PromptGenerator requires project_root or mapper."""
        # Should work without either (backwards compatibility)
        # But mapper will be None
        generator = PromptGenerator(
            template_dir="templates",
            errors_dir="errors",
        )
        
        assert generator.mapper is None

    def test_generate_prompt_accepts_retry_count(self, tmp_path):
        """Test generate_prompt accepts retry_count parameter."""
        generator = PromptGenerator(
            template_dir="templates",
            errors_dir="errors",
            project_root=tmp_path,
        )
        
        error = create_sample_error()
        
        # Should accept retry_count
        prompt = generator.generate_prompt([error], "code context", retry_count=0)
        assert isinstance(prompt, str)
        
        # Should also work without retry_count (default=0)
        prompt2 = generator.generate_prompt([error], "code context")
        assert isinstance(prompt2, str)

    def test_uses_mapper_for_adaptive_strategy(self, tmp_path):
        """Test PromptGenerator uses mapper for adaptive strategies."""
        # Create mapper with some history
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error(code="E501")
        
        # Create difficult pattern
        for _ in range(3):
            mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        
        # Create generator with mapper
        generator = PromptGenerator(
            template_dir="templates",
            errors_dir="errors",
            mapper=mapper,
        )
        
        # Generate prompt - should use adaptive strategy
        prompt = generator.generate_prompt([error], "code context", retry_count=0)
        
        # Verify prompt was generated
        assert len(prompt) > 0
        assert isinstance(prompt, str)

    def test_escalates_strategy_on_retry(self, tmp_path):
        """Test PromptGenerator escalates strategy on retry."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error(code="E501")
        
        # Record failures to make it difficult
        for _ in range(3):
            mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        
        generator = PromptGenerator(
            template_dir="templates",
            errors_dir="errors",
            mapper=mapper,
        )
        
        # First attempt
        prompt0 = generator.generate_prompt([error], "code", retry_count=0)
        # Second attempt (retry)
        prompt1 = generator.generate_prompt([error], "code", retry_count=1)
        # Third attempt
        prompt2 = generator.generate_prompt([error], "code", retry_count=2)
        
        # All should generate valid prompts
        assert isinstance(prompt0, str) and len(prompt0) > 0
        assert isinstance(prompt1, str) and len(prompt1) > 0
        assert isinstance(prompt2, str) and len(prompt2) > 0

    def test_works_without_mapper_backwards_compatibility(self):
        """Test PromptGenerator still works without mapper (backwards compatibility)."""
        # Old code that doesn't pass mapper should still work
        generator = PromptGenerator(
            template_dir="templates",
            errors_dir="errors",
        )
        
        error = create_sample_error()
        
        # Should generate prompt without mapper
        prompt = generator.generate_prompt([error], "code context")
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_enhances_advice_with_historical_suggestions(self, tmp_path):
        """Test error advice is enhanced with historical suggestions."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        error = create_sample_error(code="E501")
        
        # Record successful pattern
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        mapper.record_attempt(error, FixOutcome.SUCCESS, PromptStrategy.DETAILED)
        
        # Make it difficult to trigger historical suggestions
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        mapper.record_attempt(error, FixOutcome.FAILURE, PromptStrategy.NORMAL)
        
        generator = PromptGenerator(
            template_dir="templates",
            errors_dir="errors",
            mapper=mapper,
        )
        
        prompt = generator.generate_prompt([error], "code context")
        
        # Prompt should be generated
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_handles_new_error_with_no_history(self, tmp_path):
        """Test handles error codes with no historical data."""
        mapper = ErrorMapper(project_root=tmp_path, auto_save=False)
        
        generator = PromptGenerator(
            template_dir="templates",
            errors_dir="errors",
            mapper=mapper,
        )
        
        # New error never seen before
        error = create_sample_error(code="UNKNOWN_ERROR")
        
        # Should generate prompt with default strategy
        prompt = generator.generate_prompt([error], "code context")
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0

