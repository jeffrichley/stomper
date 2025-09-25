"""Tests for AI Agent Protocol."""

import pytest
from typing import Dict, Any
from pathlib import Path
from unittest.mock import Mock, patch

from stomper.ai.base import AIAgent, BaseAIAgent, AgentCapabilities, AgentInfo
from stomper.ai.cursor_client import CursorClient
from stomper.ai.agent_manager import AgentManager


class TestAIAgent:
    """Test AIAgent protocol compliance."""

    def test_ai_agent_protocol_interface(self):
        """Test that AIAgent protocol defines required methods."""
        # Check that protocol has required abstract methods
        assert hasattr(AIAgent, 'generate_fix')
        assert hasattr(AIAgent, 'validate_response')
        assert hasattr(AIAgent, 'get_agent_info')

    def test_ai_agent_protocol_method_signatures(self):
        """Test that protocol methods have correct signatures."""
        # Mock agent that implements the protocol
        class MockAgent:
            def generate_fix(self, error_context: Dict[str, Any], code_context: str, prompt: str) -> str:
                return "mock fix"
            
            def validate_response(self, response: str) -> bool:
                return True
            
            def get_agent_info(self) -> Dict[str, str]:
                return {"name": "mock", "version": "1.0.0"}
        
        agent = MockAgent()
        
        # Test method calls work with correct signatures
        result = agent.generate_fix({}, "code", "prompt")
        assert result == "mock fix"
        
        assert agent.validate_response("test") is True
        
        info = agent.get_agent_info()
        assert info["name"] == "mock"


class TestAgentCapabilities:
    """Test AgentCapabilities model."""

    def test_agent_capabilities_creation(self):
        """Test creating AgentCapabilities."""
        caps = AgentCapabilities(
            can_fix_linting=True,
            can_fix_types=True,
            can_fix_tests=False,
            max_context_length=4000,
            supported_languages=["python"]
        )
        
        assert caps.can_fix_linting is True
        assert caps.can_fix_types is True
        assert caps.can_fix_tests is False
        assert caps.max_context_length == 4000
        assert caps.supported_languages == ["python"]

    def test_agent_capabilities_validation(self):
        """Test AgentCapabilities validation."""
        # Test valid capabilities
        caps = AgentCapabilities(
            can_fix_linting=True,
            can_fix_types=True,
            can_fix_tests=True,
            max_context_length=8000,
            supported_languages=["python", "javascript"]
        )
        assert caps.max_context_length == 8000
        
        # Test invalid max_context_length
        with pytest.raises(ValueError):
            AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=True,
                can_fix_tests=False,
                max_context_length=0,  # Invalid
                supported_languages=["python"]
            )


class TestAgentInfo:
    """Test AgentInfo model."""

    def test_agent_info_creation(self):
        """Test creating AgentInfo."""
        info = AgentInfo(
            name="cursor-cli",
            version="1.0.0",
            description="Cursor CLI AI agent",
            capabilities=AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=True,
                can_fix_tests=False,
                max_context_length=4000,
                supported_languages=["python"]
            )
        )
        
        assert info.name == "cursor-cli"
        assert info.version == "1.0.0"
        assert info.description == "Cursor CLI AI agent"
        assert info.capabilities.can_fix_linting is True

    def test_agent_info_serialization(self):
        """Test AgentInfo serialization."""
        info = AgentInfo(
            name="test-agent",
            version="1.0.0",
            description="Test agent",
            capabilities=AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=False,
                can_fix_tests=False,
                max_context_length=2000,
                supported_languages=["python"]
            )
        )
        
        # Test dict conversion
        info_dict = info.model_dump()
        assert info_dict["name"] == "test-agent"
        assert info_dict["capabilities"]["can_fix_linting"] is True


