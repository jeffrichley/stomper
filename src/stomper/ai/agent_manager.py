"""Agent manager for AI agent selection and fallback strategies."""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .base import AIAgent, AgentInfo, AgentCapabilities


logger = logging.getLogger(__name__)


class AgentManager:
    """Manager for AI agent selection, fallback, and coordination."""
    
    def __init__(self):
        """Initialize agent manager."""
        self._agents: Dict[str, AIAgent] = {}
        self._fallback_order: List[str] = []
        self._default_agent: Optional[str] = None
    
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
    
    def get_available_agents(self) -> List[str]:
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
    
    def get_default_agent(self) -> Optional[AIAgent]:
        """Get default agent.
        
        Returns:
            Default agent or None if not set
        """
        if self._default_agent and self._default_agent in self._agents:
            return self._agents[self._default_agent]
        return None
    
    def set_fallback_order(self, agent_names: List[str]) -> None:
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
    
    def get_agents_by_capability(self, capability: str) -> List[AIAgent]:
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
            
            if hasattr(capabilities, capability):
                if getattr(capabilities, capability):
                    capable_agents.append(agent)
        
        return capable_agents
    
    def get_best_agent_for_error(self, error_type: str, language: str = "python") -> Optional[AIAgent]:
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
        self,
        primary_agent_name: str,
        error_context: Dict[str, Any],
        code_context: str,
        prompt: str
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
    
    def validate_fix_with_fallback(
        self,
        primary_agent_name: str,
        response: str
    ) -> bool:
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
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered agents.
        
        Returns:
            Dictionary with agent statistics
        """
        stats = {
            "total_agents": len(self._agents),
            "default_agent": self._default_agent,
            "fallback_order": self._fallback_order.copy(),
            "agents": {}
        }
        
        for name, agent in self._agents.items():
            agent_info = agent.get_agent_info()
            stats["agents"][name] = {
                "name": agent_info.name,
                "version": agent_info.version,
                "description": agent_info.description,
                "capabilities": agent_info.capabilities.model_dump()
            }
        
        return stats
    
    def clear_all_agents(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
        self._fallback_order.clear()
        self._default_agent = None
        logger.info("Cleared all agents")
