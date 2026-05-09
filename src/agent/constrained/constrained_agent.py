"""
Constrained Agent - Agent mit Schema-beschränkter Generierung.

Dieser Agent verwendet strukturierte Output-Generierung um sicherzustellen,
dass Tool-Calls immer syntaktisch korrekt sind:

1. Verwendet Ollama's JSON-Modus für garantiert valides JSON
2. Definiert explizite Pydantic-Schemas für jedes Tool
3. Validiert Ausgaben gegen Schemas vor Ausführung
4. Repariert automatisch kleine Formatfehler

Unterschied zu Confirmation Agent:
- Confirmation: Prüft NACH Generierung ob Werte semantisch korrekt sind
- Constrained: Erzwingt WÄHREND Generierung syntaktisch korrekte Struktur

Basierend auf: LMQL (Beurer-Kellner et al., 2022) - Constrained Decoding
"""

import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, ValidationError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from config.logging_config import get_logger
from config.settings import settings
from src.agent.agent_config import setup_langsmith_tracing, get_recursion_limit
from src.agent.llm_factory import create_llm, create_json_llm
from src.agent.tool_loader import load_tool_safely, load_klips_tools
from src.agent.constrained.schemas import (
    ToolDecision, DirectResponse, TOOL_SCHEMAS,
    RegisterToolCall, ApplyToolCall, ChangeAddressToolCall,
    ChangePasswordToolCall, CourseDetailsToolCall,
    SearchToolCall, WebScraperToolCall, EmailToolCall,
)
from src.agent.constrained.prompts import (
    get_system_prompt, get_decision_prompt, get_extraction_prompt
)
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


logger = get_logger(__name__)


