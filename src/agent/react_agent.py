"""
React Agent basierend auf LangGraph für autonomes Verhalten mit Ollama oder OpenAI
"""
import os
import uuid
from typing import Any, Dict, List, Optional

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


def create_llm(provider: Optional[str] = None, model: Optional[str] = None):
    """
    Erstellt das passende LLM basierend auf dem Provider.
    
    Args:
        provider: 'ollama' oder 'openai' (wenn None, aus settings.LLM_PROVIDER)
        model: Modellname (wenn None, aus settings)
        
    Returns:
        LangChain Chat-Modell (ChatOllama oder ChatOpenAI)
    """
    # Provider aus Settings oder Argument
    _provider = provider or getattr(settings, 'LLM_PROVIDER', 'ollama')
    
    if _provider == "openai":
        from langchain_openai import ChatOpenAI
        
        _model = model or settings.OPENAI_MODEL
        
        # OpenAI-Konfiguration
        openai_kwargs = {
            "model": _model,
            "temperature": settings.TEMPERATURE,
            "timeout": settings.REQUEST_TIMEOUT,
        }
        
        # API-Key aus Settings oder Umgebung
        if settings.OPENAI_API_KEY:
            openai_kwargs["api_key"] = settings.OPENAI_API_KEY
        
        # Optional: Custom Base-URL für OpenAI-kompatible APIs
        if settings.OPENAI_BASE_URL:
            openai_kwargs["base_url"] = settings.OPENAI_BASE_URL
        
        print(f"🤖 Initialisiere ChatOpenAI mit Modell: {_model} (temperature={openai_kwargs['temperature']})")
        return ChatOpenAI(**openai_kwargs)
    
    else:
        # Ollama (Standard)
        _model = model or settings.OLLAMA_MODEL
        
        # Context-Size nach Modellgröße
        MODEL_CTX_SIZES = {
            "0.5b": 2048,
            "1b": 4096,
            "3b": 8192,
            "8b": 8192,
            "20b": 16384,
            "70b": 16384,
        }
        
        model_lower = _model.lower()
        ctx_size = 8192
        for size_key, ctx_value in MODEL_CTX_SIZES.items():
            if size_key in model_lower:
                ctx_size = ctx_value
                break
        
        print(f"🤖 Initialisiere ChatOllama mit Modell: {_model} (ctx_size={ctx_size}, temperature={settings.TEMPERATURE})")
        
        return ChatOllama(
            model=_model,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
            num_ctx=ctx_size,
            timeout=settings.REQUEST_TIMEOUT,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )


# ============================================================================
# TOOL PARAMETER SPECIFICATIONS
# ============================================================================

TOOL_SPECS = {
    "klips2_register": {
        "description": "KLIPS2-Account erstellen",
        "required_params": {
            "vorname": "Vorname der Person",
            "nachname": "Nachname der Person",
            "geschlecht": "männlich, weiblich oder divers",
            "geburtsdatum": "Geburtsdatum im Format TT.MM.JJJJ",
            "email": "E-Mail-Adresse mit @",
            "staatsangehoerigkeit": "Staatsangehörigkeit"
        },
        "optional_params": {
            "geburtsname": "Geburtsname falls abweichend vom Nachnamen",
            "sprache": "Deutsch oder Englisch (Standard: Deutsch)"
        }
    },
    "klips2_apply_study": {
        "description": "Studienbewerbung einreichen",
        "required_params": {
            "username": "KLIPS2-Benutzername",
            "password": "KLIPS2-Passwort",
            "semester": "Zielsemester (z.B. Wintersemester 2024/25, WS 2024)",
            "degree_type": "Bachelor, Master oder Promotion",
            "study_program": "Name des Studiengangs (z.B. Informatik, Medizin)",
            "gender": "Geschlecht (männlich, weiblich, divers)",
            "birth_place": "Geburtsort",
            "nationality": "Staatsangehörigkeit",
            "hzb_date": "Datum der Hochschulzugangsberechtigung (z.B. 15.06.2018)",
            "hzb_type": "Art der HZB (z.B. Abitur, Fachhochschulreife)",
            "hzb_name": "Bezeichnung des Zeugnisses (z.B. Allgemeine Hochschulreife)",
            "hzb_grade": "Note der HZB (z.B. 2,3 oder 2.3)",
            "hzb_school": "Name der Schule",
            "hzb_place": "Ort der HZB"
        },
        "optional_params": {
            "entry_semester": "Fachsemester (Standard: 1)",
            "study_form": "Erststudium oder Zweitstudium (Standard: Erststudium)",
            "birth_country": "Geburtsland (Standard: Deutschland)",
            "hzb_country": "Land der HZB (Standard: Deutschland)",
            "street": "Straße und Hausnummer",
            "zip_code": "Postleitzahl",
            "city": "Stadt",
            "country": "Land (Standard: Deutschland)"
        }
    },
    "klips2_change_address": {
        "description": "KLIPS2-Adresse ändern",
        "required_params": {
            "username": "KLIPS2-Benutzername",
            "password": "KLIPS2-Passwort",
            "street": "Straße und Hausnummer",
            "zip_code": "Postleitzahl",
            "city": "Stadt (MUSS explizit genannt werden!)"
        },
        "optional_params": {
            "country": "Land (Standard: Deutschland)"
        }
    },
    "klips2_change_password": {
        "description": "KLIPS2-Passwort ändern",
        "required_params": {
            "username": "KLIPS2-Benutzername",
            "password": "Aktuelles Passwort",
            "new_password": "Neues Passwort"
        },
        "optional_params": {}
    },
    "klips2_get_course_details": {
        "description": "Kursdetails aus KLIPS2 abrufen",
        "required_params": {
            "course_id": "Kursnummer (z.B. 14302.0001)"
        },
        "optional_params": {
            "semester": "Semester (z.B. WS 2024/25)"
        }
    },
    "send_email": {
        "description": "E-Mail senden",
        "required_params": {
            "subject": "Betreff der E-Mail",
            "body": "Text der E-Mail"
        },
        "optional_params": {
            "to": "Empfänger-Adresse (Standard: Studierendensekretariat)"
        }
    },
    "university_knowledge_search": {
        "description": "Universitäts-Wissensdatenbank durchsuchen",
        "required_params": {
            "query": "Suchanfrage zur Universität"
        },
        "optional_params": {}
    },
    "duckduckgo_search": {
        "description": "Internet-Suche mit DuckDuckGo",
        "required_params": {
            "query": "Suchanfrage für Internet-Suche"
        },
        "optional_params": {}
    },
    "web_scraper": {
        "description": "Webseite scrapen",
        "required_params": {
            "url": "URL der Webseite"
        },
        "optional_params": {}
    }
}


