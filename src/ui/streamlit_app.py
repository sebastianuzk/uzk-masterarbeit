"""
Streamlit Web Interface für den Autonomen Chatbot-Agenten
"""
import streamlit as st
import sys
import os

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.agent.react_agent import create_react_agent
from config.settings import settings

# Process Engine automatisch starten
from src.process_engine.service import auto_start_process_engine, get_process_engine_service
auto_start_process_engine()


def display_process_engine_status():
    """Zeigt Process Engine Status in der Sidebar"""
    st.sidebar.markdown("### 🏢 Process Engine")
    
    try:
        service = get_process_engine_service()
        status = service.get_status()
        
        if status["is_initializing"]:
            st.sidebar.warning("🔄 Initialisierung läuft...")
        elif status["initialization_complete"]:
            if status.get("mock_mode", True):
                st.sidebar.info("⚙️ Mock-Modus aktiv")
                st.sidebar.caption("Für echte Camunda: `docker-compose up -d`")
            else:
                st.sidebar.success("✅ Camunda aktiv")
                st.sidebar.caption(f"Gateway: {status.get('gateway_address', 'N/A')}")
            
            # Aktive Prozesse anzeigen
            active_count = status.get("active_processes", 0)
            if active_count > 0:
                st.sidebar.metric("Aktive Prozesse", active_count)
        elif status["initialization_error"]:
            st.sidebar.error("❌ Initialisierung fehlgeschlagen")
            st.sidebar.caption(status["initialization_error"])
        else:
            st.sidebar.warning("⏳ Warte auf Initialisierung...")
            
    except Exception as e:
        st.sidebar.error(f"❌ Status-Fehler: {e}")


def initialize_session_state():
    """Initialisiere Session State"""
    if 'agent' not in st.session_state:
        try:
            st.session_state.agent = create_react_agent()
            st.session_state.initialized = True
        except Exception as e:
            st.session_state.initialized = False
            st.session_state.error = str(e)
    
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
        
        # Generiere Antwort
        with st.spinner("Denke nach..."):
            try:
                response = st.session_state.agent.chat(prompt)
                
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
        
        # Agent-Informationen
        if st.session_state.get('initialized', False):
            st.success("✅ Agent initialisiert")
            
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
        
        # Ollama-Status
        st.subheader("� Ollama Status")
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
    
    # Process Engine Status anzeigen
    display_process_engine_status()
    
    # Zeige Seitenspalte
    display_sidebar()
    
    # Hauptinhalt
    if st.session_state.get('initialized', False):
        st.markdown("### 💬 Chat mit dem Agenten")
        st.markdown("Stellen Sie Fragen oder bitten Sie um Hilfe. Der Agent kann Wikipedia durchsuchen, Webseiten scrapen und aktuelle Informationen finden.")
        
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
        - **Wikipedia**: Kostenlose Wissensdatenbank
        - **Web Scraper**: Direkter Zugriff auf Webseiten
        - **DuckDuckGo**: Privatsphärefreundliche Websuche
        """)


if __name__ == "__main__":
    main()