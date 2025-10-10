"""Agent manager for AI agent selection and fallback strategies."""

import logging
from pathlib import Path
from typing import Any

from .base import AIAgent

logger = logging.getLogger(__name__)


class AgentManager:
    """Manager for AI agent selection, fallback, and coordination."""

    def __init__(
        self,
        project_root: Path | None = None,
        mapper: Any | None = None,
    ):
        """Initialize agent manager.

        Args:
            project_root: Main project root (for mapper initialization)
            mapper: Error mapper instance (optional, created if not provided)
        """
        self._agents: dict[str, AIAgent] = {}
        self._fallback_order: list[str] = []
        self._default_agent: str | None = None

        # Create mapper if not provided (requires project_root)
        if mapper is None:
            if project_root is not None:
                # Import here to avoid circular dependency
                from stomper.ai.mapper import ErrorMapper

                self.mapper = ErrorMapper(project_root=project_root)
                logger.info("AgentManager initialized with adaptive learning")
            else:
                # No mapper - backwards compatibility mode
                self.mapper = None
                logger.debug("AgentManager initialized without adaptive learning")
        else:
            self.mapper = mapper
            logger.info("AgentManager initialized with provided mapper")

    def register_agent(self, name: str, agent: AIAgent) -> None:
        """Register an AI agent.

        Args:
            name: Agent name/identifier
            agent: AI agent implementing AIAgent protocol
        """
        if not isinstance(agent, AIAgent):
            raise TypeError("Agent must implement AIAgent protocol")

        self._agents[name] = agent
        logger.info(f"Registered agent: {name}")

    def unregister_agent(self, name: str) -> None:
        """Unregister an AI agent.

        Args:
            name: Agent name to unregister
        """
        if name in self._agents:
            del self._agents[name]
            if name in self._fallback_order:
                self._fallback_order.remove(name)
            if self._default_agent == name:
                self._default_agent = None
            logger.info(f"Unregistered agent: {name}")

    def get_agent(self, name: str) -> AIAgent:
        """Get agent by name.

        Args:
            name: Agent name

        Returns:
            AI agent

        Raises:
            ValueError: If agent not found
        """
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found")
        return self._agents[name]

    def get_available_agents(self) -> list[str]:
        """Get list of available agent names.

        Returns:
            List of agent names
        """
        return list(self._agents.keys())

    def set_default_agent(self, name: str) -> None:
        """Set default agent.

        Args:
            name: Agent name to set as default

        Raises:
            ValueError: If agent not found
        """
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found")
        self._default_agent = name
        logger.info(f"Set default agent: {name}")

    def get_default_agent(self) -> AIAgent | None:
        """Get default agent.

        Returns:
            Default agent or None if not set
        """
        if self._default_agent and self._default_agent in self._agents:
            return self._agents[self._default_agent]
        return None

    def set_fallback_order(self, agent_names: list[str]) -> None:
        """Set fallback order for agents.

        Args:
            agent_names: List of agent names in fallback order
        """
        # Validate all agents exist
        for name in agent_names:
            if name not in self._agents:
                raise ValueError(f"Agent '{name}' not found")

        self._fallback_order = agent_names.copy()
        logger.info(f"Set fallback order: {agent_names}")

    def get_agents_by_capability(self, capability: str) -> list[AIAgent]:
        """Get agents that have specific capability.

        Args:
            capability: Capability to check (e.g., 'can_fix_linting')

        Returns:
            List of agents with the capability
        """
        capable_agents = []

        for agent in self._agents.values():
            agent_info = agent.get_agent_info()
            capabilities = agent_info.capabilities

            if hasattr(capabilities, capability) and getattr(capabilities, capability):
                capable_agents.append(agent)

        return capable_agents

    def get_best_agent_for_error(self, error_type: str, language: str = "python") -> AIAgent | None:
        """Get best agent for specific error type and language.

        Args:
            error_type: Type of error (linting, type, test, etc.)
            language: Programming language

        Returns:
            Best agent for the error type, or None if none available
        """
        # First, try to find agents that can handle this specific error type
        capable_agents = []

        for agent in self._agents.values():
            agent_info = agent.get_agent_info()
            capabilities = agent_info.capabilities

            # Check if agent can handle this error type
            can_handle = False
            if error_type in ["linting", "ruff", "flake8", "pylint"]:
                can_handle = capabilities.can_fix_linting
            elif error_type in ["type", "mypy", "typing"]:
                can_handle = capabilities.can_fix_types
            elif error_type in ["test", "pytest", "unittest"]:
                can_handle = capabilities.can_fix_tests

            # Check if agent supports the language
            if can_handle and language.lower() in [
                lang.lower() for lang in capabilities.supported_languages
            ]:
                capable_agents.append(agent)

        if not capable_agents:
            return None

        # Return the first capable agent (could be enhanced with scoring)
        return capable_agents[0]

    def generate_fix_with_fallback(
        self, primary_agent_name: str, error_context: dict[str, Any], code_context: str, prompt: str
    ) -> str:
        """Generate fix with fallback strategy.

        Args:
            primary_agent_name: Name of primary agent to try
            error_context: Error context
            code_context: Code context
            prompt: Fix prompt

        Returns:
            Generated fix from successful agent

        Raises:
            RuntimeError: If all agents fail
        """
        # Try primary agent first
        if primary_agent_name in self._agents:
            try:
                agent = self._agents[primary_agent_name]
                logger.info(f"Trying primary agent: {primary_agent_name}")
                return agent.generate_fix(error_context, code_context, prompt)
            except Exception as e:
                logger.warning(f"Primary agent {primary_agent_name} failed: {e}")

        # Try fallback agents
        for agent_name in self._fallback_order:
            if agent_name == primary_agent_name:
                continue  # Skip primary agent

            if agent_name in self._agents:
                try:
                    agent = self._agents[agent_name]
                    logger.info(f"Trying fallback agent: {agent_name}")
                    return agent.generate_fix(error_context, code_context, prompt)
                except Exception as e:
                    logger.warning(f"Fallback agent {agent_name} failed: {e}")

        # If all agents failed, raise error
        raise RuntimeError("All agents failed to generate fix")

    def validate_fix_with_fallback(self, primary_agent_name: str, response: str) -> bool:
        """Validate fix with fallback strategy.

        Args:
            primary_agent_name: Name of primary agent to try
            response: Response to validate

        Returns:
            True if any agent validates the response
        """
        # Try primary agent first
        if primary_agent_name in self._agents:
            try:
                agent = self._agents[primary_agent_name]
                if agent.validate_response(response):
                    return True
            except Exception as e:
                logger.warning(f"Primary agent {primary_agent_name} validation failed: {e}")

        # Try fallback agents
        for agent_name in self._fallback_order:
            if agent_name == primary_agent_name:
                continue  # Skip primary agent

            if agent_name in self._agents:
                try:
                    agent = self._agents[agent_name]
                    if agent.validate_response(response):
                        return True
                except Exception as e:
                    logger.warning(f"Fallback agent {agent_name} validation failed: {e}")

        return False

    def get_agent_statistics(self) -> dict[str, Any]:
        """Get statistics about registered agents.

        Returns:
            Dictionary with agent statistics
        """
        stats: dict[str, Any] = {
            "total_agents": len(self._agents),
            "default_agent": self._default_agent,
            "fallback_order": self._fallback_order.copy(),
            "agents": {},
        }

        for name, agent in self._agents.items():
            agent_info = agent.get_agent_info()
            stats["agents"][name] = {
                "name": agent_info.name,
                "version": agent_info.version,
                "description": agent_info.description,
                "capabilities": agent_info.capabilities.model_dump(),
            }

        return stats

    def generate_fix_with_intelligent_fallback(
        self,
        primary_agent_name: str,
        error: Any,
        error_context: dict[str, Any],
        code_context: str,
        prompt: str,
        max_retries: int = 3,
    ) -> None:
        """Generate fix with intelligent fallback based on error history.

        Args:
            primary_agent_name: Name of primary agent to try
            error: Quality error being fixed
            error_context: Error context
            code_context: Code context
            prompt: Fix prompt
            max_retries: Maximum retry attempts

        Returns:
            None - agent modifies file in place

        Raises:
            RuntimeError: If all retries exhausted
        """
        # Fallback to simple mode if no mapper
        if not self.mapper:
            logger.warning("No mapper available, using simple fallback")
            return self.generate_fix_with_fallback(
                primary_agent_name,
                error_context,
                code_context,
                prompt,
            )

        # Import here to avoid circular dependency
        from stomper.ai.models import FixOutcome

        failed_strategies = []

        for retry_count in range(max_retries):
            # Get adaptive strategy from mapper
            adaptive_strategy = self.mapper.get_adaptive_strategy(
                error,
                retry_count=retry_count,
            )

            # Try to get fallback strategy if we've failed
            if retry_count > 0:
                fallback_strategy = self.mapper.get_fallback_strategy(
                    error,
                    failed_strategies,
                )

                if fallback_strategy is None:
                    logger.warning("All fallback strategies exhausted")
                    break

                logger.info(f"🔄 Retry #{retry_count}: Using fallback strategy {fallback_strategy.value}")

            # Try to generate fix
            try:
                if primary_agent_name not in self._agents:
                    raise ValueError(f"Agent '{primary_agent_name}' not found")

                agent = self._agents[primary_agent_name]
                logger.info(
                    f"🤖 Attempting fix with {primary_agent_name} "
                    f"(strategy: {adaptive_strategy.verbosity.value}, retry: {retry_count})"
                )

                # Agent modifies file in place, no return value
                agent.generate_fix(error_context, code_context, prompt)

                # ✅ Record success
                self.mapper.record_attempt(
                    error,
                    FixOutcome.SUCCESS,
                    adaptive_strategy.verbosity,
                )

                logger.info(f"✅ Fix successful with {adaptive_strategy.verbosity.value} strategy!")
                return  # Success - file modified in place

            except Exception as e:
                logger.warning(f"❌ Attempt {retry_count + 1} failed with {primary_agent_name}: {e}")

                # Record failure
                self.mapper.record_attempt(
                    error,
                    FixOutcome.FAILURE,
                    adaptive_strategy.verbosity,
                )

                failed_strategies.append(adaptive_strategy.verbosity)

        # All retries exhausted
        raise RuntimeError(f"All {max_retries} retry attempts failed for {error.code}")

    def clear_all_agents(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
        self._fallback_order.clear()
        self._default_agent = None
        logger.info("Cleared all agents")
