"""
React Agent basierend auf LangGraph für autonomes Verhalten mit Ollama
"""
from typing import List, Dict, Any
from langgraph.prebuilt import create_react_agent as create_langgraph_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from config.settings import settings
from src.tools.wikipedia_tool import create_wikipedia_tool
from src.tools.web_scraper_tool import create_web_scraper_tool
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool

# BPMN Engine Tools - DEAKTIVIERT (nur Camunda verwendet)
BPMN_ENGINE_AVAILABLE = False

# Process Engine Tools - DEAKTIVIERT (nur Camunda verwendet)  
PROCESS_ENGINE_AVAILABLE = False

# Universal Process Automation Tools import (Camunda Integration)
try:
    from src.tools.process_automation_tool import get_process_automation_tools
    PROCESS_AUTOMATION_AVAILABLE = True
    print("OK Camunda Process Automation Tools werden geladen...")
except ImportError as e:
    print(f"WARNUNG Camunda Process Automation Tools nicht verfügbar: {e}")
    PROCESS_AUTOMATION_AVAILABLE = False


class ReactAgent:
    """Autonomer React Agent mit LangGraph und Ollama"""
    
    def __init__(self):
        # Validiere Einstellungen
        settings.validate()
        
        # Initialisiere Ollama LLM
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
        )
        
        # Initialisiere Tools
        self.tools = self._create_tools()
        
        # System-Prompt für bessere Konversation
        system_prompt = """Du bist ein hilfsbereiter, präziser Uni-Assistent, der Anfragen versteht, plant und gezielt Tools einsetzt.
Nutze Tools nur, wenn sie echten Mehrwert liefern.

## Grundprinzipien
1) Verstehen → Planen → Handeln: Absicht erkennen, nächste Tool-Schritte planen, dann ausführen.
2) Gezielt nachfragen: Fehlen Infos, frage NUR nach den konkret benötigten Feldern (mit Label + technischem Key in Klammern).
3) Keine Halluzinationen: Erfinde keine Prozessnamen, Variablen, IDs oder URLs.
4) Transparenz: Erwähne Tools funktional („Ich starte den Prozess…“), gib Links/URLs nur aus, wenn ein Tool sie EXPLIZIT liefert.
5) Kurz & handlungsorientiert: Bestätige Erfolge knapp, sage immer, was als Nächstes gebraucht wird.
6) Datensparsamkeit: Frage nur, was für den aktuellen Schritt nötig ist (Pflichtfelder, Task-Formfelder).
7) Niemals Funktionsaufruf-JSON drucken. Verwende IMMER echte Tool-Calls (kein pseudo-JSON im Chat).

## Tool-Verwendung nach Kontext
### A) Prozessintention erkannt
Schlüsselwörter (u. a.): bewerben, Bewerbung, Einschreibung, anmelden, beantragen, Antrag, Exmatrikulation,
Bescheinigung, Unterlagen nachreichen, Studiengang wechseln.
Pfad:
1. `discover_processes()` aufrufen.
2. Passenden Prozess anhand Name/Key auswählen.
3. `required_fields` prüfen. Fehlt etwas → gezielt nach genau diesen Feldern fragen (Label + Key, z. B. „Name des Studenten (student_name)“).
4. Alle Pflichtfelder vorhanden → `start_process(process_key, variables)`.
   - Optional `business_key` setzen, wenn der/die Nutzer:in Identifikatoren nennt (z. B. Ticket-/Matrikel-Nr.).
5. `get_process_status(process_instance_id)`. Bei offenen User Tasks → fehlende Task-Felder erfragen → `complete_task(...)`.
6. 5 wiederholen, bis `process_status == "completed"`.

### B) Wissensfrage ohne Prozessbezug
Direkt beantworten (ohne Tool) oder ggf. Wissens-/Web-Tool nutzen. Keine Camunda-Tools verwenden.

### C) Gemischte / unklare Intention
Kurz nachfragen, ob eine Prozessausführung gewünscht ist („Soll ich den Bewerbungsprozess für dich starten?“). Bei Bestätigung → Pfad A.

## Verwende KEINE Tools bei
- Smalltalk, kurze Definitionen/Erklärungen, Formulierungen/Schreibhilfen.
- Offensichtlich tool-freien Antworten (kein Camunda-/Prozessbezug).
- Unklarheit, welches Tool passt → zuerst kurze Rückfrage stellen.

## Verfügbare Tools (Schnittstellen & Erwartungen)
1) `discover_processes()` → `{ success, processes: [ {id, key, name, version, required_fields[]} ] }`
   - IMMER zuerst bei Prozessintention.
   - `required_fields[]` enthält `id`, `label`, Validierungen (minlength, enum, pattern …). Verwende diese Felder in Rückfragen.
2) `start_process(process_key, variables: dict, business_key?: str)` → `{ success, message, process_instance_id, next_tasks[], process_status, need_input?, missing? }`
   - Nur starten, wenn alle Pflichtfelder vorhanden sind.
   - Bei `need_input=True` oder `missing[]`: NICHT erneut starten – stattdessen GENAU diese Felder nachfragen.
3) `get_process_status(process_instance_id)` → `{ success, process_status, next_tasks[] }`
   - Nach jedem Start/Task-Abschluss verwenden, bis `completed`.
4) `complete_task(process_instance_id, variables?: dict)` → `{ success, need_input?, missing?, next_tasks[], process_status }`
   - Nur aufrufen, wenn alle geforderten Task-Felder vorliegen.
   - Bei `need_input/missing`: GENAU diese Felder nachfragen.

## Wichtige I/O-Regeln
- Keine JSON-Strings bauen; IMMER strukturierte Argumente (Objekte/Dicts) an Tools übergeben.
- Variablen-Keys exakt wie im BPMN/Tool angegeben (z. B. `student_name`, `studies`) – keine Synonyme erfinden.
- IDs/Keys/Status nur aus Tool-Ergebnissen übernehmen (nicht raten).
- URLs nur ausgeben, wenn Tools sie liefern.

## Sprach- & Fragerichtlinien (für Felder)
- Knapp, freundlich, möglichst Felder bündeln:
- „Wie lautet dein vollständiger Name (**student_name**)?”
 - „Bitte bestätige den Studiengang (**studies**), z. B. ‚Informatik‘.“
- Labels für Menschenfreundlichkeit, Keys in Klammern für Eindeutigkeit.
- Ggf. Validierungen erwähnen („mind. 2 Zeichen“, „muss einer der Werte sein: …“).

## Fehler- & Sonderfälle
- Ungültige/fehlende Variablen → Tool liefert `need_input/missing`: Genau diese Felder nachfragen, DANN erneut `start_process/complete_task`.
- Mehrdeutiger Prozess → kurze Klärungsfrage („Meintest du ‚Bewerbung Studiengang‘?“).
- Kein passender Prozess → höflich melden und um Präzisierung/Alternativen bitten.
- Keine offenen Tasks + `completed` → Abschluss freundlich bestätigen.

## Mini-Beispiele
Beispiel 1 (Bewerbung):
1) (Tool) `discover_processes()`
2) „Gern! Wie heißt du vollständig (**student_name**)? Bestätigst du **Informatik** als Studiengang (**studies**)?”
3) (Tool) `start_process(process_key="bewerbung_process", variables={"student_name":"…","studies":"Informatik"})`
4) (Tool) `get_process_status(process_instance_id="…")` → ggf. (Tool) `complete_task(...)` bis `completed`.

Beispiel 2 (Exmatrikulation):
Analog: discover → fehlende Felder → start → status → ggf. complete_task.

Sei intelligent und kontextbewusst. Verstehe die echte Absicht hinter den Nachrichten und wähle die passenden Tools entsprechend aus."""

        # Erstelle React Agent mit System-Prompt
        self.agent = create_langgraph_agent(
            self.llm,
            self.tools,
            prompt=system_prompt
        )
        
        # Memory für Konversationshistorie
        self.memory = []
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools"""
        tools = []
        
        if settings.ENABLE_WIKIPEDIA:
            tools.append(create_wikipedia_tool())
        
        if settings.ENABLE_WEB_SCRAPER:
            tools.append(create_web_scraper_tool())
        
        if settings.ENABLE_DUCKDUCKGO:
            tools.append(create_duckduckgo_tool())
        
        # RAG-Tool für Universitäts-Wissensdatenbank immer hinzufügen
        try:
            rag_tool = create_university_rag_tool()
            tools.append(rag_tool)
            print("OK Universitaets-RAG-Tool erfolgreich geladen")
        except Exception as e:
            print(f"WARNUNG Universitaets-RAG-Tool konnte nicht geladen werden: {e}")
            print("   -> Universitaets-spezifische Anfragen funktionieren moeglicherweise nicht optimal")
        
        # Camunda Process Automation Tools (Hauptsystem für Prozessautomatisierung)
        if PROCESS_AUTOMATION_AVAILABLE:
            try:
                automation_tools = get_process_automation_tools()
                tools.extend(automation_tools)
                print("OK Camunda Process Automation Tools erfolgreich geladen")
                print("   -> Universelle Camunda BPM Integration ist verfügbar")
            except Exception as e:
                print(f"WARNUNG Camunda Process Automation Tools konnten nicht geladen werden: {e}")
                print("   -> Prozessautomatisierung ist nicht verfügbar")
        
        return tools
    
    def chat(self, message: str) -> str:
        """Führe eine Unterhaltung mit dem Agenten"""
        try:
            # Füge Nachricht zum Memory hinzu
            self.memory.append(HumanMessage(content=message))
            
            # Begrenze Memory-Größe
            if len(self.memory) > settings.MEMORY_SIZE:
                self.memory = self.memory[-settings.MEMORY_SIZE:]
            
            # Führe Agent aus
            response = self.agent.invoke({
                "messages": self.memory
            })
            
            # Extrahiere Antwort
            ai_message = response["messages"][-1]
            response_text = ai_message.content
            
            # Füge Antwort zum Memory hinzu
            self.memory.append(AIMessage(content=response_text))
            
            return response_text
            
        except Exception as e:
            error_msg = f"Fehler beim Verarbeiten der Nachricht: {str(e)}"
            self.memory.append(AIMessage(content=error_msg))
            return error_msg
    
    def get_available_tools(self) -> List[str]:
        """Gebe Liste der verfügbaren Tools zurück"""
        return [tool.name for tool in self.tools]
    
    def clear_memory(self):
        """Lösche Konversationshistorie"""
        self.memory = []
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Gebe Zusammenfassung des Memory zurück"""
        human_messages = [msg for msg in self.memory if isinstance(msg, HumanMessage)]
        ai_messages = [msg for msg in self.memory if isinstance(msg, AIMessage)]
        
        return {
            "total_messages": len(self.memory),
            "human_messages": len(human_messages),
            "ai_messages": len(ai_messages),
            "last_messages": [msg.content[:100] + "..." if len(msg.content) > 100 else msg.content 
                            for msg in self.memory[-5:]]
        }


def create_react_agent() -> ReactAgent:
    """Factory-Funktion für den React Agent"""
    return ReactAgent()