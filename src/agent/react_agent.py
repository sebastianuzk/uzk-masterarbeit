"""
React Agent basierend auf LangGraph für autonomes Verhalten mit Ollama
"""
import os
import uuid
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent as create_langgraph_agent

from config.settings import settings
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.email_tool import create_email_tool
from src.tools.klips import (
    create_klips2_register_tool,
    create_klips2_apply_tool,
    create_klips2_change_password_tool,
    create_klips2_get_course_details_tool,
    create_klips2_change_address_tool
)
from src.tools.rag_tool import create_university_rag_tool
from src.tools.web_scraper_tool import create_web_scraper_tool


class ReactAgent:
    """Autonomer React Agent mit LangGraph und Ollama"""
    
    def __init__(self):
        # Validiere Einstellungen
        settings.validate()
        
        # LangSmith Tracing konfigurieren (falls aktiviert)
        if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            print(f"✅ LangSmith-Tracing aktiviert für Projekt: {settings.LANGSMITH_PROJECT}")
        
        # Initialisiere Ollama LLM (optimiert für Performance)
        # Context-Size nach Modellgröße - größer für bessere Multi-Turn Gespräche
        MODEL_CTX_SIZES = {
            "0.5b": 2048,
            "1b": 4096,
            "3b": 8192,
            "8b": 12288,
            "20b": 16384,
            "70b": 16384,
        }
        
        # Modellgröße aus Namen extrahieren
        model_lower = settings.OLLAMA_MODEL.lower()
        ctx_size = 8192  # Standard - ausreichend für die meisten Gespräche
        for size_key, ctx_value in MODEL_CTX_SIZES.items():
            if size_key in model_lower:
                ctx_size = ctx_value
                break
        
        print(f"🤖 Initialisiere ChatOllama mit Modell: {settings.OLLAMA_MODEL} (ctx_size={ctx_size})")

        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
            num_ctx=ctx_size,  # Adaptiver Context für schnellere Antworten
        )
        
        # Initialisiere Tools (einschließlich E-Mail-Tool)
        self.tools = self._create_tools()
        
        # Professioneller System-Prompt für präzise Tool-Nutzung (Deutsch)
        system_prompt = """Du bist ein KI-Assistent für KLIPS 2.0, das Campus-Management-System der Universität zu Köln. Du unterstützt Studierende und Mitarbeitende bei Registrierung, Bewerbungen, Kursverwaltung und allgemeinen Universitätsfragen.

## KRITISCHE REGELN (NIEMALS VERLETZEN!)

1. **STOPP-REGEL**: Bevor du EIN Tool aufrufst, PRÜFE ob ALLE Pflichtparameter vom Nutzer angegeben wurden.
   - Fehlt auch nur EIN Pflichtparameter → KEIN Tool-Aufruf, sondern NACHFRAGEN!
   - NIEMALS fehlende Daten erfinden, vermuten oder mit Platzhaltern ausfüllen!

2. **VALIDIERUNGS-REGEL**: Prüfe das korrekte Format BEVOR du ein Tool aufrufst:
   - E-Mail: Muss @ und Punkt enthalten (z.B. max@uni-koeln.de)
   - Datum: Format TT.MM.JJJJ (z.B. 15.03.1999)
   - URL: Muss mit http:// oder https:// beginnen

3. **SPRACHANPASSUNG**: Antworte in der Sprache des Nutzers.

4. **KEINE ERFUNDENEN DATEN**: Wenn Daten fehlen oder ungültig sind, erkläre das Problem und bitte um Korrektur.



## VERFÜGBARE TOOLS MIT PARAMETERN

### 1. klips2_register
**Zweck**: Neuen KLIPS2-Account erstellen (für Erstbenutzer ohne Account).
**Pflichtparameter**:
  - `vorname`: Vorname des Nutzers
  - `nachname`: Nachname des Nutzers
  - `geschlecht`: männlich/weiblich/divers (auch: m/w/d, male/female)
  - `geburtsdatum`: Geburtsdatum im Format TT.MM.JJJJ
  - `email`: Gültige E-Mail-Adresse
  - `staatsangehoerigkeit`: Nationalität (z.B. "deutsch", "Deutschland", "türkisch")
**Optionale Parameter**:
  - `geburtsname`: Falls abweichend vom aktuellen Namen
  - `sprache`: Bevorzugte Sprache (Standard: Deutsch)

### 2. klips2_apply_study
**Zweck**: Bewerbung für einen Studiengang einreichen.
**Pflichtparameter (Basis)**:
  - `username`: KLIPS2-Benutzername/E-Mail
  - `password`: KLIPS2-Passwort
  - `semester`: Zielsemester (z.B. "Wintersemester 2025/26", "WS 2025")
  - `degree_type`: Abschlussart (Bachelor/Master/Promotionsstudium)
  - `study_program`: Exakter Name des Studiengangs
  - `entry_semester`: Einstiegsfachsemester (z.B. "1", "3")
  - `study_form`: Erststudium oder Zweitstudium
**Pflichtparameter (Persönliche Daten)**:
  - `gender`: Geschlecht (Männlich/Weiblich/Divers)
  - `birth_place`: Geburtsort
  - `birth_country`: Geburtsland (z.B. "Deutschland")
  - `nationality`: Staatsangehörigkeit (z.B. "deutsch")
**Pflichtparameter (HZB - Hochschulzugangsberechtigung)**:
  - `hzb_date`: Datum der HZB (Format: TT.MM.JJJJ)
  - `hzb_type`: Art der HZB (z.B. "Allgemeine Hochschulreife", "Fachhochschulreife")
  - `hzb_name`: Bezeichnung des Zeugnisses (z.B. "Abitur")
  - `hzb_grade`: Note der HZB (z.B. "2,3")
  - `hzb_school`: Name der Schule
  - `hzb_country`: Land der HZB (z.B. "Deutschland")
  - `hzb_place`: Ort/Kreis der HZB
**Zusätzliche Pflichtparameter bei Zweitstudium** (wenn study_form="Zweitstudium"):
  - `prev_uni`: Name der vorherigen Hochschule
  - `prev_program`: Vorheriger Studiengang
  - `prev_degree`: Erreichter/Angestrebter Abschluss
  - `prev_semesters`: Anzahl der Semester
**Optionale Parameter**:
  - `validate_only`: Nur prüfen ohne Absenden (true/false)
  - `street`, `zip_code`, `city`, `country`, `phone`: Adressdaten

### 3. klips2_change_address
**Zweck**: Adresse im KLIPS2-Profil aktualisieren.
**Pflichtparameter**:
  - `username`: KLIPS2-Benutzername
  - `password`: KLIPS2-Passwort
  - `street`: Straße und Hausnummer
  - `zip_code`: Postleitzahl
  - `city`: Stadt
**Optionale Parameter**:
  - `country`: Land (Standard: Deutschland)

### 4. klips2_change_password
**Zweck**: KLIPS2-Passwort ändern.
**Pflichtparameter**:
  - `username`: Benutzername
  - `password`: Aktuelles Passwort
  - `new_password`: Neues Passwort

### 5. klips2_get_course_details
**Zweck**: Details zu einer Lehrveranstaltung abrufen.
**Pflichtparameter**:
  - `course_id`: Kursnummer (z.B. "14302.0001")
**Optionale Parameter**:
  - `semester`: Semester (z.B. "WiSe 2024/25")

### 6. university_knowledge_search
**Zweck**: Universitäts-Wissensdatenbank durchsuchen für Infos zu Fristen, Studiengängen, Verfahren und allgemeinen Fragen über die WiSo Köln.
**Pflichtparameter**:
  - `query`: Suchanfrage

### 7. duckduckgo_search
**Zweck**: Web-Suche für externe Informationen.
**Pflichtparameter**:
  - `query`: Suchanfrage
**Hinweis**: Nutzer informieren, dass Ergebnisse möglicherweise nicht von offiziellen Uni-Quellen stammen!

### 8. web_scraper
**Zweck**: Textinhalte einer bestimmten Webseite extrahieren.
**Pflichtparameter**:
  - `url`: Vollständige URL (mit http:// oder https://)

### 9. send_email
**Zweck**: E-Mail an den konfigurierten Support senden.
**Pflichtparameter**:
  - `subject`: Betreff der E-Mail
  - `body`: Nachrichteninhalt

## ENTSCHEIDUNGSBAUM

```
Nutzeranfrage → Braucht es ein Tool?
                    │
              JA    │    NEIN → Direkt antworten oder university_knowledge_search
                    ▼
         Welches Tool ist richtig?
                    │
                    ▼
         Alle PFLICHTPARAMETER vorhanden?
              │           │
           JA │           │ NEIN
              ▼           ▼
    Parameter gültig?   LISTE fehlende Parameter auf
         │              und FRAGE NACH!
      JA │ NEIN         (KEIN Tool-Aufruf!)
         ▼   ▼
    TOOL    Erkläre Problem,
    AUSFÜHREN  bitte um Korrektur
```

## BEISPIELE

✅ **RICHTIG** (alle Daten vorhanden):
Nutzer: "Registriere mich: Max Müller, männlich, 15.03.1999, max@email.de, deutsch"
→ Alle 6 Pflichtparameter vorhanden → klips2_register aufrufen

✅ **RICHTIG** (Daten fehlen → nachfragen):
Nutzer: "Ich möchte mich für BWL bewerben"
→ "Für die Bewerbung benötige ich:
   • Deinen KLIPS2-Benutzernamen
   • Dein KLIPS2-Passwort
   • Das Zielsemester (z.B. Wintersemester 2025/26)
   • Den gewünschten Abschluss (Bachelor/Master)"

❌ **FALSCH** (niemals so handeln!):
Nutzer: "Registriere mich, ich bin Max aus Köln"
→ NICHT klips2_register mit erfundenen Daten aufrufen!
→ Stattdessen nach fehlenden Pflichtparametern fragen

## SPRACHVERSTÄNDNIS
- Erkenne Anfragen auch in **informeller/konversationeller Sprache**:
  - "Hey, ich bin Lisa und möchte..." → Normale Anfrage, extrahiere Daten
  - "Kannst du mal..." → Tool-Anfrage erkennen
  - "Ich bräuchte..." → Tool-Anfrage erkennen
- Extrahiere Informationen aus Fließtext:
  - "Ich heiße Max Müller, bin am 15.3.1999 geboren" → vorname="Max", nachname="Müller", geburtsdatum="15.03.1999"
- Verstehe auch englische Anfragen und antworte entsprechend

## ANTWORTSTIL
- Präzise und hilfsbereit
- Aufzählungen für fehlende Parameter
- Erfolge klar bestätigen
- Fehler verständlich erklären
- Bei informellen Anfragen: freundlich aber professionell antworten"""

        # Erstelle React Agent mit kompaktem System-Prompt
        self.agent = create_langgraph_agent(
            self.llm,
            self.tools
        )
        
        # Füge System-Prompt manuell zum Memory hinzu
        self.system_message = SystemMessage(content=system_prompt)
        
        # Memory für Konversationshistorie
        self.memory = []
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools einschließlich E-Mail-Tool"""
        tools = []
        
        if settings.ENABLE_WEB_SCRAPER:
            tools.append(create_web_scraper_tool())
        
        if settings.ENABLE_DUCKDUCKGO:
            tools.append(create_duckduckgo_tool())
        
        # RAG-Tool für Universitäts-Wissensdatenbank immer hinzufügen
        try:
            rag_tool = create_university_rag_tool()
            tools.append(rag_tool)
            print("✅ Universitäts-RAG-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️  Universitäts-RAG-Tool konnte nicht geladen werden: {e}")
            print("   → Universitäts-spezifische Anfragen funktionieren möglicherweise nicht optimal")
        
        # E-Mail-Tool für Support-Eskalation immer hinzufügen
        try:
            email_tool = create_email_tool()
            tools.append(email_tool)
            print("✅ E-Mail-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️  E-Mail-Tool konnte nicht geladen werden: {e}")
            print("   → Support-Eskalation per E-Mail nicht verfügbar")
        
        # KLIPS2-Registrierungs-Tool hinzufügen
        try:
            klips2_tool = create_klips2_register_tool()
            tools.append(klips2_tool)
            print("✅ KLIPS2-Registrierungs-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️  KLIPS2-Registrierungs-Tool konnte nicht geladen werden: {e}")
            print("   → KLIPS2-Account-Erstellung nicht verfügbar")
            
        # KLIPS2-Erweiterte Tools hinzufügen
        try:
            tools.append(create_klips2_apply_tool())
            tools.append(create_klips2_change_password_tool())
            tools.append(create_klips2_get_course_details_tool())
            tools.append(create_klips2_change_address_tool())
            print("✅ KLIPS2-Erweiterte Tools erfolgreich geladen")
        except Exception as e:
            print(f"⚠️  KLIPS2-Erweiterte Tools konnten nicht geladen werden: {e}")
        
        return tools
    
    def chat(self, message: str, session_id: str = None) -> str:
        """Führe eine Unterhaltung mit dem Agenten"""
        try:
            # Session-ID für Tracing (falls nicht übergeben)
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            # Füge Nachricht zum Memory hinzu
            human_message = HumanMessage(content=message)
            self.memory.append(human_message)
            
            # Begrenze Memory-Größe
            if len(self.memory) > settings.MEMORY_SIZE:
                self.memory = self.memory[-settings.MEMORY_SIZE:]
            
            # Führe Agent aus (mit System-Message und automatischem LangSmith-Tracing)
            agent_input = {
                "messages": [self.system_message] + self.memory
            }

            # Erstelle Config mit Metadaten für LangSmith-Tracing (falls aktiv)
            config = None
            if settings.LANGSMITH_TRACING:
                config = {
                    "metadata": {
                        "session_id": session_id,
                        "user_message": message[:100] + "..." if len(message) > 100 else message,
                        "available_tools": len(self.tools)
                    }
                }

            if config is not None:
                response = self.agent.invoke(agent_input, config=config)
            else:
                response = self.agent.invoke(agent_input)
            
            # Extrahiere Antwort - prüfe verschiedene Message-Typen
            ai_message = response["messages"][-1]
            
            # Debug: Wenn content leer ist, prüfe andere Message-Typen
            response_text = ai_message.content
            if not response_text:
                # Suche nach einer AIMessage mit Inhalt
                for msg in reversed(response["messages"]):
                    if hasattr(msg, 'content') and msg.content:
                        response_text = msg.content
                        break
                
                # Final fallback if still empty
                if not response_text:
                    response_text = "Ich konnte keine Antwort generieren. Bitte versuchen Sie es erneut."
            
            # Füge Antwort zum Memory hinzu
            ai_response = AIMessage(content=response_text)
            self.memory.append(ai_response)
            
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