"""
Safe Tool Loading Utilities for Agents.

Provides consistent tool loading with error handling and logging.
Eliminates duplicated try-except patterns across agent implementations.
"""
from typing import Callable, List, Optional, TypeVar

from langchain_core.tools import BaseTool

from config.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseTool)


def load_tool_safely(
    tool_factory: Callable[[], T],
    tool_name: str,
    fallback_message: Optional[str] = None,
    required: bool = False,
) -> Optional[T]:
    """
    Safely load a tool with consistent error handling and logging.
    
    Args:
        tool_factory: Callable that creates the tool (no arguments)
        tool_name: Human-readable name for logging
        fallback_message: Optional message to log on failure
        required: If True, raise exception on failure instead of returning None
        
    Returns:
        The loaded tool, or None if loading failed and not required
        
    Raises:
        RuntimeError: If required=True and tool loading fails
    """
    try:
        tool = tool_factory()
        logger.info(f"✓ {tool_name} loaded successfully")
        return tool
    except Exception as e:
        if required:
            logger.error(f"✗ {tool_name} failed to load (required): {e}")
            raise RuntimeError(f"Required tool {tool_name} failed to load: {e}") from e
        else:
            logger.warning(f"✗ {tool_name} could not be loaded: {e}")
            if fallback_message:
                logger.warning(f"  → {fallback_message}")
            return None


def load_tools_batch(
    tool_configs: List[dict],
) -> List[BaseTool]:
    """
    Load multiple tools with consistent error handling.
    
    Args:
        tool_configs: List of dicts with keys:
            - factory: Callable that creates the tool
            - name: Human-readable name
            - fallback_message: Optional message on failure
            - required: If True, raise on failure
            - enabled: If False, skip loading (default True)
            
    Returns:
        List of successfully loaded tools
        
    Example:
        tools = load_tools_batch([
            {"factory": create_rag_tool, "name": "RAG Tool", "required": True},
            {"factory": create_email_tool, "name": "Email Tool", "enabled": settings.ENABLE_EMAIL},
        ])
    """
    tools = []
    
    for config in tool_configs:
        enabled = config.get("enabled", True)
        if not enabled:
            logger.debug(f"⏭ {config['name']} skipped (disabled)")
            continue
        
        tool = load_tool_safely(
            tool_factory=config["factory"],
            tool_name=config["name"],
            fallback_message=config.get("fallback_message"),
            required=config.get("required", False),
        )
        
        if tool is not None:
            # Handle both single tools and lists of tools
            if isinstance(tool, list):
                tools.extend(tool)
            else:
                tools.append(tool)
    
    logger.info(f"Loaded {len(tools)} tools total")
    return tools


def load_klips_tools() -> List[BaseTool]:
    """
    Load all KLIPS2 tools with proper error handling.
    
    Returns:
        List of successfully loaded KLIPS tools
    """
    from config.settings import settings
    
    if not settings.ENABLE_KLIPS:
        logger.debug("KLIPS tools disabled in settings")
        return []
    
    tools = []
    
    # Registration tool
    try:
        from src.tools.klips import create_klips2_register_tool
        tool = create_klips2_register_tool()
        tools.append(tool)
        logger.info("✓ KLIPS2 Registration Tool loaded")
    except Exception as e:
        logger.warning(f"✗ KLIPS2 Registration Tool: {e}")
    
    # Extended KLIPS tools
    try:
        from src.tools.klips import (
            create_klips2_apply_tool,
            create_klips2_change_password_tool,
            create_klips2_get_course_details_tool,
            create_klips2_change_address_tool,
        )
        
        extended_tools = [
            (create_klips2_apply_tool, "Apply Tool"),
            (create_klips2_change_password_tool, "Password Tool"),
            (create_klips2_get_course_details_tool, "Course Details Tool"),
            (create_klips2_change_address_tool, "Address Tool"),
        ]
        
        for factory, name in extended_tools:
            try:
                tool = factory()
                tools.append(tool)
            except Exception as e:
                logger.warning(f"  ✗ KLIPS2 {name}: {e}")
        
        logger.info(f"✓ KLIPS2 Extended Tools loaded ({len(tools)-1} tools)")
    except Exception as e:
        logger.warning(f"✗ KLIPS2 Extended Tools import failed: {e}")
    
    return tools