class ConstrainedAgent:
    """
    Agent mit Schema-beschränkter Generierung.
    
    Verwendet einen zweistufigen Prozess:
    1. Entscheidung: Tool oder direkte Antwort? (mit ToolDecision Schema)
    2. Ausführung: Tool-Argumente oder Antwort generieren (mit entsprechendem Schema)
    
    Vorteile:
    - Garantiert syntaktisch korrektes JSON
    - Keine Tippfehler in Feldnamen
    - Automatische Typ-Konvertierung
    - Automatische Format-Normalisierung (Datum, Geschlecht, etc.)
    """
    
    def __init__(self):
        """Initialisiere den Constrained Agent."""
        settings.validate()
        
        # LangSmith Tracing
        setup_langsmith_tracing()
        
        logger.info(f"📐 Initialisiere Constrained Agent mit Modell: {settings.OLLAMA_MODEL}")
        
        # LLM für Entscheidungen (ohne JSON-Mode für natürliche Antworten)
        self.llm = create_llm()
        
        # LLM mit JSON-Mode für strukturierte Ausgaben
        self.llm_json = create_json_llm()
        
        # Tools initialisieren
        self.tools = self._create_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # System message für Kompatibilität mit Evaluation Harness
        self.system_message = SystemMessage(content=self._get_system_prompt())
        
        # Recursion Limit from centralized config
        self.recursion_limit = get_recursion_limit("constrained")
        
        # Memory
        self.memory: List[Union[HumanMessage, AIMessage]] = []
        
        # Tracking
        self.schema_validations = 0
        self.schema_repairs = 0
        self.schema_failures = 0
        
        # Conversation Trace für Debugging/Evaluation
        self.conversation_trace = []
    
    def _get_system_prompt(self) -> str:
        """Kompakter System-Prompt für Constrained Agent."""
        available_tool_names = {tool.name for tool in self.tools}
        return get_system_prompt(available_tool_names)
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools."""
        tools = []
        
        if settings.ENABLE_WEB_SCRAPER:
            web_tool = load_tool_safely(create_web_scraper_tool, "Web-Scraper")
            if web_tool:
                tools.append(web_tool)
        
        if settings.ENABLE_DUCKDUCKGO:
            ddg_tool = load_tool_safely(create_duckduckgo_tool, "DuckDuckGo")
            if ddg_tool:
                tools.append(ddg_tool)
        
        rag_tool = load_tool_safely(create_university_rag_tool, "Universitäts-RAG") if settings.ENABLE_RAG_TOOL else None
        if rag_tool:
            tools.append(rag_tool)
        
        if settings.ENABLE_EMAIL:
            email_tool = load_tool_safely(create_email_tool, "E-Mail")
            if email_tool:
                tools.append(email_tool)
        
        if settings.ENABLE_KLIPS:
            klips_tools = load_klips_tools()
            tools.extend(klips_tools)
        
        return tools
    
    def _get_decision_prompt(self) -> str:
        """Prompt für die Tool-Entscheidung mit expliziten Anforderungen."""
        available_tool_names = {tool.name for tool in self.tools}
        return get_decision_prompt(available_tool_names)
    
    def _get_extraction_prompt(self, tool_name: str, schema: Type[BaseModel]) -> str:
        """Prompt für die Argument-Extraktion."""
        return get_extraction_prompt(tool_name, schema)
    
    def _parse_and_validate(
        self,
        json_str: str,
        schema: Type[BaseModel],
    ) -> tuple[Optional[BaseModel], Optional[str]]:
        """
        Parse JSON und validiere gegen Schema.

        Passes source_text as context so ToolCallBase can repair umlaut
        corruption introduced by the Ollama tokenizer.

        Returns:
            (validated_model, None) bei Erfolg
            (None, error_message) bei Fehler
        """
        self.schema_validations += 1

        # 1. JSON parsen
        try:
            # Bereinige JSON (entferne Markdown-Blöcke falls vorhanden)
            json_str = json_str.strip()
            if json_str.startswith("```"):
                json_str = re.sub(r'^```(?:json)?\n?', '', json_str)
                json_str = re.sub(r'\n?```$', '', json_str)

            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Versuche Reparatur
            repaired = self._repair_json(json_str)
            if repaired:
                self.schema_repairs += 1
                data = repaired
            else:
                self.schema_failures += 1
                return None, f"JSON-Parse-Fehler: {e}"

        # 2. Gegen Schema validieren
        try:
            validated = schema.model_validate(data)
            return validated, None
        except ValidationError as e:
            self.schema_failures += 1
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return None, f"Validierungsfehler: {'; '.join(errors)}"
    
    def _repair_json(self, json_str: str) -> Optional[Dict]:
        """Versuche häufige JSON-Fehler zu reparieren."""
        # Entferne Trailing Commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Füge fehlende Quotes um Keys hinzu
        json_str = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        # Ersetze single quotes durch double quotes
        # (vorsichtig - nur wenn nicht innerhalb eines strings)
        json_str = json_str.replace("'", '"')
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Führe Tool mit validierten Argumenten aus."""
        tool = self.tool_map.get(tool_name)
        if not tool:
            return f"Fehler: Tool '{tool_name}' nicht gefunden"
        
        try:
            result = tool.invoke(args)
            return result
        except Exception as e:
            return f"Fehler bei Tool-Ausführung: {str(e)}"
    
    def chat(self, message: str, session_id: str = None) -> str:
        """
        Führe eine Unterhaltung mit dem Constrained Agent.
        
        Prozess:
        1. Entscheide ob Tool oder direkte Antwort (mit Schema)
        2. Bei Tool: Extrahiere Argumente (mit Schema)
        3. Validiere gegen Pydantic-Schema
        4. Führe Tool aus oder gib Antwort
        """
        try:
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            human_message = HumanMessage(
                content=message,
                additional_kwargs={"session_id": session_id},
            )
            self.memory.append(human_message)
            
            if len(self.memory) > settings.MEMORY_SIZE:
                self.memory = self.memory[-settings.MEMORY_SIZE:]
            
            # Erstelle erweiterten Kontext mit vorherigen Nachrichten
            context_messages = []
            if len(self.memory) > 1:
                # Inkludiere letzte 3 Nachrichtenpaare für Kontext
                prev_context = []
                for msg in self.memory[-7:-1]:  # Letzte 6 Nachrichten (ohne die aktuelle)
                    if isinstance(msg, HumanMessage):
                        prev_context.append(f"User: {msg.content}")
                    elif isinstance(msg, AIMessage):
                        prev_context.append(f"Assistant: {msg.content}")
                
                if prev_context:
                    context_str = "\n".join(prev_context)
                    enriched_message = f"Previous conversation:\n{context_str}\n\nCurrent message:\n{message}"
                else:
                    enriched_message = message
            else:
                enriched_message = message
            
            # Schritt 1: Entscheidung (mit erweitertem Kontext)
            decision_prompt = self._get_decision_prompt()
            decision_messages = [
                SystemMessage(content=decision_prompt),
                HumanMessage(content=enriched_message)
            ]
            
            decision_response = self.llm_json.invoke(decision_messages)
            decision_result, error = self._parse_and_validate(
                decision_response.content, 
                ToolDecision
            )
            
            if error or not decision_result:
                # Fallback: Direkte Antwort generieren
                response_text = self._generate_fallback_response(message)
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
            # Schritt 2: Prüfe auf fehlende Daten
            if decision_result.action == "insufficient_data":
                # Fehlende Pflichtfelder → Nachfragen
                missing = decision_result.missing_fields or []
                field_names = ", ".join(missing)
                response_text = f"Um fortzufahren, benötige ich noch folgende Informationen: {field_names}. Bitte ergänze diese Angaben."
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
            # Schritt 3: Action ausführen
            if decision_result.action == "respond":
                # Direkte Antwort generieren
                response_text = self._generate_direct_response(message)
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
            # Schritt 4: Tool-Argumente extrahieren (mit erweitertem Kontext)
            tool_names = decision_result.tool_names
            if not tool_names:
                response_text = "Keine Tools identifiziert."
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
            # Multi-Tool: Verarbeite alle Tools sequentiell
            all_results = []
            for tool_name in tool_names:
                if tool_name not in TOOL_SCHEMAS:
                    all_results.append(f"Unbekanntes Tool: {tool_name}")
                    continue
                
                schema = TOOL_SCHEMAS[tool_name]
                extraction_prompt = self._get_extraction_prompt(tool_name, schema)
                
                extraction_messages = [
                    SystemMessage(content=extraction_prompt),
                    HumanMessage(content=f"Nutzertext (mit Kontext):\n{enriched_message}")
                ]
                
                extraction_response = self.llm_json.invoke(extraction_messages)
                validated_args, error = self._parse_and_validate(
                    extraction_response.content,
                    schema,
                )

                if error:
                    # Retry: Gebe Feedback und eine weitere Chance
                    retry_prompt = f"""Die vorherige JSON-Generierung hatte Fehler:
{error}

Bitte korrigiere die Fehler und generiere das JSON erneut.
Nur die fehlenden/fehlerhaften Felder müssen korrigiert werden.

Ursprünglicher Nutzertext: {enriched_message}"""
                    
                    retry_messages = [
                        SystemMessage(content=extraction_prompt),
                        HumanMessage(content=f"Nutzertext (mit Kontext):\n{enriched_message}"),
                        AIMessage(content=extraction_response.content),
                        HumanMessage(content=retry_prompt)
                    ]
                    
                    retry_response = self.llm_json.invoke(retry_messages)
                    validated_args_retry, error_retry = self._parse_and_validate(
                        retry_response.content,
                        schema,
                    )
                    
                    if error_retry:
                        # Auch nach Retry fehlgeschlagen
                        all_results.append(f"{tool_name}: Fehler bei Datenverarbeitung: {error_retry}")
                        continue
                    
                    # Retry erfolgreich
                    validated_args = validated_args_retry
                
                # Schritt 5: Tool ausführen
                args_dict = validated_args.model_dump(exclude_none=True)
                tool_result = self._execute_tool(tool_name, args_dict)
                all_results.append(self._format_tool_response(tool_name, tool_result))
            
            # Schritt 6: Kombiniere alle Ergebnisse
            if not all_results:
                response_text = "Keine Tools konnten erfolgreich ausgeführt werden."
            elif len(all_results) == 1:
                response_text = all_results[0]
            else:
                response_text = "\n\n---\n\n".join(all_results)
            
            # Safety check: Ensure we never return raw JSON to users
            if response_text.strip().startswith('{') and '"action"' in response_text:
                response_text = "Entschuldigung, ich hatte ein technisches Problem. Bitte formulieren Sie Ihre Frage erneut."
            
            self.memory.append(AIMessage(content=response_text))
            return response_text
            
        except Exception as e:
            error_msg = f"Fehler: {str(e)}"
            self.memory.append(AIMessage(content=error_msg))
            return error_msg
    
    def _generate_direct_response(self, message: str) -> str:
        """Generiere direkte Antwort ohne Tool."""
        prompt = """Du bist ein hilfreicher Assistent für KLIPS 2.0.
Beantworte die Frage direkt und präzise.
Falls Informationen für einen Tool-Aufruf fehlen, frage gezielt nach."""
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=message)
        ]
        
        response = self.llm.invoke(messages)
        return response.content
    
    def _synthesize_rag_response(self, rag_result: str) -> str:
        """Synthesiere RAG-Ergebnisse in eine kohärente Antwort.
        
        Args:
            rag_result: Rohe RAG-Tool-Ausgabe mit Context-Chunks
            
        Returns:
            Natürliche, kohärente Antwort basierend auf dem RAG-Kontext
        """
        # Wenn RAG-Tool keine Ergebnisse fand
        if "Keine relevanten Informationen" in rag_result or "❌" in rag_result:
            return rag_result
        
        # Hole die letzte User-Nachricht für Kontext
        last_user_message = ""
        for msg in reversed(self.memory):
            if isinstance(msg, HumanMessage):
                last_user_message = msg.content
                break
        
        synthesis_prompt = f"""Du bist ein hilfreicher Universitäts-Assistent. 

Die folgende Frage wurde gestellt:
{last_user_message}

Hierzu wurden folgende Informationen aus der Wissensdatenbank abgerufen:
{rag_result}

Aufgabe: Beantworte die Frage präzise und natürlich basierend auf den abgerufenen Informationen.

REGELN:
1. Formuliere eine direkte, kohärente Antwort (NICHT "Laut Wissensdatenbank...")  
2. Integriere die relevanten Informationen nahtlos
3. Behalte wichtige Details bei (Zahlen, Namen, Anforderungen)
4. Strukturiere die Antwort übersichtlich (Absätze, Aufzählungen wenn sinnvoll)
5. Vermeide Redundanzen
6. Schreibe NICHT die ursprüngliche Frage oder Einleitungen wie "Die Antwort ist:"

Antworte direkt und natürlich:"""
        
        try:
            messages = [
                SystemMessage(content=synthesis_prompt)
            ]
            response = self.llm.invoke(messages)
            synthesized = response.content.strip()
            
            # Entferne mögliche Meta-Sätze die das LLM trotzdem hinzufügt
            patterns_to_remove = [
                r"^(Basierend auf|Laut|Gemäß|Nach) (den|der) (abgerufenen )?Informationen[^.]*[.:]\s*",
                r"^Die Antwort (lautet|ist)[^.]*[.:]\s*",
                r"^Hier ist die Antwort[^.]*[.:]\s*",
            ]
            
            for pattern in patterns_to_remove:
                synthesized = re.sub(pattern, "", synthesized, flags=re.IGNORECASE)
            
            return synthesized.strip()
            
        except Exception as e:
            logger.error(f"Fehler bei RAG-Synthese: {e}", exc_info=True)
            # Fallback: Gebe RAG-Ergebnis direkt zurück
            return rag_result
    
    def _generate_fallback_response(self, message: str) -> str:
        """Fallback wenn Entscheidung nicht geparst werden konnte."""
        return self._generate_direct_response(message)
    
    def _format_tool_response(self, tool_name: str, result: str) -> str:
        """Formatiere Tool-Ergebnis für Nutzer."""
        # Für RAG-Tool: Synthesiere Antwort aus Kontext
        if tool_name == "university_knowledge_search":
            return self._synthesize_rag_response(result)
        
        # Für andere Tools: Standard-Formatierung
        tool_descriptions = {
            "klips2_register": "KLIPS2-Registrierung",
            "klips2_apply_study": "Studienbewerbung",
            "klips2_change_address": "Adressänderung",
            "klips2_change_password": "Passwortänderung",
            "klips2_get_course_details": "Kursdetails",
            "duckduckgo_search": "Web-Suche",
            "web_scraper": "Webseiten-Inhalt",
            "send_email": "E-Mail-Versand",
        }
        
        desc = tool_descriptions.get(tool_name, tool_name)
        return f"{desc}:\n\n{result}"
    
    def get_available_tools(self) -> List[str]:
        """Gebe Liste der verfügbaren Tools zurück."""
        return [tool.name for tool in self.tools]
    
    def clear_memory(self):
        """Lösche Konversationshistorie."""
        self.memory = []
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Gebe eine Zusammenfassung des aktuellen Konversationsspeichers zurück.

        Rückgabeformat ist kompatibel zu anderen Agenten:
        - total_messages: Gesamtanzahl aller Nachrichten
        - human_messages: Anzahl der HumanMessage-Nachrichten
        - ai_messages: Anzahl der AIMessage-Nachrichten
        - last_messages: Liste der letzten Nachrichten (max. 5) als einfache Dicts
        """
        messages = self.memory

        total_messages = len(messages)
        human_messages = sum(1 for m in messages if isinstance(m, HumanMessage))
        ai_messages = sum(1 for m in messages if isinstance(m, AIMessage))

        # Formatiere die letzten Nachrichten in ein einfaches, serialisierbares Format
        last_raw = messages[-5:] if total_messages > 5 else messages
        last_messages: List[Dict[str, Any]] = []
        for m in last_raw:
            # Versuche, Rolle/Typ und Inhalt möglichst konsistent zu extrahieren
            role: str
            if isinstance(m, HumanMessage):
                role = "human"
            elif isinstance(m, AIMessage):
                role = "ai"
            elif isinstance(m, SystemMessage):
                role = "system"
            else:
                role = getattr(m, "type", "unknown")

            content = getattr(m, "content", None)
            last_messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return {
            "total_messages": total_messages,
            "human_messages": human_messages,
            "ai_messages": ai_messages,
            "last_messages": last_messages,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Gebe Statistiken über Schema-Validierungen zurück."""
        return {
            "total_validations": self.schema_validations,
            "repairs": self.schema_repairs,
            "failures": self.schema_failures,
            "success_rate": (
                (self.schema_validations - self.schema_failures) / self.schema_validations
                if self.schema_validations > 0 else 0
            )
        }
    
    def get_conversation_trace(self) -> List[Dict[str, Any]]:
        """Gebe den kompletten Conversation-Trace zurück."""
        return self.conversation_trace
    
    def clear_conversation_trace(self):
        """Lösche den Conversation-Trace."""
        self.conversation_trace = []
    
    def save_conversation_trace(self, filepath: str):
        """
        Speichere den Conversation-Trace als JSON-Datei.
        
        Args:
            filepath: Pfad zur Ausgabedatei
        """
        from pathlib import Path
        
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_trace, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Conversation-Trace gespeichert: {output_path}")
    
    def get_tool_selection(self, message: str, enable_trace: bool = False, max_retries: int = 1) -> List[Dict[str, Any]]:
        """
        Ermittle Tool-Auswahl mit Constrained-Decoding-Logik (für Evaluierung).
        
        Diese Methode führt die spezifische Constrained-Agent-Logik durch:
        1. Entscheidung ob Tool oder direkte Antwort (mit JSON-Mode)
        2. Argument-Extraktion mit Pydantic-Schema-Validierung
        3. Bei Validierungsfehlern: Retry mit Feedback (max_retries Versuche)
        
        Args:
            message: Die Nutzeranfrage
            enable_trace: Wenn True, wird der Conversation-Trace aufgezeichnet
            max_retries: Maximale Anzahl an Versuchen bei Validierungsfehlern (Standard: 2)
            
        Returns:
            Liste der ausgewählten Tool-Calls mit validierten Argumenten
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        try:
            human_message = HumanMessage(content=message)
            
            # Schritt 1: Entscheidung mit JSON-Mode LLM
            decision_prompt = self._get_decision_prompt()
            decision_messages = [
                SystemMessage(content=decision_prompt),
                human_message
            ]
            
            decision_response = self.llm_json.invoke(decision_messages)
            
            # Log Step 1: Decision (optional)
            if enable_trace:
                trace_step = {
                    "step": "decision",
                    "scenario": message,
                    "prompt": decision_prompt,
                    "raw_output": decision_response.content,
                    "timestamp": datetime.now().isoformat()
                }
            
            decision_result, error = self._parse_and_validate(
                decision_response.content, 
                ToolDecision
            )
            
            if enable_trace:
                trace_step["validation_success"] = error is None
                trace_step["validation_error"] = error
                trace_step["parsed_result"] = decision_result.model_dump() if decision_result else None
                self.conversation_trace.append(trace_step)
            
            if error or not decision_result:
                return []  # Keine Tool-Auswahl möglich
            
            # Check for insufficient data: retry once with explicit hint
            if decision_result.action == "insufficient_data":
                identified_tool = (decision_result.tool_names or [None])[0]
                # No-required-fields tools (e.g. send_email) should never be insufficient_data
                no_required = {
                    "send_email", "university_knowledge_search", "duckduckgo_search",
                    "web_scraper", "klips2_get_course_details",
                }
                if identified_tool in no_required:
                    missing = decision_result.missing_fields or []
                    retry_hint = (
                        f"Deine vorherige Entscheidung war 'insufficient_data' mit fehlenden Feldern {missing}. "
                        f"Bitte entscheide erneut. Antworte nur im JSON-Format."
                    )
                    retry_decision_msgs = [
                        SystemMessage(content=decision_prompt),
                        HumanMessage(content=message),
                        AIMessage(content=decision_response.content),
                        HumanMessage(content=retry_hint),
                    ]
                    retry_decision_response = self.llm_json.invoke(retry_decision_msgs)
                    retry_decision_result, retry_err = self._parse_and_validate(
                        retry_decision_response.content, ToolDecision
                    )
                    if not retry_err and retry_decision_result and retry_decision_result.action == "tool":
                        decision_result = retry_decision_result
                    else:
                        return []  # Still wrong after retry
                else:
                    return []  # Fehlende Daten → kein Tool-Call
            
            # Also retry if model said 'respond' but message clearly contains email keywords
            # (sub-second failures indicate model skipped the tool entirely)
            if decision_result.action == "respond":
                available_tool_names = {tool.name for tool in self.tools}
                email_keywords = (
                    "send_email" in available_tool_names and any(
                        kw in message.lower() for kw in [
                            "e-mail", "email", "mail", "sende", "schicke", "schreibe",
                            "verfasse", "nachricht", "send", "write",
                        ]
                    )
                )
                if email_keywords:
                    retry_hint = (
                        "Deine vorherige Entscheidung war 'respond', aber die Nachricht enthält "
                        "eindeutige E-Mail-Signalwörter. Das Tool 'send_email' hat PFLICHT: keine "
                        "und kann immer aufgerufen werden. Bitte entscheide erneut: "
                        "action='tool', tool_names=['send_email']. Antworte nur im JSON-Format."
                    )
                    retry_decision_msgs = [
                        SystemMessage(content=decision_prompt),
                        HumanMessage(content=message),
                        AIMessage(content=decision_response.content),
                        HumanMessage(content=retry_hint),
                    ]
                    retry_decision_response = self.llm_json.invoke(retry_decision_msgs)
                    retry_decision_result, retry_err = self._parse_and_validate(
                        retry_decision_response.content, ToolDecision
                    )
                    if not retry_err and retry_decision_result and retry_decision_result.action == "tool":
                        decision_result = retry_decision_result
                    else:
                        return []  # Still wrong after retry
                else:
                    return []  # Direkte Antwort, kein Tool
            
            # Schritt 2: Tool-Argumente mit Schema extrahieren (Multi-Tool Support)
            tool_names = decision_result.tool_names
            if not tool_names:
                return []  # Keine Tools identifiziert
            
            # Multi-Tool: Verarbeite alle Tools sequentiell
            all_tool_calls = []
            for tool_name in tool_names:
                if tool_name not in TOOL_SCHEMAS:
                    if enable_trace:
                        trace_step = {
                            "step": "error",
                            "tool_name": tool_name,
                            "scenario": message,
                            "error": f"Unknown tool: {tool_name}",
                            "timestamp": datetime.now().isoformat()
                        }
                        self.conversation_trace.append(trace_step)
                    continue  # Skip unbekanntes Tool
                
                schema = TOOL_SCHEMAS[tool_name]
                extraction_prompt = self._get_extraction_prompt(tool_name, schema)
                
                extraction_messages = [
                    SystemMessage(content=extraction_prompt),
                    HumanMessage(content=f"Nutzertext: {message}")
                ]
                
                extraction_response = self.llm_json.invoke(extraction_messages)
                
                # Log Step 2: Initial Extraction (optional)
                if enable_trace:
                    trace_step = {
                        "step": "extraction_initial",
                        "tool_name": tool_name,
                        "scenario": message,
                        "prompt": extraction_prompt,
                        "raw_output": extraction_response.content,
                        "timestamp": datetime.now().isoformat()
                    }
                
                validated_args, error = self._parse_and_validate(
                    extraction_response.content,
                    schema
                )
                
                if enable_trace:
                    trace_step["validation_success"] = error is None
                    trace_step["validation_error"] = error
                    trace_step["parsed_result"] = validated_args.model_dump() if validated_args else None
                    self.conversation_trace.append(trace_step)
                
                # Erfolg beim ersten Versuch
                if not error:
                    args_dict = validated_args.model_dump(exclude_none=True)
                    if enable_trace:
                        final_step = {
                            "step": "final_result",
                            "tool_name": tool_name,
                            "scenario": message,
                            "status": "success_first_attempt",
                            "reason": "Schema-Validierung erfolgreich beim ersten Versuch",
                            "result": {"name": tool_name, "args": args_dict},
                            "timestamp": datetime.now().isoformat()
                        }
                        self.conversation_trace.append(final_step)
                    all_tool_calls.append({"name": tool_name, "args": args_dict})
                    continue  # Nächstes Tool
                
                # Bei Fehler: Retry-Schleife
                last_response = extraction_response.content
                last_error = error
                messages_history = extraction_messages.copy()
                
                for retry_num in range(max_retries):
                    retry_prompt = f"""Die vorherige JSON-Generierung hatte Fehler (Versuch {retry_num + 1}/{max_retries}):
{last_error}

