"""
Shared Agent Configuration.

Provides centralized configuration for all agent types,
including recursion limits, memory sizes, and LangSmith setup.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


@dataclass
class AgentConfig:
    """
    Configuration for agent instances.
    
    Provides consistent defaults and easy override capability
    for all agent types.
    """
    # Agent identification
    agent_type: str = "single"
    
    # Memory configuration
    memory_size: int = 100
    
    # Recursion limit (from settings based on agent type)
    recursion_limit: Optional[int] = None
    
    # LangSmith tracing
    enable_tracing: bool = False
    
    def __post_init__(self):
        """Set recursion limit from settings if not provided."""
        if self.recursion_limit is None:
            self.recursion_limit = settings.RECURSION_LIMITS.get(
                self.agent_type, 
                settings.DEFAULT_RECURSION_LIMIT
            )
    
    @classmethod
    def for_agent_type(cls, agent_type: str) -> "AgentConfig":
        """
        Create configuration for a specific agent type.
        
        Args:
            agent_type: One of 'single', 'multi', 'confirmation', 'constrained'
            
        Returns:
            AgentConfig instance with appropriate defaults
        """
        memory_sizes = {
            "single": 100,
            "multi": 20,  # Smaller for specialized agents
            "confirmation": 100,
            "constrained": 100,
        }
        
        return cls(
            agent_type=agent_type,
            memory_size=memory_sizes.get(agent_type, 100),
            enable_tracing=settings.LANGSMITH_TRACING,
        )


def setup_langsmith_tracing(project_name: Optional[str] = None) -> bool:
    """
    Configure LangSmith tracing if enabled in settings.
    
    Args:
        project_name: Optional project name override
        
    Returns:
        True if tracing was enabled, False otherwise
    """
    if not settings.LANGSMITH_TRACING or not settings.LANGSMITH_API_KEY:
        return False
    
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = project_name or settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    
    logger.info(f"LangSmith tracing enabled for project: {settings.LANGSMITH_PROJECT}")
    return True


def get_recursion_limit(agent_type: str) -> int:
    """
    Get recursion limit for a specific agent type.
    
    Args:
        agent_type: One of 'single', 'multi', 'confirmation', 'constrained'
        
    Returns:
        Recursion limit value
    """
    return settings.RECURSION_LIMITS.get(agent_type, settings.DEFAULT_RECURSION_LIMIT)
