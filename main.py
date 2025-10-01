"""
Haupteinstiegspunkt für den Autonomen Chatbot-Agenten
"""
import sys
import os

# Füge das aktuelle Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent.react_agent import ReactAgent
from config.settings import settings


def main():
    """Hauptfunktion für die Kommandozeilen-Interaktion"""
    print(f"🤖 {settings.PAGE_TITLE}")
    print("=" * 50)
    print("Willkommen beim Autonomen Chatbot-Agenten!")
    print("Geben Sie 'quit' oder 'exit' ein, um das Programm zu beenden.")
    print("Geben Sie 'help' ein, um verfügbare Befehle zu sehen.")
    print("-" * 50)
    
    try:
        # Initialisiere Agent
        print("Initialisiere Agent...")
        agent = ReactAgent()
        print("✅ Agent erfolgreich initialisiert!")
        
        # Zeige verfügbare Tools
        tools = [tool.name for tool in agent.tools]
        print(f"📋 Verfügbare Tools: {', '.join(tools)}")
        print("-" * 50)
        
        # Interaktive Schleife
        while True:
            try:
                # Benutzereingabe
                user_input = input("\n🙋 Sie: ").strip()
                
                # Spezielle Befehle
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Auf Wiedersehen!")
                    break
                
                elif user_input.lower() == 'help':
                    print_help()
                    continue
                
                elif user_input.lower() == 'clear':
                    agent.memory = []
                    print("🗑️ Memory wurde geleert!")
                    continue
                
                elif user_input.lower() == 'status':
                    memory_count = len(agent.memory)
                    print(f"📊 Memory Status: {memory_count} Nachrichten im Speicher")
                    continue
                
                elif not user_input:
                    continue
                
                # Agent-Antwort
                print("\n🤖 Agent denkt nach...")
                response = agent.chat(user_input)
                print(f"\n🤖 Agent: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Programm wurde beendet!")
                break
            
            except Exception as e:
                print(f"\n❌ Fehler: {str(e)}")
                print("Versuchen Sie es erneut oder geben Sie 'help' für Hilfe ein.")
    
    except Exception as e:
        print(f"❌ Fehler beim Initialisieren des Agenten: {str(e)}")
        print("\n🔧 Überprüfen Sie Ihre Konfiguration:")
        print("1. Stellen Sie sicher, dass eine .env Datei existiert")
        print("2. OPENAI_API_KEY muss gesetzt sein")
        print("3. Alle Abhängigkeiten müssen installiert sein")


def print_help():
    """Zeige Hilfeinformationen"""
    print("\n📖 Verfügbare Befehle:")
    print("  help    - Zeige diese Hilfe")
    print("  clear   - Lösche Konversationshistorie")
    print("  status  - Zeige Memory-Status")
    print("  quit    - Beende das Programm")
    print("\n💡 Der Agent kann:")
    print("  • Wikipedia durchsuchen")
    print("  • Webseiten scrapen")
    print("  • Aktuelle Informationen im Internet finden")
    print("  • Komplexe Fragen beantworten")
    print("  • Schrittweise Problemlösungen durchführen")


if __name__ == "__main__":
    main()