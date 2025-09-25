"""AI Agent integration for automated code quality fixing."""

from .base import AIAgent, BaseAIAgent, AgentCapabilities, AgentInfo
from .cursor_client import CursorClient
from .agent_manager import AgentManager

__all__ = [
    "AIAgent",
    "BaseAIAgent", 
    "AgentCapabilities",
    "AgentInfo",
    "CursorClient",
    "AgentManager",
]
