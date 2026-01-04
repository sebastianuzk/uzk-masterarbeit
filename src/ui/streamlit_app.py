"""
Streamlit Web Interface für den Autonomen Chatbot-Agenten

Unterstützt zwei Agent-Modi:
- Single-Agent: Ursprünglicher ReactAgent mit allen Tools
- Multi-Agent: Orchestriertes System mit spezialisierten Agenten

Start mit Agent-Mode:
    streamlit run src/ui/streamlit_app.py -- --agent-mode multi
    streamlit run src/ui/streamlit_app.py -- --agent-mode single
"""
import argparse
import streamlit as st
import sys
import os
import uuid

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.agent import create_agent
from config.settings import settings


def get_agent_mode() -> str:
    """
    Ermittle den Agent-Mode aus den Kommandozeilenargumenten.
    
    Returns:
        "single" oder "multi"
    """
    # Parse CLI arguments (nach --)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--agent-mode",
        type=str,
        choices=["single", "multi"],
        default="single",
        help="Agent-Modus: 'single' für ReactAgent, 'multi' für Multi-Agent-System"
    )
    
    # Nur eigene Argumente parsen, Rest ignorieren (für Streamlit)
    args, _ = parser.parse_known_args()
    return args.agent_mode


def initialize_session_state():
    """Initialisiere Session State"""
    # Agent-Mode ermitteln
    if 'agent_mode' not in st.session_state:
        st.session_state.agent_mode = get_agent_mode()
    
    if 'agent' not in st.session_state:
        try:
            st.session_state.agent = create_agent(mode=st.session_state.agent_mode)
            st.session_state.initialized = True
        except Exception as e:
            st.session_state.initialized = False
            st.session_state.error = str(e)
    
    # Session-ID für LangSmith-Tracing
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []


def display_chat_interface():
    """Zeige Chat-Interface"""
    # Chat-Container
    chat_container = st.container()
    
    with chat_container:
        # Zeige vorherige Nachrichten
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Chat-Input
    if prompt := st.chat_input("Stellen Sie Ihre Frage..."):
        # Füge Benutzernachricht hinzu
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        
        # Generiere Antwort mit Session-ID für Tracing
        with st.spinner("Denke nach..."):
            try:
                response = st.session_state.agent.chat(
                    prompt, 
                    session_id=st.session_state.session_id
                )
                
                # Füge Antwort hinzu
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                with chat_container:
                    with st.chat_message("assistant"):
                        st.markdown(response)
                        
            except Exception as e:
                error_msg = f"Fehler: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                
                with chat_container:
                    with st.chat_message("assistant"):
                        st.error(error_msg)


def display_sidebar():
    """Zeige Seitenspalte mit Informationen"""
    with st.sidebar:
        st.title("🔧 Einstellungen")
        
        # Agent-Mode anzeigen
        agent_mode = st.session_state.get('agent_mode', 'single')
        if agent_mode == "multi":
            st.info("🎭 **Multi-Agent Modus**")
        else:
            st.info("🤖 **Single-Agent Modus**")
        
        # Agent-Informationen
        if st.session_state.get('initialized', False):
            st.success("✅ Agent initialisiert")
            
            # Multi-Agent: Zeige verfügbare Agenten
            if agent_mode == "multi" and hasattr(st.session_state.agent, 'get_available_agents'):
                st.subheader("🎭 Verfügbare Agenten")
                agents = st.session_state.agent.get_available_agents()
                for agent_name in agents:
                    st.write(f"• {agent_name}")
            
            # Verfügbare Tools
            st.subheader("🛠️ Verfügbare Tools")
            tools = st.session_state.agent.get_available_tools()
            for tool in tools:
                st.write(f"• {tool}")
            
            # Memory-Informationen
            st.subheader("🧠 Memory Status")
            memory_info = st.session_state.agent.get_memory_summary()
            st.write(f"Nachrichten: {memory_info['total_messages']}")
            st.write(f"Benutzer: {memory_info['human_messages']}")
            st.write(f"AI: {memory_info['ai_messages']}")
            
            # Memory löschen
            if st.button("🗑️ Memory löschen"):
                st.session_state.agent.clear_memory()
                st.session_state.messages = []
                st.rerun()
        
        else:
            st.error("❌ Agent nicht initialisiert")
            if 'error' in st.session_state:
                st.error(f"Fehler: {st.session_state.error}")
        
        # Konfiguration anzeigen
        st.subheader("⚙️ Konfiguration")
        st.write(f"Modell: {settings.OLLAMA_MODEL}")
        st.write(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
        st.write(f"Temperatur: {settings.TEMPERATURE}")
        
        # LangSmith-Status
        if settings.LANGSMITH_TRACING:
            st.write(f"🔍 LangSmith: ✅ Aktiv")
            st.write(f"📊 Projekt: {settings.LANGSMITH_PROJECT}")
            st.write(f"🔑 Session: {st.session_state.session_id[:8]}...")
        else:
            st.write(f"🔍 LangSmith: ❌ Inaktiv")
        
        # Ollama-Status
        st.subheader("🤖 Ollama Status")
        try:
            import requests
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
            if response.status_code == 200:
                st.success("Ollama Server: ✅")
                models = response.json().get('models', [])
                if any(model['name'].startswith(settings.OLLAMA_MODEL) for model in models):
                    st.success(f"Modell '{settings.OLLAMA_MODEL}': ✅")
                else:
                    st.warning(f"Modell '{settings.OLLAMA_MODEL}': ⚠️ Nicht gefunden")
                    st.info(f"Installieren Sie es mit: ollama pull {settings.OLLAMA_MODEL}")
            else:
                st.error("Ollama Server: ❌")
        except:
            st.error("Ollama Server: ❌ Nicht erreichbar")
            st.info("Starten Sie Ollama mit: ollama serve")


def main():
    """Hauptfunktion der Streamlit App"""
    # Seitenkonfiguration
    st.set_page_config(
        page_title=settings.PAGE_TITLE,
        page_icon=settings.PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Titel
    st.title(f"{settings.PAGE_ICON} {settings.PAGE_TITLE}")
    st.markdown("---")
    
    # Initialisiere Session State
    initialize_session_state()
    
    # Zeige Seitenspalte
    display_sidebar()
    
    # Hauptinhalt
    if st.session_state.get('initialized', False):
        st.markdown("### 💬 Chat mit dem Agenten")
        st.markdown("Stellen Sie Fragen oder bitten Sie um Hilfe. Der Agent kann Webseiten scrapen, aktuelle Informationen finden.")
        
        display_chat_interface()
    
    else:
        st.error("Agent konnte nicht initialisiert werden. Bitte überprüfen Sie Ihre Konfiguration.")
        
        st.markdown("### 🔧 Konfiguration")
        st.markdown("""
        1. Stellen Sie sicher, dass Ollama installiert und gestartet ist:
           ```bash
           ollama serve
           ```
        2. Installieren Sie das gewünschte Modell:
           ```bash
           ollama pull llama3.2
           ```
        3. Optional: Erstellen Sie eine `.env` Datei für benutzerdefinierte Einstellungen:
           ```
           OLLAMA_BASE_URL=http://localhost:11434
           OLLAMA_MODEL=llama3.2
           ```
        4. Starten Sie die App neu
        
        ### 📖 Verfügbare Open Source Tools:
        - **Web Scraper**: Direkter Zugriff auf Webseiten
        - **DuckDuckGo**: Privatsphärefreundliche Websuche
        """)


if __name__ == "__main__":
    main()