"""
React Agent basierend auf LangGraph für autonomes Verhalten mit Ollama
Erweitert um intelligente E-Mail-Eskalation bei ungelösten Anfragen
"""
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from langgraph.prebuilt import create_react_agent as create_langgraph_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from config.settings import settings
from src.tools.wikipedia_tool import create_wikipedia_tool
from src.tools.web_scraper_tool import create_web_scraper_tool
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool
from src.tools.email_tool import create_email_tool


class ReactAgent:
    """Autonomer React Agent mit LangGraph, Ollama und intelligenter E-Mail-Eskalation"""
    
    def __init__(self):
        # Validiere Einstellungen
        settings.validate()
        
        # Initialisiere Ollama LLM
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
        )
        
        # Initialisiere Tools (einschließlich E-Mail-Tool)
        self.tools = self._create_tools()
        
        # System-Prompt für bessere Konversation UND Qualitätsbewertung
        system_prompt = """Du bist ein hilfsreicher und freundlicher Chatbot-Assistent mit der Fähigkeit zur Selbstreflexion.

WICHTIGE REGELN:
1. Führe NORMALE UNTERHALTUNGEN, ohne automatisch nach Informationen zu suchen
2. Verwende Tools NUR wenn explizit nach aktuellen Informationen, Fakten oder Recherche gefragt wird
3. Bei Begrüßungen, Smalltalk oder persönlichen Fragen antworte direkt freundlich
4. Wenn jemand seinen Namen sagt, begrüße ihn höflich - suche NICHT nach dem Namen!

QUALITÄTSBEWERTUNG:
Nach jeder Antwort bewerte selbstkritisch ohne dies im Chat zu erwähnen:
- Konnte ich die Frage vollständig beantworten?
- War meine Antwort präzise und hilfreich?
- Hat der Benutzer möglicherweise eine unzufriedene Reaktion?
- Sollte diese Anfrage eskaliert werden?

ESKALATION:
Bei mehreren aufeinanderfolgenden unzureichenden Antworten oder komplexen unbeantwortbaren Anfragen verwende das E-Mail-Tool
für professionelle Support-Eskalation. Der Betreff sollte eine kurze Zusammenfassung des Themas enthalten z.B. "Unzufriedenheit mit Informationen zu Bewerbungsfristen".
Der Inhalt der E-Mail sollte eine Zusammenfassung der Problembeschreibung und alle relevanten Informationen enthalten. Darüber hinaus soll die relevante Chat-Historie beigefügt werden.

Verfügbare Tools:
- Wikipedia: Für Enzyklopädie-Informationen
- Web-Scraping: Für Inhalte von spezifischen Webseiten  
- DuckDuckGo: Für aktuelle Websuche
- Universitäts-Wissensdatenbank: Für Fragen zur Universität zu Köln / WiSo-Fakultät
- E-Mail: Für Support-Eskalation bei ungelösten Anfragen

Verwende Tools nur bei entsprechenden Anfragen, nicht bei Smalltalk."""

        # Erstelle React Agent mit erweitertem System-Prompt
        self.agent = create_langgraph_agent(
            self.llm,
            self.tools,
            prompt=system_prompt
        )
        
        # Memory für Konversationshistorie
        self.memory = []
        
        # Tracking für E-Mail-Eskalation (flexibel, nicht hart-codiert)
        self.conversation_context = {
            "user_satisfaction_indicators": [],
            "unresolved_queries": [],
            "escalation_triggers": [],
            "conversation_quality_scores": []
        }
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools einschließlich E-Mail-Tool"""
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
        
        return tools
    
    def chat(self, message: str) -> str:
        """Führe eine Unterhaltung mit dem Agenten mit intelligenter Qualitätsbewertung"""
        try:
            # Füge Nachricht zum Memory hinzu
            human_message = HumanMessage(content=message)
            self.memory.append(human_message)
            
            # Analysiere Benutzer-Nachricht auf Unzufriedenheit
            self._analyze_user_satisfaction(message)
            
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
            ai_response = AIMessage(content=response_text)
            self.memory.append(ai_response)
            
            # Bewerte Antwortqualität und prüfe Eskalationsbedarf
            self._evaluate_response_quality(message, response_text)
            
            # Prüfe ob E-Mail-Eskalation erforderlich ist
            if self._should_escalate_to_email():
                self._trigger_email_escalation(message, response_text)
            
            return response_text
            
        except Exception as e:
            error_msg = f"Fehler beim Verarbeiten der Nachricht: {str(e)}"
            self.memory.append(AIMessage(content=error_msg))
            
            # Auch Fehler können Eskalation auslösen
            self.conversation_context["escalation_triggers"].append({
                "type": "system_error",
                "message": message,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
            return error_msg
    
    def get_available_tools(self) -> List[str]:
        """Gebe Liste der verfügbaren Tools zurück"""
        return [tool.name for tool in self.tools]
    
    def clear_memory(self):
        """Lösche Konversationshistorie und Eskalations-Context"""
        self.memory = []
        self.conversation_context = {
            "user_satisfaction_indicators": [],
            "unresolved_queries": [],
            "escalation_triggers": [],
            "conversation_quality_scores": []
        }
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Gebe erweiterte Zusammenfassung des Memory und Eskalations-Status zurück"""
        human_messages = [msg for msg in self.memory if isinstance(msg, HumanMessage)]
        ai_messages = [msg for msg in self.memory if isinstance(msg, AIMessage)]
        
        return {
            "total_messages": len(self.memory),
            "human_messages": len(human_messages),
            "ai_messages": len(ai_messages),
            "last_messages": [msg.content[:100] + "..." if len(msg.content) > 100 else msg.content 
                            for msg in self.memory[-5:]],
            "escalation_status": {
                "satisfaction_indicators": len(self.conversation_context["user_satisfaction_indicators"]),
                "unresolved_queries": len(self.conversation_context["unresolved_queries"]),
                "escalation_triggers": len(self.conversation_context["escalation_triggers"]),
                "quality_scores": self.conversation_context["conversation_quality_scores"][-5:] if self.conversation_context["conversation_quality_scores"] else []
            }
        }
    
    def _analyze_user_satisfaction(self, message: str) -> None:
        """Analysiere Benutzer-Nachricht auf Zufriedenheit/Unzufriedenheit (flexibel, nicht hart-codiert)"""
        message_lower = message.lower()
        
        # Dynamische Muster für Unzufriedenheit
        dissatisfaction_patterns = [
            r'\b(verstehe?\s*(ich\s*)?nicht|kapiere?\s*nicht|weiß\s*nicht)\b',
            r'\b(hilft\s*mir\s*nicht|funktioniert\s*nicht|geht\s*nicht)\b',
            r'\b(falsch|unvollständig|ungenau|schlecht)\b',
            r'\b(nochmal|noch\s*einmal|erneut|wieder)\b.*\b(frage|erkläre|versuche)\b',
            r'\b(das\s*war\s*nicht|ist\s*nicht\s*das|wollte\s*ich\s*nicht)\b',
            r'\b(kann\s*mir\s*jemand|brauche\s*hilfe|support|admin)\b',
            r'\b(frustriert|ärgerlich|unzufrieden|enttäuscht)\b'
        ]
        
        satisfaction_patterns = [
            r'\b(danke|dankeschön|perfekt|super|toll|großartig)\b',
            r'\b(hat\s*geholfen|verstehe|verstanden|klar)\b',
            r'\b(genau\s*das|richtig|korrekt|stimmt)\b'
        ]
        
        # Analyse der Nachricht
        dissatisfaction_score = sum(1 for pattern in dissatisfaction_patterns if re.search(pattern, message_lower))
        satisfaction_score = sum(1 for pattern in satisfaction_patterns if re.search(pattern, message_lower))
        
        if dissatisfaction_score > 0:
            self.conversation_context["user_satisfaction_indicators"].append({
                "type": "dissatisfaction",
                "score": dissatisfaction_score,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
        elif satisfaction_score > 0:
            self.conversation_context["user_satisfaction_indicators"].append({
                "type": "satisfaction",
                "score": satisfaction_score,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
    
    def _evaluate_response_quality(self, user_message: str, ai_response: str) -> None:
        """Bewerte die Qualität der AI-Antwort (adaptiv)"""
        # Einfache heuristische Qualitätsbewertung
        quality_indicators = {
            "length_appropriate": 20 <= len(ai_response) <= 1000,
            "contains_information": not any(phrase in ai_response.lower() for phrase in [
                "ich weiß nicht", "kann ich nicht", "keine informationen", "tut mir leid, ich kann"
            ]),
            "asks_clarification": "?" in ai_response and any(word in ai_response.lower() for word in [
                "können sie", "möchten sie", "was genau", "welche"
            ]),
            "provides_alternatives": any(word in ai_response.lower() for word in [
                "alternativ", "stattdessen", "oder", "auch möglich"
            ])
        }
        
        quality_score = sum(quality_indicators.values()) / len(quality_indicators)
        
        self.conversation_context["conversation_quality_scores"].append({
            "score": quality_score,
            "indicators": quality_indicators,
            "user_message": user_message,
            "ai_response": ai_response[:200] + "..." if len(ai_response) > 200 else ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Markiere als ungelöste Anfrage bei niedriger Qualität
        if quality_score < 0.5:
            self.conversation_context["unresolved_queries"].append({
                "user_message": user_message,
                "ai_response": ai_response,
                "quality_score": quality_score,
                "timestamp": datetime.now().isoformat()
            })
    
    def _should_escalate_to_email(self) -> bool:
        """Intelligente Entscheidung über E-Mail-Eskalation (adaptiv, nicht hart-codiert)"""
        # Zähle negative Indikatoren der letzten Interaktionen
        recent_dissatisfaction = [
            ind for ind in self.conversation_context["user_satisfaction_indicators"][-10:]
            if ind["type"] == "dissatisfaction"
        ]
        
        recent_unresolved = self.conversation_context["unresolved_queries"][-5:]
        recent_low_quality = [
            score for score in self.conversation_context["conversation_quality_scores"][-5:]
            if score["score"] < 0.4
        ]
        
        # Eskalations-Kriterien (flexibel anpassbar)
        escalation_criteria = {
            "multiple_dissatisfaction": len(recent_dissatisfaction) >= 3,
            "repeated_unresolved": len(recent_unresolved) >= 2,
            "consistently_low_quality": len(recent_low_quality) >= 3,
            "explicit_help_request": any(
                any(word in ind["message"].lower() for word in ["hilfe", "support", "admin", "jemand"])
                for ind in recent_dissatisfaction
            ),
            "error_accumulation": len(self.conversation_context["escalation_triggers"]) >= 2
        }
        
        # Eskaliere wenn mindestens 2 Kriterien erfüllt sind
        active_criteria = [criterion for criterion, active in escalation_criteria.items() if active]
        
        if len(active_criteria) >= 2:
            self.conversation_context["escalation_triggers"].append({
                "type": "automatic_escalation",
                "criteria_met": active_criteria,
                "timestamp": datetime.now().isoformat()
            })
            return True
        
        return False
    
    def _trigger_email_escalation(self, last_user_message: str, last_ai_response: str) -> None:
        """Löse E-Mail-Eskalation mit Zusammenfassung und Historie aus"""
        try:
            # Erstelle Zusammenfassung des Problems
            problem_summary = self._create_problem_summary()
            
            # Bereite Konversationshistorie für E-Mail auf
            conversation_history = self._prepare_conversation_history()
            
            # Finde E-Mail-Tool
            email_tool = next((tool for tool in self.tools if tool.name == "send_email"), None)
            
            if email_tool:
                # Sende Eskalations-E-Mail
                result = email_tool._run(
                    recipient="support",  # Wird automatisch an DEFAULT_RECIPIENT gesendet
                    subject=f"🚨 Chatbot-Eskalation: Ungelöste Benutzeranfrage",
                    body=f"""AUTOMATISCHE ESKALATION VOM CHATBOT-SYSTEM

PROBLEM-ZUSAMMENFASSUNG:
{problem_summary}

LETZTE BENUTZER-NACHRICHT:
{last_user_message}

LETZTE BOT-ANTWORT:
{last_ai_response}

VOLLSTÄNDIGE KONVERSATIONS-HISTORIE:
{conversation_history}

ESKALATIONS-STATISTIK:
- Unzufriedenheits-Indikatoren: {len(self.conversation_context['user_satisfaction_indicators'])}
- Ungelöste Anfragen: {len(self.conversation_context['unresolved_queries'])}
- Durchschnittliche Antwortqualität: {self._calculate_average_quality():.2f}

Bitte prüfen Sie diese Anfrage und kontaktieren Sie den Benutzer bei Bedarf.""",
                    sender_name="Autonomer Chatbot-Agent",
                    conversation_history=conversation_history,
                    request_summary=problem_summary
                )
                
                print(f"📧 E-Mail-Eskalation ausgelöst: {result}")
            else:
                print("⚠️  E-Mail-Tool nicht verfügbar für Eskalation")
                
        except Exception as e:
            print(f"❌ Fehler bei E-Mail-Eskalation: {e}")
    
    def _create_problem_summary(self) -> str:
        """Erstelle intelligente Zusammenfassung des Problems"""
        recent_messages = self.memory[-10:] if len(self.memory) >= 10 else self.memory
        user_messages = [msg.content for msg in recent_messages if isinstance(msg, HumanMessage)]
        
        if not user_messages:
            return "Keine spezifischen Benutzeranfragen verfügbar."
        
        # Einfache Zusammenfassung basierend auf häufigen Themen
        summary_parts = []
        
        if len(user_messages) > 1:
            summary_parts.append(f"Benutzer stellte {len(user_messages)} Anfragen.")
        
        # Analysiere wiederkehrende Begriffe
        all_words = " ".join(user_messages).lower().split()
        word_freq = {}
        for word in all_words:
            if len(word) > 3:  # Nur bedeutungsvolle Wörter
                word_freq[word] = word_freq.get(word, 0) + 1
        
        common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        if common_words:
            keywords = [word for word, count in common_words if count > 1]
            if keywords:
                summary_parts.append(f"Häufige Themen: {', '.join(keywords)}")
        
        unresolved_count = len(self.conversation_context["unresolved_queries"])
        if unresolved_count > 0:
            summary_parts.append(f"Anzahl ungelöster Anfragen: {unresolved_count}")
        
        dissatisfaction_count = len([
            ind for ind in self.conversation_context["user_satisfaction_indicators"]
            if ind["type"] == "dissatisfaction"
        ])
        if dissatisfaction_count > 0:
            summary_parts.append(f"Unzufriedenheits-Signale: {dissatisfaction_count}")
        
        return " | ".join(summary_parts) if summary_parts else "Allgemeine Konversationsprobleme erkannt."
    
    def _prepare_conversation_history(self) -> List[Dict]:
        """Bereite Konversationshistorie für E-Mail auf"""
        history = []
        
        for i, message in enumerate(self.memory):
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                role = "system"
            
            history.append({
                "role": role,
                "content": message.content,
                "timestamp": datetime.now().isoformat(),  # In real implementation, use actual timestamps
                "message_number": i + 1
            })
        
        return history
    
    def _calculate_average_quality(self) -> float:
        """Berechne durchschnittliche Antwortqualität"""
        scores = self.conversation_context["conversation_quality_scores"]
        if not scores:
            return 0.0
        
        return sum(score["score"] for score in scores) / len(scores)


def create_react_agent() -> ReactAgent:
    """Factory-Funktion für den React Agent"""
    return ReactAgent()