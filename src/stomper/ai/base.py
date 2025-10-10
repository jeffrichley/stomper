"""Base AI Agent protocol and models for swappable AI agents."""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator


class AgentCapabilities(BaseModel):
    """Agent capabilities and limitations."""

    can_fix_linting: bool = Field(default=True, description="Can fix linting errors")
    can_fix_types: bool = Field(default=True, description="Can fix type errors")
    can_fix_tests: bool = Field(default=False, description="Can fix test failures")
    max_context_length: int = Field(default=4000, description="Maximum context length in tokens")
    supported_languages: list[str] = Field(
        default=["python"], description="Supported programming languages"
    )

    @field_validator("max_context_length")
    @classmethod
    def validate_max_context_length(cls, v):
        if v <= 0:
            raise ValueError("max_context_length must be positive")
        return v

    @field_validator("supported_languages")
    @classmethod
    def validate_supported_languages(cls, v):
        if not v:
            raise ValueError("supported_languages cannot be empty")
        return v


class AgentInfo(BaseModel):
    """Agent metadata and information."""

    name: str = Field(description="Agent name")
    version: str = Field(description="Agent version")
    description: str = Field(description="Agent description")
    capabilities: AgentCapabilities = Field(description="Agent capabilities")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("version")
    @classmethod
    def validate_version(cls, v):
        if not v or not v.strip():
            raise ValueError("version cannot be empty")
        return v.strip()


@runtime_checkable
class AIAgent(Protocol):
    """Protocol for swappable AI agents."""

    def generate_fix(self, error_context: dict[str, Any], code_context: str, prompt: str) -> None:
        """Generate fix for given error context and code.

        Args:
            error_context: Error details including type, location, message
            code_context: Surrounding code context
            prompt: Specific fix instructions

        Returns:
            None - modifies file in place
        """
        ...

    def validate_response(self, response: str) -> bool:
        """Validate AI response before applying.

        Args:
            response: AI-generated response to validate

        Returns:
            True if response is valid, False otherwise
        """
        ...

    def get_agent_info(self) -> AgentInfo:
        """Get agent metadata and capabilities.

        Returns:
            Agent information and capabilities
        """
        ...


class BaseAIAgent(ABC):
    """Abstract base class for AI agents implementing the AIAgent protocol."""

    def __init__(self, agent_info: AgentInfo):
        """Initialize base AI agent.

        Args:
            agent_info: Agent metadata and capabilities
        """
        self._agent_info = agent_info

    @abstractmethod
    def generate_fix(self, error_context: dict[str, Any], code_context: str, prompt: str) -> None:
        """Generate fix for given error context and code.

        Args:
            error_context: Error details including type, location, message
            code_context: Surrounding code context
            prompt: Specific fix instructions

        Returns:
            None - modifies file in place
        """
        pass

    @abstractmethod
    def validate_response(self, response: str) -> bool:
        """Validate AI response before applying.

        Args:
            response: AI-generated response to validate

        Returns:
            True if response is valid, False otherwise
        """
        pass

    def get_agent_info(self) -> AgentInfo:
        """Get agent metadata and capabilities.

        Returns:
            Agent information and capabilities
        """
        return self._agent_info

    def can_handle_error_type(self, error_type: str) -> bool:
        """Check if agent can handle specific error type.

        Args:
            error_type: Type of error to check

        Returns:
            True if agent can handle this error type
        """
        capabilities = self._agent_info.capabilities

        if error_type in ["linting", "ruff", "flake8", "pylint"]:
            return capabilities.can_fix_linting
        elif error_type in ["type", "mypy", "typing"]:
            return capabilities.can_fix_types
        elif error_type in ["test", "pytest", "unittest"]:
            return capabilities.can_fix_tests

        return False

    def can_handle_language(self, language: str) -> bool:
        """Check if agent supports specific programming language.

        Args:
            language: Programming language to check

        Returns:
            True if agent supports this language
        """
        return language.lower() in [
            lang.lower() for lang in self._agent_info.capabilities.supported_languages
        ]

    def get_max_context_length(self) -> int:
        """Get maximum context length for this agent.

        Returns:
            Maximum context length in tokens
        """
        return self._agent_info.capabilities.max_context_length

    def __str__(self) -> str:
        """String representation of agent."""
        return f"{self._agent_info.name} v{self._agent_info.version}"

    def __repr__(self) -> str:
        """Detailed string representation of agent."""
        return (
            f"{self.__class__.__name__}("
            f"name='{self._agent_info.name}', "
            f"version='{self._agent_info.version}', "
            f"capabilities={self._agent_info.capabilities.model_dump()}"
            f")"
        )
