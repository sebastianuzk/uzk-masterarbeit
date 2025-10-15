"""
Streamlit Web Interface für den Autonomen Chatbot-Agenten mit CAMUNDA Process Engine
"""
import streamlit as st
import sys
import os
import logging
import time
import subprocess
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.agent.react_agent import create_react_agent
from config.settings import settings
from src.process_automation.process_engine.integration import get_bpmn_engine
from src.ui.bpmn_interface import display_bpmn_engine_interface
from src.ui.camunda_interface import display_camunda_engine_interface
from src.camunda_integration.services.docker_manager import DockerManager

# Setup logging
logging.basicConfig(level=logging.INFO)

def auto_start_docker_camunda():
    """Automatischer Start des Camunda Docker Containers"""
    if 'docker_auto_started' not in st.session_state:
        st.session_state.docker_auto_started = False
        
    if not st.session_state.docker_auto_started:
        try:
            compose_file = Path("src/camunda_integration/docker/docker-compose.yml")
            docker_manager = DockerManager(compose_file=compose_file)
            
            # Prüfe ob Container bereits läuft
            status_result = docker_manager.get_status()
            if status_result.get("success") and "camunda-platform-manual" in status_result.get("output", ""):
                # Container läuft bereits, prüfe auch API
                try:
                    import requests
                    response = requests.get("http://localhost:8080/engine-rest/engine", timeout=5)
                    if response.status_code == 200:
                        st.session_state.docker_auto_started = True
                        st.session_state.docker_status = "✅ Camunda Docker Container bereits aktiv und erreichbar"
                        return
                except:
                    pass  # API noch nicht bereit
                
                st.session_state.docker_status = "🔄 Container läuft, warte auf API..."
                return
            
            # Zeige Status während Start
            status_placeholder = st.empty()
            
            with status_placeholder.container():
                st.info("🚀 Starte Camunda Docker Container automatisch...")
                
                # Starte Container
                result = docker_manager.start_camunda(detached=True)
                
                if result.get("success", False):
                    st.success("✅ Camunda Docker Container erfolgreich gestartet!")
                    st.info("⏳ Warte auf Camunda-Initialisierung...")
                    
                    # Warte auf Camunda-Start mit Progress Bar
                    progress_bar = st.progress(0)
                    for i in range(60):  # 60 Sekunden warten
                        time.sleep(1)
                        progress_bar.progress((i + 1) / 60)
                        
                        # Prüfe API-Verfügbarkeit
                        if i > 20:  # Nach 20 Sekunden API prüfen
                            try:
                                import requests
                                response = requests.get("http://localhost:8080/engine-rest/engine", timeout=2)
                                if response.status_code == 200:
                                    progress_bar.progress(1.0)
                                    break
                            except:
                                continue
                    
                    st.success("🎉 Camunda Engine ist bereit!")
                    st.session_state.docker_auto_started = True
                    st.session_state.docker_status = "✅ Camunda automatisch gestartet"
                    
                    # Entferne Status-Container nach erfolgreichem Start
                    time.sleep(2)
                    status_placeholder.empty()
                else:
                    error_msg = result.get("error", "Unbekannter Fehler")
                    st.error(f"❌ Docker-Start fehlgeschlagen: {error_msg}")
                    st.session_state.docker_status = f"❌ Docker-Start fehlgeschlagen: {error_msg}"
                    
        except Exception as e:
            st.error(f"❌ Docker Auto-Start Fehler: {str(e)}")
            st.session_state.docker_status = f"❌ Fehler: {str(e)}"