Bitte korrigiere die Fehler und generiere das JSON erneut.
Nur die fehlenden/fehlerhaften Felder müssen korrigiert werden.

Ursprünglicher Nutzertext: {message}"""
                    
                    # History erweitern
                    messages_history.append(AIMessage(content=last_response))
                    messages_history.append(HumanMessage(content=retry_prompt))
                    
                    retry_response = self.llm_json.invoke(messages_history)
                    
                    # Log Retry (optional)
                    if enable_trace:
                        trace_step = {
                            "step": f"extraction_retry_{retry_num + 1}",
                            "tool_name": tool_name,
                            "scenario": message,
                            "previous_error": last_error,
                            "retry_prompt": retry_prompt,
                            "raw_output": retry_response.content,
                            "timestamp": datetime.now().isoformat()
                        }
                    
                    validated_args_retry, error_retry = self._parse_and_validate(
                        retry_response.content,
                        schema
                    )
                    
                    if enable_trace:
                        trace_step["validation_success"] = error_retry is None
                        trace_step["validation_error"] = error_retry
                        trace_step["parsed_result"] = validated_args_retry.model_dump() if validated_args_retry else None
                        self.conversation_trace.append(trace_step)
                    
                    # Erfolg nach Retry
                    if not error_retry:
                        args_dict = validated_args_retry.model_dump(exclude_none=True)
                        if enable_trace:
                            final_step = {
                                "step": "final_result",
                                "tool_name": tool_name,
                                "scenario": message,
                                "status": f"success_after_retry_{retry_num + 1}",
                                "reason": f"Schema-Validierung erfolgreich nach {retry_num + 1} Retry(s)",
                                "result": {"name": tool_name, "args": args_dict},
                                "timestamp": datetime.now().isoformat()
                            }
                            self.conversation_trace.append(final_step)
                        all_tool_calls.append({"name": tool_name, "args": args_dict})
                        break  # Retry erfolgreich, nächstes Tool
                    
                    # Update für nächste Iteration
                    last_response = retry_response.content
                    last_error = error_retry
                else:
                    # Alle Retries fehlgeschlagen für dieses Tool
                    if enable_trace:
                        final_step = {
                            "step": "final_result",
                            "tool_name": tool_name,
                            "scenario": message,
                            "status": f"failed_after_{max_retries}_retries",
                            "reason": f"Schema-Validierung fehlgeschlagen nach {max_retries} Retry(s)",
                            "initial_error": error,
                            "final_error": last_error,
                            "result": None,  # Kein Tool-Aufruf bei Validierungsfehler
                            "timestamp": datetime.now().isoformat()
                        }
                        self.conversation_trace.append(final_step)
                    # Tool wird übersprungen, fahre mit nächstem fort
            
            # Gebe alle erfolgreich verarbeiteten Tools zurück
            return all_tool_calls
            
        except Exception as e:
            if enable_trace:
                trace_step = {
                    "step": "error",
                    "scenario": message,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                self.conversation_trace.append(trace_step)
            return []  # Bei Fehler keine Tool-Auswahl


def create_constrained_agent() -> ConstrainedAgent:
    """Factory-Funktion für den Constrained Agent."""
    return ConstrainedAgent()
