"""PromptGenerator class for converting errors to AI agent prompts."""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from stomper.quality.base import QualityError

logger = logging.getLogger(__name__)


class PromptGenerator:
    """Generates prompts for AI agents based on quality errors and code context."""
    
    def __init__(
        self, 
        template_dir: str = "templates", 
        errors_dir: str = "errors"
    ):
        """Initialize the PromptGenerator.
        
        Args:
            template_dir: Directory containing Jinja2 templates
            errors_dir: Directory containing error mapping files
        """
        self.template_dir = Path(template_dir)
        self.errors_dir = Path(errors_dir)
        
        # Initialize Jinja2 environment
        self.env = Environment(loader=FileSystemLoader(template_dir))
    
    def generate_prompt(self, errors: List[QualityError], code_context: str) -> str:
        """Generate a prompt for AI agents based on errors and code context.
        
        Args:
            errors: List of quality errors to fix
            code_context: Surrounding code context
            
        Returns:
            Generated prompt string
            
        Raises:
            FileNotFoundError: If template file is not found
        """
        if not errors:
            logger.warning("No errors provided to PromptGenerator")
            return self._generate_empty_prompt()
        
        # Extract error context
        error_context = self._extract_error_context(errors)
        
        # Load error-specific advice
        error_advice = self._load_error_advice(errors)
        
        # Process code context
        processed_code_context = self._process_code_context(code_context)
        
        # Generate prompt using template
        try:
            template = self.env.get_template("fix_prompt.j2")
            prompt = template.render(
                error_context=error_context,
                error_advice=error_advice,
                code_context=processed_code_context
            )
            
            # Return the full prompt without any optimization
            
            return prompt
            
        except TemplateNotFound:
            logger.error(f"Template file not found in {self.template_dir}")
            raise FileNotFoundError(f"Template file not found in {self.template_dir}")
    
    def _extract_error_context(self, errors: List[QualityError]) -> Dict[str, Any]:
        """Extract structured context from quality errors.
        
        Args:
            errors: List of quality errors
            
        Returns:
            Dictionary containing error context
        """
        # Group errors by tool
        error_groups = {}
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
                        "file": str(error.file)
                    }
                    for error in tool_errors
                ],
                "fixing_rules": self._get_fixing_rules_for_tool(tool),
                "instructions": self._get_instructions_for_tool(tool)
            }
            structured_groups.append(group)
        
        return {
            "error_count": len(errors),
            "error_groups": structured_groups,
            "tool_outputs": list(error_groups.keys()),
            "validation_status": "complete"
        }
    
    def _load_error_advice(self, errors: List[QualityError]) -> Dict[str, str]:
        """Load error-specific advice from mapping files.
        
        Args:
            errors: List of quality errors
            
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
                    advice[error_code] = advice_file.read_text(encoding='utf-8')
                except Exception as e:
                    logger.warning(f"Failed to read advice file {advice_file}: {e}")
                    advice[error_code] = f"Fix {error_code}: {error.message}"
            else:
                # Fallback to generic advice
                advice[error_code] = f"Fix {error_code}: {error.message}"
        
        return advice
    
    def _process_code_context(self, code_context: str) -> str:
        """Process code context for inclusion in prompts.
        
        Args:
            code_context: Raw code context
            
        Returns:
            Processed code context
        """
        if not code_context or not code_context.strip():
            return "No code context available"
        
        # Return full code context without truncation
        return code_context
    
    def _generate_empty_prompt(self) -> str:
        """Generate a prompt when no errors are provided."""
        return "No errors found to fix."
    
    def _get_advice_file_path(self, tool: str, error_code: str) -> Optional[Path]:
        """Get the path to an advice file for a specific error.
        
        Args:
            tool: Quality tool name
            error_code: Error code
            
        Returns:
            Path to advice file, or None if not found
        """
        # Map tool names to directory names
        tool_dirs = {
            "ruff": "ruff",
            "mypy": "mypy", 
            "drill-sergeant": "drill-sergeant"
        }
        
        tool_dir = tool_dirs.get(tool, tool)
        advice_file = self.errors_dir / tool_dir / f"{error_code}.md"
        
        return advice_file if advice_file.exists() else None
    
    def _get_fixing_rules_for_tool(self, tool: str) -> List[str]:
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
                "Eliminate duplicate or redundant code patterns"
            ],
            "mypy": [
                "Correct operand mismatches",
                "Align function return types with type hints", 
                "Adjust function arguments to match defaults"
            ],
            "drill-sergeant": [
                "Improve test quality and coverage",
                "Fix test naming conventions",
                "Add missing test cases"
            ]
        }
        
        return rules_map.get(tool, ["Fix quality issues"])
    
    def _get_instructions_for_tool(self, tool: str) -> List[str]:
        """Get instructions for a specific tool.
        
        Args:
            tool: Quality tool name
            
        Returns:
            List of instructions
        """
        instructions_map = {
            "ruff": [
                "ACTION: Apply each auto-fix deterministically",
                "ENSURE: Resulting code compiles"
            ],
            "mypy": [
                "ACTION: Rewrite code so mypy passes cleanly",
                "AVOID: Using # type: ignore",
                "ADD: Type hints where missing or unclear"
            ],
            "drill-sergeant": [
                "ACTION: Improve test quality and structure",
                "ENSURE: Tests are comprehensive and well-named"
            ]
        }
        
        return instructions_map.get(tool, ["ACTION: Fix the identified issues"])
