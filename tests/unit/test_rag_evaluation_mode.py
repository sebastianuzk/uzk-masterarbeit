"""
Unit Test für RAG-Evaluation-Modus.

Dieser Test verifiziert, dass im RAG-Evaluation-Modus keine anderen Tools
im System-Prompt erwähnt werden, wodurch das LLM nicht versucht, sie zu nutzen.
"""

import pytest
import sys
import importlib
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_constrained_agent_rag_mode_only_rag_tool():
    """
    Test: Im RAG-Evaluation-Modus sollte der Constrained Agent NUR das RAG-Tool
    in seinem System-Prompt erwähnen.
    
    Dies verhindert, dass das LLM versucht, deaktivierte Tools wie
    klips2_get_course_details zu verwenden, was zu Fehlern führt.
    """
    # Import settings FIRST, before any agent imports  
    import config.settings
    settings_module = config.settings
    
    # Save original settings
    original_duckduckgo = settings_module.Settings.ENABLE_DUCKDUCKGO
    original_web_scraper = settings_module.Settings.ENABLE_WEB_SCRAPER
    original_email = settings_module.Settings.ENABLE_EMAIL
    original_klips = settings_module.Settings.ENABLE_KLIPS
    
    try:
        # Modify CLASS variables (not instance variables)
        settings_module.Settings.ENABLE_DUCKDUCKGO = False
        settings_module.Settings.ENABLE_WEB_SCRAPER = False
        settings_module.Settings.ENABLE_EMAIL = False
        settings_module.Settings.ENABLE_KLIPS = False
        
        # Also modify the instance
        settings_module.settings.ENABLE_DUCKDUCKGO = False
        settings_module.settings.ENABLE_WEB_SCRAPER = False
        settings_module.settings.ENABLE_EMAIL = False
        settings_module.settings.ENABLE_KLIPS = False
        
        # Force reload of constrained_agent module to pick up new settings
        if 'src.agent.constrained.constrained_agent' in sys.modules:
            del sys.modules['src.agent.constrained.constrained_agent']
        
        # NOW import the agent (with settings already modified)
        from src.agent.constrained.constrained_agent import ConstrainedAgent
        
        # Create agent
        agent = ConstrainedAgent()
        
        # Verify only RAG tool is loaded
        loaded_tool_names = {tool.name for tool in agent.tools}
        print(f"\n📋 Loaded tools: {loaded_tool_names}")
        
        assert "university_knowledge_search" in loaded_tool_names, \
            "RAG tool should be loaded"
        
        # Verify KLIPS tools are NOT loaded
        klips_tools = [
            "klips2_register", "klips2_apply_study", "klips2_change_password",
            "klips2_change_address", "klips2_get_course_details"
        ]
        for klips_tool in klips_tools:
            assert klips_tool not in loaded_tool_names, \
                f"KLIPS tool {klips_tool} should NOT be loaded in RAG mode"
        
        # Verify other tools are NOT loaded
        assert "duckduckgo_search" not in loaded_tool_names, \
            "DuckDuckGo should NOT be loaded in RAG mode"
        assert "web_scraper" not in loaded_tool_names, \
            "Web scraper should NOT be loaded in RAG mode"
        assert "send_email" not in loaded_tool_names, \
            "Email tool should NOT be loaded in RAG mode"
        
        # Check system prompt
        system_prompt = agent.system_message.content
        print(f"\n📝 System prompt length: {len(system_prompt)} chars")
        
        # Verify KLIPS tools are NOT mentioned in system prompt
        for klips_tool in klips_tools:
            assert klips_tool not in system_prompt, \
                f"KLIPS tool {klips_tool} should NOT be mentioned in system prompt in RAG mode"
        
        # Verify other tools are NOT mentioned
        assert "duckduckgo_search" not in system_prompt, \
            "DuckDuckGo should NOT be mentioned in system prompt in RAG mode"
        assert "send_email" not in system_prompt, \
            "Email tool should NOT be mentioned in system prompt in RAG mode"
        
        # Verify RAG tool IS mentioned
        assert "university_knowledge_search" in system_prompt or "RAG" in system_prompt or "Uni-Wissen" in system_prompt, \
            "RAG tool should be mentioned in system prompt"
        
        # Check decision prompt
        decision_prompt = agent._get_decision_prompt()
        print(f"\n📝 Decision prompt length: {len(decision_prompt)} chars")
        
        # Verify KLIPS tools are NOT mentioned in decision prompt
        for klips_tool in klips_tools:
            assert klips_tool not in decision_prompt, \
                f"KLIPS tool {klips_tool} should NOT be mentioned in decision prompt in RAG mode"
        
        # Verify other tools are NOT mentioned
        assert "duckduckgo_search" not in decision_prompt, \
            "DuckDuckGo should NOT be mentioned in decision prompt in RAG mode"
        assert "send_email" not in decision_prompt, \
            "Email tool should NOT be mentioned in decision prompt in RAG mode"
        
        # Verify RAG tool IS mentioned
        assert "university_knowledge_search" in decision_prompt, \
            "RAG tool should be mentioned in decision prompt"
        
        print("\n✅ SUCCESS: RAG evaluation mode correctly excludes disabled tools from prompts")
        
    finally:
        # Restore original settings
        settings_module.Settings.ENABLE_DUCKDUCKGO = original_duckduckgo
        settings_module.Settings.ENABLE_WEB_SCRAPER = original_web_scraper
        settings_module.Settings.ENABLE_EMAIL = original_email
        settings_module.Settings.ENABLE_KLIPS = original_klips
        
        settings_module.settings.ENABLE_DUCKDUCKGO = original_duckduckgo
        settings_module.settings.ENABLE_WEB_SCRAPER = original_web_scraper
        settings_module.settings.ENABLE_EMAIL = original_email
        settings_module.settings.ENABLE_KLIPS = original_klips


if __name__ == "__main__":
    test_constrained_agent_rag_mode_only_rag_tool()
