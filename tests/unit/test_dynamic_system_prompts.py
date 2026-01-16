"""
Unit Tests für dynamische System-Prompt-Generierung.

Testet, dass System-Prompts korrekt an verfügbare Tools angepasst werden.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config import settings


class TestSystemPromptDynamicGeneration:
    """
    Tests für dynamische System-Prompt-Generierung.
    
    Diese Tests verifizieren, dass die System-Prompts nur Tools erwähnen,
    die tatsächlich geladen wurden - unabhängig von den Settings.
    """
    
    def test_react_agent_prompt_matches_loaded_tools(self):
        """Test: ReactAgent Prompt erwähnt nur tatsächlich geladene Tools."""
        from src.agent.react_agent import ReactAgent
        
        agent = ReactAgent()
        loaded_tool_names = {tool.name for tool in agent.tools}
        prompt = agent.system_message.content
        
        print(f"\n📋 Geladene Tools: {loaded_tool_names}")
        
        # Für jedes geladene Tool: Prüfe ob im Prompt erwähnt
        for tool_name in loaded_tool_names:
            # Einige Tools sind unter verschiedenen Namen im Prompt
            if tool_name == "university_knowledge_search":
                assert tool_name in prompt or "Universitäts-RAG" in prompt, \
                    f"Tool {tool_name} geladen aber nicht im Prompt erwähnt"
            elif tool_name.startswith("klips2_"):
                # KLIPS-Tools können auch als "KLIPS2-Aktionen" erwähnt werden
                assert tool_name in prompt or "KLIPS2-Aktionen" in prompt or "klips2_" in prompt.lower(), \
                    f"Tool {tool_name} geladen aber nicht im Prompt erwähnt"
            else:
                assert tool_name in prompt, \
                    f"Tool {tool_name} geladen aber nicht im Prompt erwähnt"
        
        print("✅ ReactAgent: Alle geladenen Tools im Prompt erwähnt")
        
        # Liste der möglichen Tools
        all_possible_tools = {
            "duckduckgo_search", "web_scraper", "send_email",
            "klips2_register", "klips2_apply_study", "klips2_change_password",
            "klips2_change_address", "klips2_get_course_details"
        }
        
        # Für jedes NICHT geladene Tool: Prüfe ob NICHT im Prompt erwähnt
        unloaded_tools = all_possible_tools - loaded_tool_names
        for tool_name in unloaded_tools:
            assert tool_name not in prompt, \
                f"Tool {tool_name} NICHT geladen aber im Prompt erwähnt!"
        
        print(f"✅ ReactAgent: Keine nicht-geladenen Tools im Prompt erwähnt")
    
    def test_confirmation_agent_prompt_matches_loaded_tools(self):
        """Test: ConfirmationAgent Prompt erwähnt nur tatsächlich geladene Tools."""
        from src.agent.confirmation.confirmation_agent import ConfirmationAgent
        
        agent = ConfirmationAgent()
        loaded_tool_names = {tool.name for tool in agent.tools}
        prompt = agent.system_message.content
        
        print(f"\n📋 Geladene Tools: {loaded_tool_names}")
        
        # Liste der möglichen Tools
        all_possible_tools = {
            "duckduckgo_search", "web_scraper", "send_email",
            "klips2_register", "klips2_apply_study", "klips2_change_password",
            "klips2_change_address", "klips2_get_course_details"
        }
        
        # Für jedes NICHT geladene Tool: Prüfe ob NICHT im Prompt erwähnt
        unloaded_tools = all_possible_tools - loaded_tool_names
        for tool_name in unloaded_tools:
            assert tool_name not in prompt, \
                f"Tool {tool_name} NICHT geladen aber im Prompt erwähnt!"
        
        print(f"✅ ConfirmationAgent: Keine nicht-geladenen Tools im Prompt erwähnt")
    
    def test_constrained_agent_prompt_matches_loaded_tools(self):
        """Test: ConstrainedAgent Prompt erwähnt nur tatsächlich geladene Tools."""
        from src.agent.constrained.constrained_agent import ConstrainedAgent
        
        agent = ConstrainedAgent()
        loaded_tool_names = {tool.name for tool in agent.tools}
        prompt = agent.system_message.content
        
        print(f"\n📋 Geladene Tools: {loaded_tool_names}")
        
        # Liste der möglichen Tools
        all_possible_tools = {
            "duckduckgo_search", "web_scraper", "send_email",
            "klips2_register", "klips2_apply_study", "klips2_change_password",
            "klips2_change_address", "klips2_get_course_details"
        }
        
        # Für jedes NICHT geladene Tool: Prüfe ob NICHT im Prompt erwähnt
        unloaded_tools = all_possible_tools - loaded_tool_names
        for tool_name in unloaded_tools:
            assert tool_name not in prompt, \
                f"Tool {tool_name} NICHT geladen aber im Prompt erwähnt!"
        
        print(f"✅ ConstrainedAgent: Keine nicht-geladenen Tools im Prompt erwähnt")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 DYNAMIC SYSTEM PROMPT TESTS")
    print("="*80 + "\n")
    
    # Main Test
    print("\n📝 System Prompt Dynamic Generation Tests:")
    print("-" * 80)
    test_main = TestSystemPromptDynamicGeneration()
    test_main.test_react_agent_prompt_matches_loaded_tools()
    test_main.test_confirmation_agent_prompt_matches_loaded_tools()
    test_main.test_constrained_agent_prompt_matches_loaded_tools()
    
    print("\n" + "="*80)
    print("✅ ALLE TESTS BESTANDEN!")
    print("="*80 + "\n")
