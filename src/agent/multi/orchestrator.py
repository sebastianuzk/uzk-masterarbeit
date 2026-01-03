"""
Orchestrator Agent - Supervisor-Agent für das Multi-Agent-System.

Der Orchestrator ist der zentrale Routing-Agent, der eingehende
Anfragen analysiert und an den passenden spezialisierten Agenten
weiterleitet.

Implementiert das Supervisor-Pattern:
1. Empfängt Anfrage vom Nutzer
2. Analysiert die Anfrage
3. Wählt den passenden spezialisierten Agenten
4. Delegiert die Anfrage
5. Gibt die Antwort zurück
"""

import json
import os
from typing import Any, Dict, List, Optional, Type

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from config.settings import settings

from .base_agent import BaseSpecializedAgent
from .klips_agent import KlipsAgent
from .email_agent import EmailAgent
from .knowledge_agent import KnowledgeAgent


class RoutingDecision(BaseModel):
    """Schema für die Routing-Entscheidung des Orchestrators."""
    
    agent_name: str = Field(
        description="Name des gewählten Agenten: 'KLIPS-Agent', 'Email-Agent' oder 'Wissens-Agent'"
    )
    reasoning: str = Field(
        description="Kurze Begründung für die Wahl des Agenten"
    )
    context: Optional[str] = Field(
        default=None,
        description="Optionaler Kontext für den spezialisierten Agenten"
    )


class OrchestratorAgent:
    """
    Supervisor-Agent der das Routing zu spezialisierten Agenten übernimmt.
    
    Der Orchestrator analysiert jede Anfrage und entscheidet,
    welcher spezialisierte Agent am besten geeignet ist.
    """
    
    def __init__(self):
        """Initialisiere den Orchestrator mit allen spezialisierten Agenten."""
        print("🎭 Initialisiere Multi-Agent Orchestrator...")
        
        # Validiere Einstellungen
        settings.validate()
        
        # Track last routed agent and response for evaluation
        self.last_routed_agent: Optional[str] = None
        self.last_agent_response: Optional[Dict[str, Any]] = None
        
        # LangSmith Tracing konfigurieren (falls aktiviert)
        if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            print(f"✅ LangSmith-Tracing aktiviert für Projekt: {settings.LANGSMITH_PROJECT}")
        
        # Shared LLM für alle Agenten (Ressourceneffizienz)
        self.shared_llm = self._create_llm()
        
        # Spezialisierte Agenten initialisieren
        self.agents: Dict[str, BaseSpecializedAgent] = {}
        self._initialize_agents()
        
        # Routing LLM (kann leichteres Modell sein)
        self.routing_llm = self.shared_llm
        
        # Memory für Konversationshistorie
        self.memory: List[Any] = []
        self._max_memory_size = settings.MEMORY_SIZE
        
        print(f"🎭 Orchestrator bereit mit {len(self.agents)} spezialisierten Agenten")
    
    def _create_llm(self) -> ChatOllama:
        """Erstelle die shared LLM-Instanz."""
        MODEL_CTX_SIZES = {
            "0.5b": 2048,
            "1b": 4096,
            "3b": 8192,
            "8b": 8192,
            "20b": 16384,
            "70b": 16384,
        }
        
        model_lower = settings.OLLAMA_MODEL.lower()
        ctx_size = 8192
        for size_key, ctx_value in MODEL_CTX_SIZES.items():
            if size_key in model_lower:
                ctx_size = ctx_value
                break
        
        print(f"🤖 Initialisiere ChatOllama mit Modell: {settings.OLLAMA_MODEL} (ctx_size={ctx_size})")
        
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
            num_ctx=ctx_size,
            timeout=settings.REQUEST_TIMEOUT,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )
    
    def _initialize_agents(self) -> None:
        """Initialisiere alle spezialisierten Agenten."""
        agent_classes: List[Type[BaseSpecializedAgent]] = [
            KlipsAgent,
            EmailAgent,
            KnowledgeAgent,
        ]
        
        for agent_class in agent_classes:
            try:
                agent = agent_class(share_llm=self.shared_llm)
                self.agents[agent.name] = agent
            except Exception as e:
                print(f"⚠️  Fehler beim Initialisieren von {agent_class.__name__}: {e}")
    
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
   - Account-Registrierung, Anmeldung
   - Studienbewerbung
   - Passwort-Änderung
   - Adress-Änderung
   - Kurs- oder Lehrveranstaltungsfragen mit Kursnummern

