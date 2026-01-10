"""
Orchestrator Agent - Supervisor-Agent für das Multi-Agent-System.

Der Orchestrator ist der zentrale Routing-Agent, der eingehende
Anfragen analysiert und an den passenden spezialisierten Agenten
weiterleitet.

Implementiert das Supervisor-Pattern mit State Management:
1. Empfängt Anfrage vom Nutzer
2. Analysiert die Anfrage mit historischem Kontext
3. Wählt den passenden spezialisierten Agenten (mit Confidence-Score)
4. Delegiert die Anfrage mit strukturiertem Kontext
5. Tracked Multi-Step Tasks
6. Gibt die Antwort zurück
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from config.settings import settings

from .base_agent import BaseSpecializedAgent
from .klips_agent import KlipsAgent
from .email_agent import EmailAgent
from .knowledge_agent import KnowledgeAgent
from .llm_utils import create_llm


@dataclass
class ToolCall:
    """Repräsentiert einen ausgeführten Tool-Aufruf."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    agent: Optional[str] = None


@dataclass
class TaskState:
    """
    Verwaltet den Zustand für Multi-Step Tasks.
    
    Ermöglicht dem Orchestrator, sich an vorherige Schritte zu erinnern
    und Kontext über mehrere Agent-Aufrufe hinweg zu erhalten.
    """
    completed_steps: List[ToolCall] = field(default_factory=list)
    current_step: Optional[str] = None
    user_context: Dict[str, Any] = field(default_factory=dict)
    last_agent: Optional[str] = None
    
    def add_step(self, tool_call: ToolCall):
        """Füge abgeschlossenen Schritt hinzu."""
        self.completed_steps.append(tool_call)
        self.last_agent = tool_call.agent
    
    def get_context_summary(self) -> str:
        """Erstelle Zusammenfassung bisheriger Schritte."""
        if not self.completed_steps:
            return ""
        
        summary = "Vorherige Aktionen:\n"
        for i, step in enumerate(self.completed_steps, 1):
            summary += f"{i}. {step.tool_name} von {step.agent}\n"
        return summary


@dataclass
class SharedContext:
    """
    Strukturierter Kontext der zwischen Agenten geteilt wird.
    
    Ersetzt den einfachen String-Kontext mit strukturierten Daten,
    die Agenten besser nutzen können.
    """
    conversation_history: List[Any] = field(default_factory=list)
    task_state: TaskState = field(default_factory=TaskState)
    user_info: Dict[str, Any] = field(default_factory=dict)
    routing_confidence: float = 1.0
    
    def to_context_string(self) -> str:
        """Konvertiere zu String für Agenten die noch keinen SharedContext unterstützen."""
        parts = []
        
        # Task State
        context_summary = self.task_state.get_context_summary()
        if context_summary:
            parts.append(context_summary)
        
        # User Info
        if self.user_info:
            parts.append(f"Nutzer-Info: {self.user_info}")
        
        return "\n".join(parts) if parts else ""


class RoutingDecision(BaseModel):
    """Schema für die Routing-Entscheidung des Orchestrators mit Confidence."""
    
    agent_name: str = Field(
        description="Name des gewählten Agenten: 'KLIPS-Agent', 'Email-Agent' oder 'Wissens-Agent'"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence-Score der Routing-Entscheidung (0.0-1.0)"
    )
    reasoning: str = Field(
        description="Kurze Begründung für die Wahl des Agenten"
    )
    fallback_agent: Optional[str] = Field(
        default=None,
        description="Alternativer Agent falls primäre Wahl fehlschlägt"
    )


