"""
Plan-and-Execute Agent mit LangGraph StateGraph für autonomes Verhalten
"""
import operator
from datetime import datetime
from typing import List, Dict, Any, Optional, TypedDict, Annotated, Tuple, Literal, Union
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from config.settings import settings
from src.tools.web_scraper_tool import create_web_scraper_tool
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool
from src.tools.email_tool import create_email_tool


class Plan(BaseModel):
    """Plan für zukünftige Ausführung"""
    steps: List[str] = Field(description="verschiedene Schritte, die befolgt werden sollen, sollten in sortierter Reihenfolge sein")


class Response(BaseModel):
    """Antwort an den Benutzer."""
    response: str

class Act(BaseModel):
    """Auszuführende Aktion."""

    action: Union[Response, Plan] = Field(
        description="Auszuführende Aktion. Wenn du dem Benutzer antworten willst, verwende Response. "
        "Wenn du weitere Tools verwenden musst, um die Antwort zu erhalten, verwende Plan."
    )


class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str


# Tools-Setup
tools = []
if settings.ENABLE_WEB_SCRAPER:
    tools.append(create_web_scraper_tool())
if settings.ENABLE_DUCKDUCKGO:
    tools.append(create_duckduckgo_tool())
if settings.ENABLE_UNIVERSITY_RAG:
    rag_tool = create_university_rag_tool()
    if rag_tool:
        tools.append(rag_tool)
if settings.ENABLE_EMAIL:
    tools.append(create_email_tool())

# LLM-Setup
llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=settings.TEMPERATURE,
    timeout=settings.REQUEST_TIMEOUT
)

llmp = ChatOllama(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=0,
    timeout=settings.REQUEST_TIMEOUT
)

llmrp = ChatOllama(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=0,
    timeout=settings.REQUEST_TIMEOUT
)

# Agent-Executor erstellen
agent_executor = create_react_agent(llm, tools)

# Planer-Setup mit deutschen Prompts
planner_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Du bist ein Planer-Agent, welcher lediglich einen Plan erstellt. "
     "Für das gegebene Ziel darfst du ausschließlich einen einfachen schrittweisen Plan erstellen. "
     "Dieser Plan muss einzelne Aufgaben enthalten, die minimal notwendig sind, um das Ziel zu erreichen. "
     "Füge keine überflüssigen Schritte hinzu. Das Ergebnis des letzten Schritts sollte die endgültige Antwort sein. "
     "Stelle sicher, dass jeder Schritt alle benötigten Informationen enthält - überspringe keine Schritte."
     "Stelle sicher, dass die Schritte möglichst kurz und prägnant sind. "
     "Du selber darfst keine Schritte ausführen, sondern nur den Plan erstellen."),
    ("placeholder", "{messages}"),
])
planner = planner_prompt | llmp.with_structured_output(Plan)

replanner_prompt = ChatPromptTemplate.from_template(
    """Du bist ein Replanner-Agent, welcher lediglich einen bestehenden Plan aktualisiert.
Für das gegebene Ziel darfst du ausschließlich einen einfachen schrittweisen Plan erstellen.
Dieser Plan muss einzelne Aufgaben enthalten, die minimal notwendig sind, um das Ziel zu erreichen.
Füge keine überflüssigen Schritte hinzu. Das Ergebnis des letzten Schritts sollte die endgültige Antwort sein.
Stelle sicher, dass jeder Schritt alle benötigten Informationen enthält - überspringe keine Schritte.
Stelle sicher, dass die Schritte möglichst kurz und prägnant sind.
Das Erstellen der Antwort darf kein Teil des Plans sein.
Du selber darfst keine Schritte ausführen, sondern nur den Plan erstellen.

Dein Ziel war:
{input}

Dein ursprünglicher Plan war:
{plan}

Bereits durchgeführte Schritte:
{past_steps}    

Erfolgreich erledigte Schritte des Plans dürfen nicht erneut durchgeführt werden. Falls ein Schritt nicht erfolgreich war, behalte ihn unverändert im Plan bei.
Füge nur Schritte zum Plan hinzu, die noch erfolgreich abzuschließen sind. Wenn alle Schritte erfolgreich sind und du dem Benutzer antworten kannst, dann antworte ihm. Ansonsten fülle den Plan aus.

Antworte dem Benutzer, sobald das Ziel erreicht wurde. Das Ziel gilt als erreicht, sobald alle notwendigen Schritte erfolgreich abgeschlossen sind. Falls das Ziel noch nicht erreicht wurde, aktualisiere deinen Plan basierend auf den vorliegenden Informationen.
"""
)

replanner = replanner_prompt | llmrp.with_structured_output(Act)


def execute_step(state: PlanExecute):
    plan = state["plan"]

    past_steps = state.get("past_steps", [])
    
    # DEBUG: Plan-Status ausgeben
    print("\n" + "="*50)
    print("🔧 EXECUTE_STEP DEBUG:")
    print(f"📋 Aktueller Plan ({len(plan)} Schritte):")
    for i, step in enumerate(plan, 1):
        print(f"  {i}. {step}")
    print(f"✅ Bereits erledigt ({len(past_steps)} Schritte):")
    for i, (task, result) in enumerate(past_steps, 1):
        print(f"  {i}. {task} → {result[:100]}...")
    print("="*50)
    
    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    task = plan[0]
    task_formatted = f"""Für den folgenden Plan:
{plan_str}\n\nDu sollst Schritt {1} ausführen: {task}. Fasse die Ergebnisse kurz und prägnant zusammen. Gebe kurz zurück, ob der Schritt erfolgreich erledigt wurde."""
    
    agent_response = agent_executor.invoke({"messages": [("user", task_formatted)]})
    return {"past_steps": [(task, agent_response["messages"][-1].content)]}


def plan_step(state: PlanExecute):
    plan = planner.invoke({"messages": [("user", state["input"])]})
    
    # DEBUG: Initial Plan ausgeben
    print("\n" + "="*50)
    print("🎬 INITIAL PLAN DEBUG:")
    print(f"❓ Eingabe: {state['input']}")
    print(f"📋 Erstellter Plan ({len(plan.steps)} Schritte):")
    for i, step in enumerate(plan.steps, 1):
        print(f"  {i}. {step}")
    print("="*50)
    
    return {"plan": plan.steps}


def replan_step(state: PlanExecute):
    # Replanning mit Retry bei Fehlern
    for attempt in range(3):
        try:
            output = replanner.invoke(state)
            if output and hasattr(output, 'action') and output.action:
                if isinstance(output.action, Response):
                    return {"response": output.action.response}
                else:
                    return {"plan": output.action.steps}
            print(f"🔄 Replan retry {attempt + 1}/3")
        except Exception as e:
            print(f"❌ Replan error: {e}")
    
    return {"response": "Entschuldigung, ich konnte die Anfrage nicht vollständig verarbeiten."}


def should_end(state: PlanExecute):
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"


# Workflow erstellen
workflow = StateGraph(PlanExecute)
workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_step)
workflow.add_node("replan", replan_step)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "agent")
workflow.add_edge("agent", "replan")
workflow.add_conditional_edges("replan", should_end, ["agent", END])

# Kompilieren
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


def create_plan_and_execute_agent():
    """Factory-Funktion zur Erstellung eines Plan-and-Execute Agenten"""
    return app