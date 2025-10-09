"""PromptGenerator class for converting errors to AI agent prompts."""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from stomper.quality.base import QualityError

logger = logging.getLogger(__name__)


class PromptGenerator:
    """Generates prompts for AI agents based on quality errors and code context."""

    def __init__(
        self,
        template_dir: str = "templates",
        errors_dir: str = "errors",
        project_root: Path | None = None,
        mapper: Any | None = None,
    ):
        """Initialize the PromptGenerator.

        Args:
            template_dir: Directory containing Jinja2 templates
            errors_dir: Directory containing error mapping files
            project_root: Main project root (for mapper initialization)
            mapper: Error mapper for adaptive strategies (optional)
        """
        self.template_dir = Path(template_dir)
        self.errors_dir = Path(errors_dir)

        # Create mapper if not provided (requires project_root)
        if mapper is None:
            if project_root is not None:
                # Import here to avoid circular dependency
                from stomper.ai.mapper import ErrorMapper

                self.mapper = ErrorMapper(project_root=project_root)
                logger.info("PromptGenerator initialized with adaptive learning")
            else:
                # No mapper - backwards compatibility mode
                self.mapper = None
                logger.debug("PromptGenerator initialized without adaptive learning")
        else:
            self.mapper = mapper
            logger.info("PromptGenerator initialized with provided mapper")

        # Initialize Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate_prompt(
        self,
        errors: list[QualityError],
        code_context: str,
        retry_count: int = 0,
    ) -> str:
        """Generate a prompt for AI agents based on errors and code context.

        Args:
            errors: List of quality errors to fix
            code_context: Surrounding code context
            retry_count: Number of retry attempts (for adaptive strategies)

        Returns:
            Generated prompt string

        Raises:
            FileNotFoundError: If template file is not found
        """
        if not errors:
            logger.warning("No errors provided to PromptGenerator")
            return self._generate_empty_prompt()

        # Get adaptive strategy for primary error (if mapper available)
        adaptive_strategy = None
        if self.mapper:
            primary_error = errors[0]
            adaptive_strategy = self.mapper.get_adaptive_strategy(
                primary_error,
                retry_count=retry_count,
            )
            logger.debug(
                f"Using {adaptive_strategy.verbosity.value} strategy for {primary_error.code} "
                f"(retry #{retry_count})"
            )

        # Extract error context
        error_context = self._extract_error_context(errors)

        # Load error-specific advice (enhanced with adaptive strategy)
        error_advice = self._load_error_advice(errors, adaptive_strategy)

        # Process code context (adapt based on strategy)
        processed_code_context = self._process_code_context(code_context, adaptive_strategy)

        # Add adaptive strategy to context (for template)
        if adaptive_strategy:
            error_context["adaptive_strategy"] = {
                "verbosity": adaptive_strategy.verbosity.value,
                "retry_count": adaptive_strategy.retry_count,
                "include_examples": adaptive_strategy.include_examples,
                "include_history": adaptive_strategy.include_history,
                "suggested_approach": adaptive_strategy.suggested_approach,
            }

        # Generate prompt using template
        try:
            template = self.env.get_template("fix_prompt.j2")
            prompt = template.render(
                error_context=error_context,
                error_advice=error_advice,
                code_context=processed_code_context,
                adaptive_strategy=adaptive_strategy,
            )

            # Return the full prompt without any optimization

            return prompt

        except TemplateNotFound:
            logger.error(f"Template file not found in {self.template_dir}")
            raise FileNotFoundError(f"Template file not found in {self.template_dir}")

    def _extract_error_context(self, errors: list[QualityError]) -> dict[str, Any]:
        """Extract structured context from quality errors.

        Args:
            errors: List of quality errors

        Returns:
            Dictionary containing error context
        """
        # Group errors by tool
        error_groups: dict[str, list[QualityError]] = {}
        for error in errors:
            tool = error.tool
            if tool not in error_groups:
                error_groups[tool] = []
            error_groups[tool].append(error)

        # Convert to structured format
        structured_groups = []
        for tool, tool_errors in error_groups.items():
            group = {
                "tool": tool,
                "name": f"{tool}_errors",
                "title": f"Fix {tool.title()} Issues",
                "errors": [
                    {
                        "line": error.line,
                        "column": error.column,
                        "code": error.code,
                        "message": error.message,
                        "severity": error.severity,
                        "auto_fixable": error.auto_fixable,
                        "file": str(error.file),
                    }
                    for error in tool_errors
                ],
                "fixing_rules": self._get_fixing_rules_for_tool(tool),
                "instructions": self._get_instructions_for_tool(tool),
            }
            structured_groups.append(group)

        return {
            "error_count": len(errors),
            "error_groups": structured_groups,
            "tool_outputs": list(error_groups.keys()),
            "validation_status": "complete",
        }

    def _load_error_advice(
        self,
        errors: list[QualityError],
        adaptive_strategy: Any | None = None,
    ) -> dict[str, str]:
        """Load error-specific advice from mapping files.

        Args:
            errors: List of quality errors
            adaptive_strategy: Adaptive strategy for this fix (optional)

        Returns:
            Dictionary mapping error codes to advice
        """
        advice = {}

        for error in errors:
            error_code = error.code
            tool = error.tool

            # Try to load advice file
            advice_file = self._get_advice_file_path(tool, error_code)
            if advice_file and advice_file.exists():
                try:
                    base_advice = advice_file.read_text(encoding="utf-8")

                    # Enhance advice with adaptive strategy suggestions
                    if adaptive_strategy and adaptive_strategy.suggested_approach:
                        enhanced_advice = (
                            f"{base_advice}\n\n"
                            f"**💡 Recommended Approach (based on history):**\n"
                            f"{adaptive_strategy.suggested_approach}"
                        )
                        advice[error_code] = enhanced_advice
                    else:
                        advice[error_code] = base_advice

                except Exception as e:
                    logger.warning(f"Failed to read advice file {advice_file}: {e}")
                    advice[error_code] = f"Fix {error_code}: {error.message}"
            else:
                # Fallback to generic advice
                advice[error_code] = f"Fix {error_code}: {error.message}"

        return advice

    def _process_code_context(
        self,
        code_context: str,
        adaptive_strategy: Any | None = None,
    ) -> str:
        """Process code context for inclusion in prompts.

        Args:
            code_context: Raw code context
            adaptive_strategy: Strategy for this fix (optional)

        Returns:
            Processed code context
        """
        if not code_context or not code_context.strip():
            return "No code context available"

        # For detailed/verbose strategies, include more context
        # For minimal strategy, could provide less context
        # (Currently just returns full context, but hook is here for future)

        return code_context

    def _generate_empty_prompt(self) -> str:
        """Generate a prompt when no errors are provided."""
        return "No errors found to fix."

    def _get_advice_file_path(self, tool: str, error_code: str) -> Path | None:
        """Get the path to an advice file for a specific error.

        Args:
            tool: Quality tool name
            error_code: Error code

        Returns:
            Path to advice file, or None if not found
        """
        # Map tool names to directory names
        tool_dirs = {"ruff": "ruff", "mypy": "mypy", "drill-sergeant": "drill-sergeant"}

        tool_dir = tool_dirs.get(tool, tool)
        advice_file = self.errors_dir / tool_dir / f"{error_code}.md"

        return advice_file if advice_file.exists() else None

    def _get_fixing_rules_for_tool(self, tool: str) -> list[str]:
        """Get fixing rules for a specific tool.

        Args:
            tool: Quality tool name

        Returns:
            List of fixing rules
        """
        rules_map = {
            "ruff": [
                "Remove unused imports (F401)",
                "Apply formatting corrections",
                "Eliminate duplicate or redundant code patterns",
            ],
            "mypy": [
                "Correct operand mismatches",
                "Align function return types with type hints",
                "Adjust function arguments to match defaults",
            ],
            "drill-sergeant": [
                "Improve test quality and coverage",
                "Fix test naming conventions",
                "Add missing test cases",
            ],
        }

        return rules_map.get(tool, ["Fix quality issues"])

    def _get_instructions_for_tool(self, tool: str) -> list[str]:
        """Get instructions for a specific tool.

        Args:
            tool: Quality tool name

        Returns:
            List of instructions
        """
        instructions_map = {
            "ruff": [
                "ACTION: Apply each auto-fix deterministically",
                "ENSURE: Resulting code compiles",
            ],
            "mypy": [
                "ACTION: Rewrite code so mypy passes cleanly",
                "AVOID: Using # type: ignore",
                "ADD: Type hints where missing or unclear",
            ],
            "drill-sergeant": [
                "ACTION: Improve test quality and structure",
                "ENSURE: Tests are comprehensive and well-named",
            ],
        }

        return instructions_map.get(tool, ["ACTION: Fix the identified issues"])