class OrchestratorAgent:
    """
    Supervisor-Agent der das Routing zu spezialisierten Agenten übernimmt.
    
    Der Orchestrator analysiert jede Anfrage und entscheidet,
    welcher spezialisierte Agent am besten geeignet ist.
    """
    
    def __init__(self, use_adaptive_routing: bool = True, force_llm_routing: bool = False):
        """
        Initialisiere den Orchestrator mit allen spezialisierten Agenten.
        
        Args:
            use_adaptive_routing: Nutze modell-abhängige Routing-Strategien
            force_llm_routing: Erzwinge LLM-Routing (keine Keywords) für Evaluation-Konsistenz
        """
        print("🎭 Initialisiere Multi-Agent Orchestrator (Enhanced)...")
        
        # Validiere Einstellungen
        settings.validate()
        
        # Track last routed agent and response for evaluation
        self.last_routed_agent: Optional[str] = None
        self.last_agent_response: Optional[Dict[str, Any]] = None
        
        # Task State Management für Multi-Step Workflows
        self.task_state = TaskState()
        self.shared_context = SharedContext()
        
        # Routing configuration
        self.confidence_threshold = 0.7
        self.use_adaptive_routing = use_adaptive_routing
        self.force_llm_routing = force_llm_routing
        
        # LangSmith Tracing konfigurieren (falls aktiviert)
        if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            print(f"✅ LangSmith-Tracing aktiviert für Projekt: {settings.LANGSMITH_PROJECT}")
        
        # Shared LLM für alle Agenten (Ressourceneffizienz)
        self.shared_llm = create_llm(verbose=True)
        
        # Spezialisierte Agenten initialisieren
        self.agents: Dict[str, BaseSpecializedAgent] = {}
        self._initialize_agents()
        
        # Routing LLM (kann leichteres Modell sein)
        self.routing_llm = self.shared_llm
        
        # Memory für Konversationshistorie
        self.memory: List[Any] = []
        self._max_memory_size = settings.MEMORY_SIZE
        
        # Model-aware routing strategy
        if self.force_llm_routing:
            # Override strategy when forcing LLM routing
            self.routing_strategy = 'llm_only'
            print(f"🎯 Routing-Modus: LLM-only (keine Keywords) für Evaluation-Konsistenz")
        else:
            self.routing_strategy = self._determine_routing_strategy()
        
        print(f"🎭 Orchestrator bereit mit {len(self.agents)} spezialisierten Agenten")
        print(f"   ✅ State Management aktiviert")
        print(f"   ✅ Confidence Threshold: {self.confidence_threshold}")
    
    def _initialize_agents(self) -> None:
        """Initialisiere alle spezialisierten Agenten."""
        agent_classes: List[Type[BaseSpecializedAgent]] = [
            KlipsAgent,
            EmailAgent,
            KnowledgeAgent,
        ]
        
        for agent_class in agent_classes:
            try:
                agent = agent_class(shared_llm=self.shared_llm)
                self.agents[agent.name] = agent
            except Exception as e:
                print(f"⚠️  Fehler beim Initialisieren von {agent_class.__name__}: {e}")
    
    def _determine_routing_strategy(self) -> str:
        """
        Bestimme Routing-Strategie basierend auf Modell-Größe.
        
        Kleine Modelle (<10B): Aggressive keyword pre-routing
        Mittelgroße Modelle (10-30B): Hybrid (keywords als hints)
        Große Modelle (>30B): Trust LLM, minimal keywords
        
        Returns:
            'keyword_heavy', 'hybrid', oder 'llm_heavy'
        """
        if not self.use_adaptive_routing:
            return 'keyword_heavy'  # Fallback to original behavior
        
        model_name = settings.OLLAMA_MODEL.lower()
        
        # Extract parameter size from model name
        if '70b' in model_name or '72b' in model_name:
            strategy = 'llm_heavy'
        elif '20b' in model_name or '13b' in model_name:
            strategy = 'hybrid'
        elif '8b' in model_name or '7b' in model_name or '3b' in model_name:
            strategy = 'keyword_heavy'
        else:
            # Default: hybrid for unknown models
            strategy = 'hybrid'
        
        print(f"🎯 Routing-Strategie: {strategy} (Modell: {model_name})")
        return strategy
    
    def _get_routing_prompt(self) -> str:
        """Erstelle den System-Prompt für das Routing."""
        # Sammle Informationen über verfügbare Agenten
        agent_descriptions = []
        for name, agent in self.agents.items():
            tools = ", ".join(agent.get_tool_names())
            agent_descriptions.append(
                f"- **{name}**: {agent.description}\n  Tools: {tools}"
            )
        
        agents_info = "\n".join(agent_descriptions)
        
        return f"""Du bist ein Routing-Agent für ein Multi-Agent-System der Universität zu Köln.

## DEINE AUFGABE
Analysiere die Nutzeranfrage und entscheide, welcher spezialisierte Agent sie bearbeiten soll.

## VERFÜGBARE AGENTEN
{agents_info}

## ROUTING-REGELN

1. **KLIPS-Agent** wählen bei:
   - Account-Registrierung, Anmeldung, Konto erstellen
   - Studienbewerbung, Studiengang bewerben
   - Passwort-Änderung
   - Adress-Änderung
   - Kurse, Veranstaltungen, Lehrveranstaltungen, Kursnummern (z.B. "Kurs 14530")
   - ALLES was KLIPS2 betrifft

2. **Email-Agent** wählen bei:
   - Expliziter Bitte, eine E-Mail zu senden
   - Support-Anfragen, die eskaliert werden sollen
   - Kontaktaufnahme mit dem Support

3. **Wissens-Agent** wählen bei:
   - Allgemeine Fragen OHNE KLIPS-Bezug
   - Web-Suche mit Schlüsselwörtern: "im Internet", "online", "suche nach", "recherchiere"
   - Webseiten-Inhalte extrahieren (URLs)
   - NUR wenn kein anderer Agent passt

## ANTWORTFORMAT
Antworte NUR mit einem JSON-Objekt in diesem Format:
```json
{{
  "agent_name": "<Name des Agenten>",
  "reasoning": "<Kurze Begründung>",
  "context": "<Optionaler Kontext für den Agenten>"
}}
```

WICHTIG: Gib NUR das JSON zurück, keinen anderen Text!"""
    
    def _keyword_pre_route(self, message: str) -> Optional[RoutingDecision]:
        """
        Schnelles Keyword-basiertes Pre-Routing ohne LLM-Aufruf.
        
        Adapts confidence and usage based on routing strategy:
        - keyword_heavy: High confidence (0.95), aggressive matching
        - hybrid: Lower confidence (0.75), keywords as hints
        - llm_heavy: Very low confidence (0.60), only obvious cases
        
        Returns None wenn LLM-Routing benötigt wird.
        """
        # Force LLM routing if configured (for evaluation consistency)
        if self.force_llm_routing:
            return None
        
        # Skip keyword routing for LLM-heavy strategy unless extremely obvious
        if self.routing_strategy == 'llm_heavy':
            # Only route on extremely explicit keywords
            msg_lower = message.lower()
            if 'sende eine e-mail' in msg_lower or 'send an email' in msg_lower:
                return RoutingDecision(
                    agent_name="Email-Agent",
                    confidence=0.60,
                    reasoning=f"Explicit email request (LLM-heavy mode)",
                    fallback_agent="Wissens-Agent"
                )
            # Let LLM handle everything else
            return None
        
        # Determine confidence based on strategy
        if self.routing_strategy == 'keyword_heavy':
            base_confidence = 0.95
        elif self.routing_strategy == 'hybrid':
            base_confidence = 0.75
        else:
            base_confidence = 0.60
        
        msg_lower = message.lower()
        
        # KLIPS-Keywords (sehr spezifisch) - erweitert für Englisch
        klips_keywords = [
            "klips", "registrier", "anmeld", "konto erstellen", "account", "sign up",
            "bewerb", "studienbewerbung", "studiengang", "apply", "application",
            "passwort änder", "password", "neues passwort", "change password",
            "adresse änder", "neue adresse", "umgezogen", "address", "change address",
            "kurs ", "veranstaltung", "lehrveranstaltung", "kursnummer", "course",
            "semester", "einschreib", "enroll"
        ]
        
        for keyword in klips_keywords:
            if keyword in msg_lower:
                return RoutingDecision(
                    agent_name="KLIPS-Agent",
                    confidence=base_confidence,
                    reasoning=f"Keyword-Match: '{keyword}' ({self.routing_strategy})",
                    fallback_agent="Wissens-Agent"
                )
        
        # Email-Keywords - erweitert
        email_keywords = [
            "e-mail send", "email send", "mail schick", "mail schreib", 
            "sende eine e-mail", "sende eine mail", "send email", "write email"
        ]
        for keyword in email_keywords:
            if keyword in msg_lower:
                return RoutingDecision(
                    agent_name="Email-Agent",
                    confidence=base_confidence,
                    reasoning=f"Keyword-Match: '{keyword}' ({self.routing_strategy})",
                    fallback_agent="Wissens-Agent"
                )
        
        # Email-Keywords - erweitert
        email_keywords = [
            "e-mail send", "email send", "mail schick", "mail schreib", 
            "sende eine e-mail", "sende eine mail", "send email", "write email"
        ]
        for keyword in email_keywords:
            if keyword in msg_lower:
                return RoutingDecision(
                    agent_name="Email-Agent",
                    confidence=base_confidence,
                    reasoning=f"Keyword-Match: '{keyword}' ({self.routing_strategy})",
                    fallback_agent="Wissens-Agent"
                )
        
        # Kein eindeutiger Match - LLM-Routing benötigt
        return None
    
    def _route_query(self, message: str) -> RoutingDecision:
        """
        Entscheide, welcher Agent die Anfrage bearbeiten soll.
        
        Nutzt Task-State für kontextbewusste Routing-Entscheidungen
        und liefert Confidence-Scores mit Fallback-Optionen.
        
        Args:
            message: Die Nutzeranfrage
            
        Returns:
            RoutingDecision mit gewähltem Agenten, Confidence und Fallback
        """
        # Versuche erst schnelles Keyword-Routing
        pre_route = self._keyword_pre_route(message)
        if pre_route:
            print(f"⚡ Pre-Routing: {pre_route.agent_name} (confidence={pre_route.confidence:.2f})")
            return pre_route
        
        routing_prompt = self._get_routing_prompt()
        
        messages = [
            SystemMessage(content=routing_prompt),
            HumanMessage(content=f"Analysiere diese Anfrage und wähle den passenden Agenten:\n\n{message}")
        ]
        
        try:
            response = self.routing_llm.invoke(messages)
            response_text = response.content.strip()
            
            # Versuche JSON zu parsen
            # Entferne mögliche Markdown-Code-Blöcke
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            decision_data = json.loads(response_text)
            
            # Validiere Agent-Name
            agent_name = decision_data.get("agent_name", "")
            if agent_name not in self.agents:
                # Fallback auf Wissens-Agent
                print(f"⚠️  Unbekannter Agent '{agent_name}', Fallback auf Wissens-Agent")
                agent_name = "Wissens-Agent"
            
            # Confidence Score
            confidence = decision_data.get("confidence", 0.8)
            
            # Fallback Agent
            fallback_agent = decision_data.get("fallback_agent")
            if fallback_agent and fallback_agent not in self.agents:
                fallback_agent = "Wissens-Agent"
            
            decision = RoutingDecision(
                agent_name=agent_name,
                confidence=confidence,
                reasoning=decision_data.get("reasoning", ""),
                fallback_agent=fallback_agent
            )
            
            # Check confidence and warn if low
            if confidence < self.confidence_threshold:
                print(f"⚠️  Niedrige Confidence ({confidence:.2f}), Fallback: {fallback_agent}")
            
            return decision
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Fallback: Wissens-Agent bei Parse-Fehler
            print(f"⚠️  Routing-Parse-Fehler: {e}, Fallback auf Wissens-Agent")
            return RoutingDecision(
                agent_name="Wissens-Agent",
                confidence=0.5,  # Niedrige Confidence bei Fehler
                reasoning="Fallback wegen Parse-Fehler",
                fallback_agent="KLIPS-Agent"
            )
    
    def _detect_multi_step(self, message: str) -> bool:
        """Erkenne ob die Anfrage mehrere Schritte erfordert."""
        multi_step_indicators = [
            "dann", "und dann", "danach", "anschließend", "afterwards", "then",
            "und schick", "und sende", "and send", "and email",
            "suche.*und", "search.*and", "hole.*und", "get.*and"
        ]
        msg_lower = message.lower()
        return any(indicator in msg_lower for indicator in multi_step_indicators)
    
    def _decompose_query(self, message: str) -> List[str]:
        """
        Zerlege Multi-Step-Anfrage in einzelne Schritte.
        
        Nutzt LLM um die Anfrage in ausführbare Teilschritte zu zerlegen.
        """
        decompose_prompt = f"""Zerlege diese Anfrage in sequentielle Schritte:

{message}

Gib die Schritte als JSON-Array zurück:
{{"steps": ["Schritt 1", "Schritt 2", ...]}}

Nur JSON zurückgeben!"""
        
        try:
            response = self.routing_llm.invoke([SystemMessage(content=decompose_prompt)])
            content = response.content.strip()
            
            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            steps = data.get("steps", [])
            
            if len(steps) > 1:
                print(f"📋 Query in {len(steps)} Schritte zerlegt")
                return steps
        except Exception as e:
            print(f"⚠️ Decomposition fehlgeschlagen: {e}")
        
        # Fallback: Original-Nachricht als einzelner Schritt
        return [message]
    
    def process(self, message: str, session_id: Optional[str] = None) -> str:
        """
        Verarbeite eine Nachricht und gebe die Antwort zurück.
        
        Unterstützt Multi-Step-Workflows:
        - Erkennt ob mehrere Schritte nötig sind
        - Zerlegt Anfrage in Teilschritte
        - Führt Schritte sequentiell aus: Orchestrator → Agent → Orchestrator → Agent
        - Sammelt Zwischenergebnisse und gibt Gesamtergebnis zurück
        
        Args:
            message: Die Nutzeranfrage
            session_id: Optionale Session-ID für Tracing
            
        Returns:
            Die Antwort (evtl. aus mehreren Agent-Aufrufen aggregiert)
        """
        try:
            # Prüfe ob Multi-Step-Workflow
            is_multi_step = self._detect_multi_step(message)
            
            if is_multi_step:
                # Multi-Step: Zerlege und führe sequentiell aus
                steps = self._decompose_query(message)
                
                if len(steps) > 1:
                    print(f"🔄 Multi-Step-Workflow: {len(steps)} Schritte")
                    step_results = []
                    
                    for i, step in enumerate(steps, 1):
                        print(f"\n--- Schritt {i}/{len(steps)}: {step[:50]}...")
                        
                        # Route für diesen Schritt
                        routing = self._route_query(step)
                        print(f"🎯 Routing zu: {routing.agent_name}")
                        
                        # Führe Schritt aus
                        agent = self.agents.get(routing.agent_name)
                        if not agent:
                            print(f"⚠️ Agent nicht gefunden: {routing.agent_name}")
                            continue
                        
                        # Kontext: Vorherige Ergebnisse
                        context = "\n".join([f"Schritt {j}: {r}" for j, r in enumerate(step_results, 1)]) if step_results else None
                        
                        # Agent ausführen
                        step_result = agent.process(step, context=context)
                        step_results.append(step_result)
                        print(f"✓ Schritt {i} abgeschlossen")
                    
                    # Aggregiere Ergebnisse
                    if len(step_results) == 1:
                        return step_results[0]
                    
                    final_result = "\n\n".join([
                        f"**Schritt {i}:**\n{result}" 
                        for i, result in enumerate(step_results, 1)
                    ])
                    return f"Multi-Step-Ergebnis:\n\n{final_result}"
            
            # Single-Step: Normaler Ablauf
            # 1. Routing-Entscheidung treffen
            routing = self._route_query(message)
            print(f"🎯 Routing zu: {routing.agent_name} ({routing.reasoning})")
            
            # 2. Spezialisierten Agenten aufrufen
            agent = self.agents.get(routing.agent_name)
            if not agent:
                return f"Fehler: Agent '{routing.agent_name}' nicht verfügbar."
            
            # Track which agent was routed to (for evaluation)
            self.last_routed_agent = routing.agent_name
            
            # 3. Anfrage an Agenten delegieren
            # Übergebe strukturierten Kontext
            context_string = self.shared_context.to_context_string()
            response = agent.process(message, context=context_string)
            
            # Store the agent's response for evaluation
            self.last_agent_response = agent.last_agent_response
            
            # 4. Memory aktualisieren
            self.memory.append(HumanMessage(content=message))
            self.memory.append(AIMessage(content=response))
            
            if len(self.memory) > self._max_memory_size:
                self.memory = self.memory[-self._max_memory_size:]
            
            return response
            
        except Exception as e:
            error_msg = f"Fehler im Orchestrator: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def get_available_agents(self) -> List[str]:
        """Gebe Liste der verfügbaren Agenten zurück."""
        return list(self.agents.keys())
    
    def get_all_tools(self) -> List[str]:
        """Gebe Liste aller verfügbaren Tools über alle Agenten zurück."""
        all_tools = []
        for agent in self.agents.values():
            all_tools.extend(agent.get_tool_names())
        return all_tools
    
    def get_agent_info(self) -> Dict[str, Dict[str, Any]]:
        """Gebe detaillierte Informationen über alle Agenten zurück."""
        return {
            name: agent.get_routing_info()
            for name, agent in self.agents.items()
        }
    
    def clear_memory(self) -> None:
        """Lösche die Konversationshistorie aller Agenten und Task State."""
        self.memory = []
        self.last_routed_agent = None
        self.last_agent_response = None
        
        # Reset Task State und Shared Context
        self.task_state = TaskState()
        self.shared_context = SharedContext()
        
        for agent in self.agents.values():
            agent.clear_memory()
    
    def get_tool_selection(self, message: str) -> tuple:
        """
        Ermittle Routing und Tool-Auswahl ohne Tool-Ausführung (für Evaluierung).
        
        Handles multi-step workflows by decomposing and collecting tools from all steps.
        
        Args:
            message: Die Nutzeranfrage
            
        Returns:
            Tuple von (agent_name, tool_calls) - bei multi-step: mehrere Agenten, aggregierte Tools
        """
        try:
            # Check if multi-step
            is_multi_step = self._detect_multi_step(message)
            
            if is_multi_step:
                steps = self._decompose_query(message)
                
                if len(steps) > 1:
                    # Multi-Step: Sammle Tools von allen Schritten
                    all_tools = []
                    agent_names = []
                    
                    for i, step in enumerate(steps, 1):
                        routing = self._route_query(step)
                        agent = self.agents.get(routing.agent_name)
                        
                        if agent:
                            context_string = self.shared_context.to_context_string()
                            step_tools = agent.get_tool_selection(step, context=context_string)
                            all_tools.extend(step_tools)
                            agent_names.append(routing.agent_name)
                    
                    # Return first agent name, all tools (evaluation compatibility)
                    primary_agent = agent_names[0] if agent_names else "Wissens-Agent"
                    return primary_agent, all_tools
            
            # Single-Step: Normales Routing
            routing = self._route_query(message)
            print(f"🎯 Routing zu: {routing.agent_name} ({routing.reasoning})")
            
            self.last_routed_agent = routing.agent_name
            
            # Spezialisierten Agenten für Tool-Auswahl fragen (ohne Ausführung)
            agent = self.agents.get(routing.agent_name)
            if not agent:
                return routing.agent_name, []
            
            # Tool-Auswahl ohne Ausführung (mit strukturiertem Kontext)
            context_string = self.shared_context.to_context_string()
            tool_calls = agent.get_tool_selection(message, context=context_string)
            
            return routing.agent_name, tool_calls
            
        except Exception as e:
            print(f"❌ Fehler bei Tool-Auswahl: {str(e)}")
            return "Wissens-Agent", []
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Gebe Zusammenfassung des Memory zurück."""
        human_messages = [msg for msg in self.memory if isinstance(msg, HumanMessage)]
        ai_messages = [msg for msg in self.memory if isinstance(msg, AIMessage)]
        
        return {
            "total_messages": len(self.memory),
            "human_messages": len(human_messages),
            "ai_messages": len(ai_messages),
            "last_messages": [
                msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                for msg in self.memory[-5:]
            ]
        }