def initialize_session_state():
    """Initialisiere Session State"""
    # AUTO-START: Camunda Docker Container
    auto_start_docker_camunda()
    
    # BPMN Process Engine - DEAKTIVIERT für Camunda-Only Mode
    if 'bpmn_engine_initialized' not in st.session_state:
        # TEMPORÄR DEAKTIVIERT: Separate BPMN Engine um Auto-Deployment zu verhindern
        st.session_state.bpmn_engine_initialized = False
        st.session_state.bpmn_engine_error = "BPMN Engine deaktiviert - Nur Camunda Platform 7 aktiv"
        
        # ORIGINAL CODE (auskommentiert):
        # try:
        #     bpmn_manager = get_bpmn_engine()
        #     # Engine automatisch starten
        #     if not bpmn_manager.running:
        #         bpmn_manager.start()
        #     st.session_state.bpmn_engine_initialized = True
        #     st.session_state.bpmn_engine_error = None
        #     st.session_state.bpmn_manager = bpmn_manager
        # except Exception as e:
        #     st.session_state.bpmn_engine_initialized = False
        #     st.session_state.bpmn_engine_error = str(e)
    
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
        st.title("🔧 System Status")
        
        # Docker Camunda Status (neu hinzugefügt)
        st.subheader("🐳 Camunda Docker Container")
        if 'docker_status' in st.session_state:
            if "✅" in st.session_state.docker_status:
                st.success(st.session_state.docker_status)
            elif "❌" in st.session_state.docker_status:
                st.error(st.session_state.docker_status)
            else:
                st.info(st.session_state.docker_status)
        else:
            st.info("🔄 Docker-Status wird geprüft...")
        
        st.markdown("---")
        
        # BPMN Process Engine Status
        st.subheader("🔄 BPMN Process Engine")
        if st.session_state.get('bpmn_engine_initialized', False):
            bpmn_manager = st.session_state.bpmn_manager
            
            # Hole Engine-Status
            try:
                instances = bpmn_manager.execution_engine.get_active_instances()
                active_instances = [inst for inst in instances if inst.status == 'ACTIVE']
                
                st.success("✅ BPMN Engine aktiv")
                st.write(f"Typ: BPMN 2.0 Process Engine")
                st.write(f"Aktive Prozesse: {len(active_instances)}")
                st.write(f"Gesamt Prozesse: {len(instances)}")
                
                # Zeige aktive Prozesse
                if active_instances:
                    st.markdown("**Aktive Prozess-Instanzen:**")
                    for inst in active_instances[:3]:  # Nur die ersten 3 anzeigen
                        st.write(f"• {inst.id[:8]}... ({inst.process_definition.id})")
                        
            except Exception as e:
                st.warning(f"⚠️ Status-Fehler: {str(e)}")
        else:
            st.error("❌ BPMN Engine Fehler")
            if 'bpmn_engine_error' in st.session_state:
                st.error(f"Fehler: {st.session_state.bpmn_engine_error}")
        
        st.markdown("---")
        
        # Agent-Informationen
        st.subheader("🤖 Chatbot Agent")
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
        
        st.markdown("---")
        
        # Konfiguration anzeigen
        st.subheader("⚙️ Konfiguration")
        st.write(f"Modell: {settings.OLLAMA_MODEL}")
        st.write(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
        st.write(f"Temperatur: {settings.TEMPERATURE}")
        
        # Ollama-Status
        st.subheader("🦙 Ollama Status")
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
        page_title=settings.PAGE_TITLE + " + BPMN Engine",
        page_icon=settings.PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Titel
    st.title(f"{settings.PAGE_ICON} {settings.PAGE_TITLE} + BPMN 2.0 Process Engine")
    st.markdown("---")
    
    # Initialisiere Session State
    initialize_session_state()
      
    # Zeige Seitenspalte
    display_sidebar()
    
    # Tabs für verschiedene Bereiche
    tab1, tab2, tab3 = st.tabs(["💬 Chatbot", "🔄 BPMN Process Engine", "🏗️ Camunda Engine"])
    
    with tab1:
        display_chat_tab()
    
    with tab2:
        display_bpmn_engine_interface()
        
    with tab3:
        display_camunda_engine_interface()


def display_chat_tab():
    """Zeige Chat-Tab"""
    # Hauptinhalt
    if st.session_state.get('initialized', False):
        st.markdown("### 💬 Chat mit dem Agenten")
        st.markdown("Stellen Sie Fragen oder bitten Sie um Hilfe. Der Agent kann Wikipedia durchsuchen, Webseiten scrapen, aktuelle Informationen finden und echte BPMN-Prozesse verwalten.")
        
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
        - **BPMN Process Engine**: Echte BPMN 2.0 konforme Process Engine
        """)


if __name__ == "__main__":
    main()