class ReactAgent:
    """Autonomer React Agent mit LangGraph und Ollama oder OpenAI"""
    
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
        
        # Initialisiere LLM (Ollama oder OpenAI basierend auf settings.LLM_PROVIDER)
        self.llm = create_llm()
        
        # Initialisiere Tools (einschließlich E-Mail-Tool)
        self.tools = self._create_tools()
        
        # System-Prompt mit detaillierten Tool-Spezifikationen
        system_prompt = self._get_system_prompt()
        
        # Erstelle React Agent
        self.agent = create_langgraph_agent(
            self.llm,
            self.tools
        )
        
        # Konfiguriere Recursion Limit für Agent
        self.recursion_limit = getattr(settings, 'AGENT_RECURSION_LIMIT', 25)
        
        # Speichere System-Prompt als SystemMessage für Memory
        self.system_message = SystemMessage(content=system_prompt)
        
        # Memory für Konversationshistorie
        self.memory = []
    
    def _get_system_prompt(self) -> str:
        """Erstelle den System-Prompt mit detaillierten Tool-Spezifikationen."""
        
        # Formatiere Tool-Spezifikationen
        tools_info = []
        for tool_name, spec in TOOL_SPECS.items():
            info = f"\n### {tool_name}\n"
            info += f"**Beschreibung:** {spec['description']}\n\n"
            
            if spec['required_params']:
                info += "**PFLICHTPARAMETER** (müssen ALLE vorhanden sein):\n"
                for param, desc in spec['required_params'].items():
                    info += f"  - `{param}`: {desc}\n"
                info += "\n"
            
            if spec['optional_params']:
                info += "**OPTIONALE PARAMETER** (können fehlen):\n"
                for param, desc in spec['optional_params'].items():
                    info += f"  - `{param}`: {desc}\n"
                info += "\n"
            
            tools_info.append(info)
        
        tools_spec_text = "".join(tools_info)
        
        return f"""Du bist ein KI-Assistent für KLIPS 2.0, das Campus-Management-System der Universität zu Köln.

## VERFÜGBARE TOOLS MIT EXAKTEN PARAMETER-ANFORDERUNGEN

{tools_spec_text}

## WANN EIN TOOL AUFRUFEN?

✅ Tool aufrufen bei:
- KLIPS2-Aktionen: Wenn ALLE Pflichtparameter vorhanden sind
- Wissensfragen zur Universität → university_knowledge_search
- Explizite Internet-Suche ("Suche im Internet", "Search for") → duckduckgo_search
- URL genannt → web_scraper
- E-Mail senden gewünscht → send_email (mit Betreff und Text)

❌ KEIN Tool bei:
- Begrüßungen ("Hallo!", "Wie geht's?")
- Fragen über dich selbst ("Was kannst du?")
- Einfache Rechenaufgaben, Übersetzungen
- Allgemeine Wissensfragen ohne Uni-Bezug
- **UNVOLLSTÄNDIGE Daten**: Wenn Pflichtparameter fehlen → FRAGE NACH, rufe KEIN Tool auf

## PARAMETER-EXTRAKTION

Extrahiere Parameter GROSSZÜGIG aus dem Text:
- "Ich bin Max Müller" → vorname="Max", nachname="Müller"
- "geboren am 15.03.1999" → geburtsdatum="15.03.1999"
- "männlich" / "male" / "m" → geschlecht="männlich"
- "Abitur 2018 Note 2,3" → hzb_type="Abitur", hzb_date="2018", hzb_grade="2.3"
- "Musterstraße 1, 50678 Köln" → street="Musterstraße 1", zip_code="50678", city="Köln"

**Format-Variationen sind OK:**
- Geschlecht: "m"/"männlich"/"male" → "männlich"
- Datum: "15.06.2018" / "15/06/2018" / "2018-06-15" → akzeptabel
- Note: "2,3" / "2.3" → beide OK

## PFLICHTFELD-CHECK

Vor JEDEM Tool-Aufruf:
1. ✅ Sind ALLE Pflichtparameter vorhanden?
2. ✅ Haben die Parameter plausible Werte (keine Platzhalter wie "TBD", "N/A")?
3. ✅ Passen die Daten zum Tool-Zweck?

**Wenn Pflichtparameter fehlen:**
- Nenne KONKRET welche Parameter fehlen
- Beispiel: "Für die Registrierung benötige ich noch: Geburtsdatum und E-Mail-Adresse"
- Rufe KEIN Tool auf mit unvollständigen Daten!

## MULTI-STEP KONVERSATIONEN

Wenn im Prompt "Previous conversation:" steht:
1. Analysiere ALLE Informationen aus vorherigen Nachrichten
2. Kombiniere sie mit der aktuellen Nachricht
3. Wenn dadurch ALLE Pflichtparameter vorhanden sind → Tool aufrufen

## MULTI-TOOL-ANFRAGEN (WICHTIG!)

**Wenn der User MEHRERE Aktionen in EINER Nachricht fordert:**
- "Suche X **und dann** hole Y" → BEIDE Tools aufrufen: [duckduckgo_search, klips2_get_course_details]
- "Hole Kursdetails **und schicke** E-Mail" → BEIDE Tools aufrufen: [klips2_get_course_details, send_email]
- "Recherchiere X, **dann** Details zu Y" → BEIDE Tools aufrufen: [duckduckgo_search, klips2_get_course_details]

Signalwörter für Multi-Tool:
- "und dann", "danach", "anschließend", "then"
- "und schicke", "und sende", "and send"
- Mehrere Aktionsverben in einer Anfrage

**REGEL:** Bei Multi-Tool-Anfragen → ALLE relevanten Tools aufrufen!

## BEISPIELE

✅ RICHTIG: "Registriere Max Müller, männlich, 01.01.2000, max@test.de, deutsch"
   → 6/6 Pflichtparameter → klips2_register AUFRUFEN

❌ FALSCH: "Registriere Max Müller"
   → Nur 2/6 Parameter → NACHFRAGEN statt Tool aufrufen

Antworte in der Sprache des Nutzers."""
    
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
            config = {
                "recursion_limit": self.recursion_limit
            }
            
            if settings.LANGSMITH_TRACING:
                config["metadata"] = {
                    "session_id": session_id,
                    "user_message": message[:100] + "..." if len(message) > 100 else message,
                    "available_tools": len(self.tools)
                }

            response = self.agent.invoke(agent_input, config=config)
            
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
    
    def get_tool_selection(self, message: str) -> List[Dict[str, Any]]:
        """
        Ermittle Tool-Auswahl ohne Ausführung (für Evaluierung).
        
        Diese Methode ruft das LLM mit gebundenen Tools auf und
        extrahiert die Tool-Calls, ohne sie auszuführen.
        
        Args:
            message: Die Nutzeranfrage
            
        Returns:
            Liste der ausgewählten Tool-Calls
        """
        try:
            # LLM mit gebundenen Tools
            llm_with_tools = self.llm.bind_tools(self.tools)
            
            # Message-Liste erstellen
            messages = [
                self.system_message,
                HumanMessage(content=message)
            ]
            
            # LLM aufrufen um Tool-Auswahl zu bekommen (OHNE Ausführung)
            response = llm_with_tools.invoke(messages)
            
            # Tool-Calls extrahieren
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append({
                        "name": tc.get("name", ""),
                        "args": tc.get("args", {})
                    })
            
            return tool_calls
            
        except Exception as e:
            return []  # Bei Fehler keine Tool-Auswahl

def create_react_agent() -> ReactAgent:
    """Factory-Funktion für den React Agent"""
    return ReactAgent()