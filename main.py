#!/usr/bin/env python3
"""
Haupteinstiegspunkt für den Autonomen Chatbot-Agenten.

Unterstützt zwei Agent-Modi:
- Single-Agent: Ursprünglicher ReactAgent mit allen Tools
- Multi-Agent: Orchestriertes System mit spezialisierten Agenten

Verwendung:
    # Single-Agent Modus (Standard)
    python main.py
    python main.py --agent-mode single
    
    # Multi-Agent Modus
    python main.py --agent-mode multi
    
    # Streamlit UI starten
    python main.py --ui
    python main.py --ui --agent-mode multi
"""

import argparse
import sys
from pathlib import Path

# Projekt-Root zum Pfad hinzufügen
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def parse_arguments():
    """Parse Kommandozeilenargumente."""
    parser = argparse.ArgumentParser(
        description="Autonomer Chatbot-Agent für KLIPS 2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
    python main.py                        # CLI mit Single-Agent
    python main.py --agent-mode multi     # CLI mit Multi-Agent
    python main.py --ui                   # Streamlit UI mit Single-Agent
    python main.py --ui --agent-mode multi  # Streamlit UI mit Multi-Agent
        """
    )
    
    parser.add_argument(
        "--agent-mode",
        type=str,
        choices=["single", "multi"],
        default="single",
        help="Agent-Modus: 'single' für ReactAgent, 'multi' für Multi-Agent-System (default: single)"
    )
    
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Starte Streamlit Web-Interface statt CLI"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Aktiviere Debug-Ausgaben"
    )
    
    return parser.parse_args()


def run_cli(agent_mode: str, debug: bool = False):
    """
    Starte den Agenten im CLI-Modus.
    
    Args:
        agent_mode: "single" oder "multi"
        debug: Aktiviere Debug-Ausgaben
    """
    from src.agent import create_agent
    
    print("=" * 60)
    print("🤖 Autonomer Chatbot-Agent für KLIPS 2.0")
    print("=" * 60)
    print()
    
    # Agent erstellen
    print(f"Initialisiere Agent im {agent_mode.upper()}-Modus...")
    agent = create_agent(mode=agent_mode)
    print()
    
    # Verfügbare Tools anzeigen
    print("📦 Verfügbare Tools:")
    for tool in agent.get_available_tools():
        print(f"   • {tool}")
    print()
    
    # Multi-Agent: Verfügbare Agenten anzeigen
    if agent_mode == "multi" and hasattr(agent, 'get_available_agents'):
        print("🎭 Verfügbare Agenten:")
        for agent_name in agent.get_available_agents():
            print(f"   • {agent_name}")
        print()
    
    print("=" * 60)
    print("Geben Sie Ihre Frage ein (oder 'quit'/'exit' zum Beenden)")
    print("Geben Sie 'clear' ein, um den Chatverlauf zu löschen")
    print("=" * 60)
    print()
    
    # Chat-Loop
    while True:
        try:
            user_input = input("👤 Sie: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Auf Wiedersehen!")
                break
            
            if user_input.lower() == "clear":
                agent.clear_memory()
                print("🗑️ Chatverlauf gelöscht.\n")
                continue
            
            if user_input.lower() == "status":
                memory_info = agent.get_memory_summary()
                print(f"\n📊 Status:")
                print(f"   Nachrichten: {memory_info['total_messages']}")
                print(f"   Benutzer: {memory_info['human_messages']}")
                print(f"   AI: {memory_info['ai_messages']}\n")
                continue
            
            # Anfrage an Agent senden
            print("\n🤔 Agent denkt nach...\n")
            response = agent.chat(user_input)
            print(f"🤖 Agent: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Auf Wiedersehen!")
            break
        except Exception as e:
            print(f"\n❌ Fehler: {e}\n")
            if debug:
                import traceback
                traceback.print_exc()


def run_streamlit(agent_mode: str):
    """
    Starte Streamlit Web-Interface.
    
    Args:
        agent_mode: "single" oder "multi"
    """
    import subprocess
    
    streamlit_path = project_root / "src" / "ui" / "streamlit_app.py"
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(streamlit_path),
        "--",
        f"--agent-mode={agent_mode}"
    ]
    
    print(f"🚀 Starte Streamlit UI im {agent_mode.upper()}-Modus...")
    subprocess.run(cmd)


def main():
    """Hauptfunktion."""
    args = parse_arguments()
    
    if args.ui:
        run_streamlit(args.agent_mode)
    else:
        run_cli(args.agent_mode, debug=args.debug)


if __name__ == "__main__":
    main()
