"""
Test: Multi-Agent System im RAG-Evaluation-Modus

Verifiziert dass das Multi-Agent-System korrekt nur den Wissens-Agenten
mit RAG-Tool lädt, wenn andere Tools deaktiviert sind.
"""

import sys
from pathlib import Path
import importlib

# Projekt-Root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_multi_agent_rag_only_mode():
    """Test: Multi-Agent im RAG-Only Modus lädt nur Wissens-Agent mit RAG-Tool."""
    
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
        settings_module.Settings.ENABLE_KLIPS = False
        settings_module.Settings.ENABLE_DUCKDUCKGO = False
        settings_module.Settings.ENABLE_WEB_SCRAPER = False
        settings_module.Settings.ENABLE_EMAIL = False
        
        # Also modify the settings instance
        settings_module.settings.ENABLE_KLIPS = False
        settings_module.settings.ENABLE_DUCKDUCKGO = False
        settings_module.settings.ENABLE_WEB_SCRAPER = False
        settings_module.settings.ENABLE_EMAIL = False
        
        # Force reload of multi-agent modules to pick up new settings
        modules_to_reload = [
            'src.agent.multi.multi_agent_system',
            'src.agent.multi.orchestrator',
            'src.agent.multi.knowledge_agent',
            'src.agent.multi.klips_agent',
            'src.agent.multi.email_agent',
        ]
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                del sys.modules[module_name]
        
        # NOW import the agent (with settings already modified)
        from src.agent.multi.multi_agent_system import MultiAgentSystem
        agent = MultiAgentSystem(force_llm_routing=True)
        
        # 1. Prüfe dass nur Wissens-Agent geladen wurde
        available_agents = agent.get_available_agents()
        print(f"\n✅ Verfügbare Agenten: {available_agents}")
        assert len(available_agents) == 1, f"Erwartet: 1 Agent, Gefunden: {len(available_agents)}"
        assert "Wissens-Agent" in available_agents, "Wissens-Agent fehlt"
        
        # 2. Prüfe dass nur RAG-Tool geladen wurde
        available_tools = agent.get_available_tools()
        print(f"✅ Verfügbare Tools: {available_tools}")
        assert len(available_tools) == 1, f"Erwartet: 1 Tool (RAG), Gefunden: {len(available_tools)}"
        assert any("university" in tool.lower() or "rag" in tool.lower() for tool in available_tools), \
            "RAG-Tool fehlt"
        
        # 3. Prüfe dass keine anderen Tools geladen wurden
        forbidden_tools = ["klips", "duckduckgo", "email", "scraper", "camunda"]
        for forbidden in forbidden_tools:
            assert not any(forbidden in tool.lower() for tool in available_tools), \
                f"Tool '{forbidden}' sollte nicht geladen sein"
        
        # 4. Prüfe System-Prompt des Wissens-Agenten
        knowledge_agent = agent.orchestrator.agents["Wissens-Agent"]
        system_prompt = knowledge_agent._get_system_prompt()
        print(f"\n📝 System-Prompt Länge: {len(system_prompt)} Zeichen")
        
        # Verifiziere dass deaktivierte Tools NICHT im Prompt erwähnt werden
        assert "duckduckgo_search" not in system_prompt.lower(), \
            "DuckDuckGo sollte nicht im System-Prompt erwähnt werden"
        assert "web_scraper" not in system_prompt.lower(), \
            "Web-Scraper sollte nicht im System-Prompt erwähnt werden"
        
        # Verifiziere dass RAG-Tool IM Prompt erwähnt wird
        assert "university_knowledge_search" in system_prompt.lower(), \
            "RAG-Tool sollte im System-Prompt erwähnt werden"
        
        print("✅ System-Prompt erwähnt nur verfügbare Tools")
        print("\n✅ Alle Tests bestanden: Multi-Agent respektiert RAG-Only Modus")
        
    finally:
        # Restore original settings
        settings_module.Settings.ENABLE_KLIPS = original_klips
        settings_module.Settings.ENABLE_DUCKDUCKGO = original_duckduckgo
        settings_module.Settings.ENABLE_WEB_SCRAPER = original_web_scraper
        settings_module.Settings.ENABLE_EMAIL = original_email
        
        settings_module.settings.ENABLE_KLIPS = original_klips
        settings_module.settings.ENABLE_DUCKDUCKGO = original_duckduckgo
        settings_module.settings.ENABLE_WEB_SCRAPER = original_web_scraper
        settings_module.settings.ENABLE_EMAIL = original_email


if __name__ == "__main__":
    test_multi_agent_rag_only_mode()