class TestBaseAIAgent:
    """Test BaseAIAgent abstract class."""

    def test_base_ai_agent_abstract(self):
        """Test that BaseAIAgent is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseAIAgent()

    def test_base_ai_agent_implementation(self):
        """Test concrete implementation of BaseAIAgent."""
        class ConcreteAgent(BaseAIAgent):
            def __init__(self):
                self._info = AgentInfo(
                    name="concrete",
                    version="1.0.0",
                    description="Concrete agent",
                    capabilities=AgentCapabilities(
                        can_fix_linting=True,
                        can_fix_types=True,
                        can_fix_tests=False,
                        max_context_length=4000,
                        supported_languages=["python"]
                    )
                )
            
            def generate_fix(self, error_context: Dict[str, Any], code_context: str, prompt: str) -> str:
                return f"Fix for {error_context.get('error_type', 'unknown')}"
            
            def validate_response(self, response: str) -> bool:
                return len(response) > 0 and "fix" in response.lower()
            
            def get_agent_info(self) -> AgentInfo:
                return self._info
        
        agent = ConcreteAgent()
        
        # Test methods work
        fix = agent.generate_fix({"error_type": "linting"}, "code", "prompt")
        assert "linting" in fix
        
        assert agent.validate_response("This is a fix") is True
        assert agent.validate_response("") is False
        
        info = agent.get_agent_info()
        assert info.name == "concrete"


class TestAgentManager:
    """Test AgentManager for agent selection and fallback."""

    def test_agent_manager_creation(self):
        """Test creating AgentManager."""
        manager = AgentManager()
        assert manager is not None

    def test_agent_manager_register_agent(self):
        """Test registering agents with AgentManager."""
        manager = AgentManager()
        
        # Mock agent
        mock_agent = Mock(spec=AIAgent)
        mock_agent.get_agent_info.return_value = AgentInfo(
            name="mock-agent",
            version="1.0.0",
            description="Mock agent",
            capabilities=AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=True,
                can_fix_tests=False,
                max_context_length=4000,
                supported_languages=["python"]
            )
        )
        
        manager.register_agent("mock-agent", mock_agent)
        assert "mock-agent" in manager._agents

    def test_agent_manager_get_agent(self):
        """Test getting agent from AgentManager."""
        manager = AgentManager()
        
        # Mock agent
        mock_agent = Mock(spec=AIAgent)
        mock_agent.get_agent_info.return_value = AgentInfo(
            name="test-agent",
            version="1.0.0",
            description="Test agent",
            capabilities=AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=True,
                can_fix_tests=False,
                max_context_length=4000,
                supported_languages=["python"]
            )
        )
        
        manager.register_agent("test-agent", mock_agent)
        
        # Test getting agent
        agent = manager.get_agent("test-agent")
        assert agent == mock_agent
        
        # Test getting non-existent agent
        with pytest.raises(ValueError):
            manager.get_agent("non-existent")

    def test_agent_manager_fallback_strategy(self):
        """Test agent fallback strategy."""
        manager = AgentManager()
        
        # Register multiple agents
        agent1 = Mock(spec=AIAgent)
        agent1.get_agent_info.return_value = AgentInfo(
            name="agent1",
            version="1.0.0",
            description="Primary agent",
            capabilities=AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=True,
                can_fix_tests=False,
                max_context_length=4000,
                supported_languages=["python"]
            )
        )
        
        agent2 = Mock(spec=AIAgent)
        agent2.get_agent_info.return_value = AgentInfo(
            name="agent2",
            version="1.0.0",
            description="Fallback agent",
            capabilities=AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=False,
                can_fix_tests=False,
                max_context_length=2000,
                supported_languages=["python"]
            )
        )
        
        manager.register_agent("agent1", agent1)
        manager.register_agent("agent2", agent2)
        
        # Set fallback order
        manager.set_fallback_order(["agent1", "agent2"])
        
        # Test fallback when primary agent fails
        agent1.generate_fix.side_effect = Exception("Agent failed")
        agent2.generate_fix.return_value = "fallback fix"
        
        # Test fallback logic
        result = manager.generate_fix_with_fallback(
            "agent1",
            {"error_type": "linting"},
            "code",
            "prompt"
        )
        assert result == "fallback fix"

    def test_agent_manager_capability_matching(self):
        """Test agent capability matching."""
        manager = AgentManager()
        
        # Agent that can fix linting
        linting_agent = Mock(spec=AIAgent)
        linting_agent.get_agent_info.return_value = AgentInfo(
            name="linting-agent",
            version="1.0.0",
            description="Linting agent",
            capabilities=AgentCapabilities(
                can_fix_linting=True,
                can_fix_types=False,
                can_fix_tests=False,
                max_context_length=4000,
                supported_languages=["python"]
            )
        )
        
        # Agent that can fix types
        type_agent = Mock(spec=AIAgent)
        type_agent.get_agent_info.return_value = AgentInfo(
            name="type-agent",
            version="1.0.0",
            description="Type agent",
            capabilities=AgentCapabilities(
                can_fix_linting=False,
                can_fix_types=True,
                can_fix_tests=False,
                max_context_length=4000,
                supported_languages=["python"]
            )
        )
        
        manager.register_agent("linting-agent", linting_agent)
        manager.register_agent("type-agent", type_agent)
        
        # Test capability matching
        linting_agents = manager.get_agents_by_capability("can_fix_linting")
        assert len(linting_agents) == 1
        assert linting_agents[0].get_agent_info().name == "linting-agent"
        
        type_agents = manager.get_agents_by_capability("can_fix_types")
        assert len(type_agents) == 1
        assert type_agents[0].get_agent_info().name == "type-agent"