2. **Email-Agent** wählen bei:
   - Expliziter Bitte, eine E-Mail zu senden
   - Support-Anfragen, die eskaliert werden sollen
   - Kontaktaufnahme mit dem Support

3. **Wissens-Agent** wählen bei:
   - Allgemeine Fragen über die Universität
   - Informationen zu Studiengängen, Fristen, Prüfungen
   - Fragen, die Recherche erfordern
   - Web-Suche oder Webseiten-Inhalte

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
    
    def _route_query(self, message: str) -> RoutingDecision:
        """
        Entscheide, welcher Agent die Anfrage bearbeiten soll.
        
        Args:
            message: Die Nutzeranfrage
            
        Returns:
            RoutingDecision mit gewähltem Agenten und Begründung
        """
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
            
            # Kontext verarbeiten - falls dict, in String umwandeln
            context = decision_data.get("context")
            if context and isinstance(context, dict):
                # Konvertiere dict zu einem sinnvollen String
                context = json.dumps(context, ensure_ascii=False)
            
            return RoutingDecision(
                agent_name=agent_name,
                reasoning=decision_data.get("reasoning", ""),
                context=context
            )
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Fallback: Versuche Agent-Namen aus Text zu extrahieren
            print(f"⚠️  Fehler beim Parsen der Routing-Entscheidung: {e}")
            
            response_lower = response_text.lower() if response_text else ""
            
            if "klips" in response_lower:
                return RoutingDecision(
                    agent_name="KLIPS-Agent",
                    reasoning="Keyword-basiertes Fallback-Routing",
                    context=None
                )
            elif "email" in response_lower or "e-mail" in response_lower:
                return RoutingDecision(
                    agent_name="Email-Agent",
                    reasoning="Keyword-basiertes Fallback-Routing",
                    context=None
                )
            else:
                return RoutingDecision(
                    agent_name="Wissens-Agent",
                    reasoning="Standard-Fallback-Routing",
                    context=None
                )
    
    def process(self, message: str, session_id: Optional[str] = None) -> str:
        """
        Verarbeite eine Nachricht und gebe die Antwort zurück.
        
        Args:
            message: Die Nutzeranfrage
            session_id: Optionale Session-ID für Tracing
            
        Returns:
            Die Antwort des spezialisierten Agenten
        """
        try:
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
            response = agent.process(message, context=routing.context)
            
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
        """Lösche die Konversationshistorie aller Agenten."""
        self.memory = []
        self.last_routed_agent = None
        self.last_agent_response = None
        for agent in self.agents.values():
            agent.clear_memory()
    
    def get_tool_selection(self, message: str) -> tuple:
        """
        Ermittle Routing und Tool-Auswahl ohne Tool-Ausführung (für Evaluierung).
        
        Args:
            message: Die Nutzeranfrage
            
        Returns:
            Tuple von (agent_name, tool_calls)
        """
        try:
            # 1. Routing-Entscheidung treffen
            routing = self._route_query(message)
            print(f"🎯 Routing zu: {routing.agent_name} ({routing.reasoning})")
            
            self.last_routed_agent = routing.agent_name
            
            # 2. Spezialisierten Agenten für Tool-Auswahl fragen (ohne Ausführung)
            agent = self.agents.get(routing.agent_name)
            if not agent:
                return routing.agent_name, []
            
            # Tool-Auswahl ohne Ausführung
            tool_calls = agent.get_tool_selection(message, context=routing.context)
            
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
