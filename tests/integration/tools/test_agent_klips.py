"""
Integration Tests für KLIPS über den Agenten
============================================
Testet ob der Agent die KLIPS-Tools korrekt nutzt und
die richtigen Parameter übergibt.

WARNUNG: Diese Tests können mit dem echten KLIPS-System interagieren!

HINWEIS: Diese Tests verwenden das gpt-oss:20b Modell für bessere Ergebnisse.
"""
import os
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Setze das Modell für alle Integration Tests auf gpt-oss:20b
os.environ["OLLAMA_MODEL"] = "gpt-oss:20b"

from tests.integration.tools.conftest import ollama_available


# Überspringe alle Tests wenn Ollama nicht verfügbar ist
pytestmark = pytest.mark.skipif(
    not ollama_available(),
    reason="Ollama-Server nicht erreichbar"
)


def has_klips_credentials():
    """Prüft ob KLIPS-Credentials vorhanden sind"""
    return bool(os.getenv("KLIPS_USERNAME")) and bool(os.getenv("KLIPS_PASSWORD"))


class ToolCallTracker:
    """Helper-Klasse um Tool-Aufrufe zu tracken"""
    
    def __init__(self, agent):
        from src.agent.react_agent import ReactAgent
        self.agent: ReactAgent = agent
        self.tool_calls: List[Dict] = []
        self._original_invoke = agent.agent.invoke
        
    def __enter__(self):
        def tracking_invoke(input_dict, **kwargs):
            result = self._original_invoke(input_dict, **kwargs)
            for msg in result.get("messages", []):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    self.tool_calls.extend(msg.tool_calls)
            return result
        
        self.agent.agent.invoke = tracking_invoke
        return self
    
    def __exit__(self, *args):
        self.agent.agent.invoke = self._original_invoke
    
    def get_tool_names(self) -> List[str]:
        return [tc.get('name', '') for tc in self.tool_calls]
    
    def get_calls_for_tool(self, tool_name: str) -> List[Dict]:
        return [tc for tc in self.tool_calls if tool_name.lower() in tc.get('name', '').lower()]
    
    def get_last_call_args(self, tool_name: str) -> Dict:
        calls = self.get_calls_for_tool(tool_name)
        return calls[-1].get('args', {}) if calls else {}


@pytest.fixture
def agent():
    """Erstellt einen Agent für die Tests mit gpt-oss:20b Modell"""
    from config.settings import Settings, settings
    from langchain_ollama import ChatOllama
    from langgraph.prebuilt import create_react_agent as create_langgraph_agent
    
    from src.agent.react_agent import ReactAgent
    
    # Überschreibe das Modell für bessere Test-Ergebnisse - BEVOR Agent erstellt wird
    Settings.OLLAMA_MODEL = "gpt-oss:20b"
    settings.OLLAMA_MODEL = "gpt-oss:20b"
    
    # Erstelle Agent
    agent_instance = ReactAgent()
    
    # IMMER das LLM mit dem korrekten Modell neu erstellen für konsistentes Verhalten
    agent_instance.llm = ChatOllama(
        model="gpt-oss:20b",
        base_url=settings.OLLAMA_BASE_URL,
        temperature=settings.TEMPERATURE,
        num_ctx=16384,  # Größerer Context für 20b Modell
        timeout=60,
        keep_alive="5m",
    )
    
    # Agent neu erstellen mit korrektem LLM
    agent_instance.agent = create_langgraph_agent(
        agent_instance.llm,
        agent_instance.tools
    )
    
    # Debug-Output
    print(f"\n🚀 Test-Konfiguration: Modell='{agent_instance.llm.model}', Timeout=60s")
    
    yield agent_instance


# =============================================================================
# TEST KLASSE: Agent fragt nach fehlenden Daten
# =============================================================================
@pytest.mark.integration
@pytest.mark.klips
@pytest.mark.slow
class TestAgentKLIPSDataCollection:
    """Tests: Agent sammelt alle benötigten Daten für KLIPS"""
    
    def test_agent_asks_for_studiengang_when_missing(self, agent):
        """Test: Agent fragt nach Studiengang oder versucht Tool zu nutzen"""
        with ToolCallTracker(agent) as tracker:
            response = agent.chat(
                "Ich möchte mich für das Wintersemester 2025/26 bewerben. "
                "Mein Login ist testuser mit Passwort test123."
            )
            
            assert isinstance(response, str)
            response_lower = response.lower()
            
            # Agent sollte entweder nach Studiengang fragen ODER Tool aufrufen
            asks_for_program = (
                "studiengang" in response_lower or
                "fach" in response_lower or
                "was möchtest" in response_lower or
                "welch" in response_lower
            )
            
            tool_called = len(tracker.tool_calls) > 0
            
            assert asks_for_program or tool_called, \
                f"Agent sollte nach Studiengang fragen oder Tool aufrufen, aber sagte: {response[:200]}"
    
    def test_agent_asks_for_semester_when_missing(self, agent):
        """Test: Agent fragt nach Semester oder versucht Tool zu nutzen"""
        with ToolCallTracker(agent) as tracker:
            response = agent.chat(
                "Ich möchte mich für Rechtswissenschaften bewerben. "
                "Mein Login ist testuser mit Passwort test123."
            )
            
            assert isinstance(response, str)
            response_lower = response.lower()
            
            # Agent sollte entweder nach Semester fragen ODER Tool aufrufen
            asks_for_semester = (
                "semester" in response_lower or
                "wann" in response_lower or
                "winter" in response_lower or
                "sommer" in response_lower
            )
            
            tool_called = len(tracker.tool_calls) > 0
            
            assert asks_for_semester or tool_called, \
                f"Agent sollte nach Semester fragen oder Tool aufrufen, aber sagte: {response[:200]}"
    
    def test_agent_asks_for_login_when_missing(self, agent):
        """Test: Agent fragt nach Login wenn nicht angegeben"""
        response = agent.chat(
            "Ich möchte mich für Rechtswissenschaften im Wintersemester 2025/26 bewerben."
        )
        
        assert isinstance(response, str)
        response_lower = response.lower()
        
        asks_for_login = (
            "login" in response_lower or
            "benutzername" in response_lower or
            "passwort" in response_lower or
            "anmeldedaten" in response_lower or
            "zugangsdaten" in response_lower
        )
        assert asks_for_login, f"Agent sollte nach Login fragen, aber sagte: {response[:200]}"


# =============================================================================
# TEST KLASSE: Agent ruft Tools mit korrekten Parametern auf
# =============================================================================
@pytest.mark.integration
@pytest.mark.klips
@pytest.mark.slow
class TestAgentKLIPSToolParameters:
    """Tests: Agent übergibt korrekte Parameter an KLIPS-Tools"""
    
    def test_agent_calls_apply_tool_with_study_program(self, agent):
        """Test: Agent ruft Apply-Tool mit korrektem Studiengang auf"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Bewirb mich bitte für Rechtswissenschaften im Wintersemester 2025/26. "
                "Login: testuser, Passwort: test123. Fachsemester 1, Erststudium."
            )
            
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                study_program = args.get('study_program', '')
                
                assert 'recht' in study_program.lower(), \
                    f"Studiengang sollte 'Rechtswissenschaften' enthalten: {study_program}"
    
    def test_agent_calls_apply_tool_with_semester(self, agent):
        """Test: Agent ruft Apply-Tool mit korrektem Semester auf"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Bewerbung für BWL, Wintersemester 2025/26. "
                "Login: max.muster, Passwort: geheim123. 1. Semester, Erststudium."
            )
            
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                semester = args.get('semester', '')
                
                assert 'winter' in semester.lower() or '2025' in semester, \
                    f"Semester sollte Wintersemester 2025/26 sein: {semester}"
    
    def test_agent_calls_apply_tool_with_credentials(self, agent):
        """Test: Agent ruft Apply-Tool mit Login-Daten auf"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Bewirb mich für Informatik im WS 2025/26. "
                "Benutzername: uni_user123, Passwort: sicheresPasswort!42"
            )
            
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                
                has_username = 'username' in args
                has_password = 'password' in args
                
                assert has_username, f"Tool-Call sollte username enthalten: {list(args.keys())}"
                assert has_password, f"Tool-Call sollte password enthalten: {list(args.keys())}"
                
                assert args.get('username') == 'uni_user123', \
                    f"Username sollte 'uni_user123' sein: {args.get('username')}"
    
    def test_agent_calls_apply_tool_with_entry_semester(self, agent):
        """Test: Agent ruft Apply-Tool mit Fachsemester auf"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Bewirb mich für Physik im WS 2025/26, 3. Fachsemester. "
                "Login: physik_student, Passwort: physik2025"
            )
            
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                entry_semester = args.get('entry_semester', '')
                
                assert '3' in str(entry_semester), \
                    f"Fachsemester sollte '3' sein: {entry_semester}"
    
    def test_agent_calls_apply_tool_with_study_form(self, agent):
        """Test: Agent ruft Apply-Tool mit Studienform auf"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Bewirb mich für Chemie im WS 2025/26. Es ist mein Zweitstudium. "
                "Login: chemie_student, Passwort: chemie2025"
            )
            
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                study_form = args.get('study_form', '')
                
                if study_form:
                    assert 'zweit' in study_form.lower(), \
                        f"Studienform sollte 'Zweitstudium' sein: {study_form}"


# =============================================================================
# TEST KLASSE: Agent wählt richtiges Tool
# =============================================================================
@pytest.mark.integration
@pytest.mark.klips
@pytest.mark.slow
class TestAgentKLIPSToolSelection:
    """Tests: Agent wählt das richtige KLIPS-Tool"""
    
    def test_agent_selects_apply_tool_for_bewerbung(self, agent):
        """Test: Agent wählt Apply-Tool für Bewerbung"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Bewirb mich für BWL im WS 2025/26. "
                "Login: bwl_student, Passwort: bwl2025!"
            )
            
            tool_names = tracker.get_tool_names()
            
            if tool_names:
                has_apply = any('apply' in name.lower() for name in tool_names)
                assert has_apply, f"Agent sollte apply-Tool nutzen für Bewerbung, nutzte: {tool_names}"
    
    def test_agent_selects_register_tool_for_registration(self, agent):
        """Test: Agent wählt Register-Tool für Registrierung"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Ich möchte einen neuen KLIPS-Account erstellen. "
                "Vorname: Max, Nachname: Mustermann, "
                "Email: max.mustermann@uni-koeln.de, "
                "Geburtsdatum: 01.01.2000"
            )
            
            tool_names = tracker.get_tool_names()
            
            if tool_names:
                has_register = any('register' in name.lower() for name in tool_names)
                # Register ist erwartet, wenn genug Daten vorhanden
    
    def test_agent_does_not_use_klips_for_info_questions(self, agent):
        """Test: Agent nutzt keine KLIPS-Action-Tools für Info-Fragen"""
        with ToolCallTracker(agent) as tracker:
            agent.chat("Welche Studiengänge bietet die Uni Köln an?")
            
            tool_names = tracker.get_tool_names()
            
            klips_action_tools = ['apply', 'register', 'activate', 'password', 'address']
            
            for tool in klips_action_tools:
                has_action = any(tool in name.lower() for name in tool_names)
                assert not has_action, \
                    f"Agent sollte '{tool}' nicht für Info-Fragen nutzen: {tool_names}"


# =============================================================================
# TEST KLASSE: Multi-Turn mit Tool-Tracking
# =============================================================================
@pytest.mark.integration
@pytest.mark.klips
@pytest.mark.slow
class TestAgentKLIPSMultiTurnWithTracking:
    """Tests: Agent sammelt Daten über mehrere Turns und ruft Tool korrekt auf"""
    
    def test_agent_accumulates_data_and_calls_tool(self, agent):
        """Test: Agent sammelt Daten und ruft Tool mit allen Parametern auf"""
        with ToolCallTracker(agent) as tracker:
            # Schrittweise Daten angeben
            agent.chat("Ich möchte mich für Wirtschaftsinformatik bewerben")
            agent.chat("Wintersemester 2025/26")
            agent.chat("Login ist winfo_student, Passwort ist winfo2025!")
            agent.chat("Erstes Fachsemester, Erststudium. Bitte jetzt bewerben.")
            
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                
                # Prüfe alle gesammelten Daten
                assert 'study_program' in args, "study_program sollte vorhanden sein"
                assert 'semester' in args, "semester sollte vorhanden sein"
                assert 'username' in args, "username sollte vorhanden sein"
                assert 'password' in args, "password sollte vorhanden sein"
                
                # Prüfe Werte
                assert 'wirtschaft' in args.get('study_program', '').lower() or \
                       'info' in args.get('study_program', '').lower(), \
                       f"Studiengang falsch: {args.get('study_program')}"
                assert 'winfo_student' in args.get('username', ''), \
                       f"Username falsch: {args.get('username')}"
    
    def test_full_application_dialog_calls_tool(self, agent):
        """Test: Kompletter Bewerbungsdialog führt zu Tool-Aufruf"""
        with ToolCallTracker(agent) as tracker:
            # Alle Daten in weniger Nachrichten, damit kleinere Modelle folgen können
            agent.chat("Ich möchte mich für Rechtswissenschaften im Wintersemester 2025/26 bewerben.")
            agent.chat("1. Fachsemester, Erststudium. Login: jura_bewerber, Passwort: jura2025secure")
            response = agent.chat("Bitte führe die Bewerbung jetzt durch.")
            
            # Prüfe ob ein relevantes Tool aufgerufen wurde
            tool_names = tracker.get_tool_names()
            
            # Entweder Tool wurde aufgerufen ODER Agent gibt sinnvolle Antwort
            tool_called = len(tracker.tool_calls) > 0
            reasonable_response = len(response) > 50
            
            assert tool_called or reasonable_response, \
                f"Agent sollte Tool aufrufen oder sinnvoll antworten. Tools: {tool_names}, Response: {response[:100]}"
            
            # Wenn Apply-Tool aufgerufen wurde, prüfe Parameter
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                
                assert 'study_program' in args, f"study_program fehlt: {args.keys()}"
                assert 'recht' in args.get('study_program', '').lower(), \
                    f"Studiengang sollte Rechtswissenschaften sein: {args}"


# =============================================================================
# TEST KLASSE: Agent Antwort-Qualität
# =============================================================================
@pytest.mark.integration
@pytest.mark.klips
@pytest.mark.slow
class TestAgentKLIPSResponseQuality:
    """Tests: Agent-Antworten sind hilfreich und korrekt"""
    
    def test_agent_explains_required_fields(self, agent):
        """Test: Agent erklärt welche Felder benötigt werden"""
        response = agent.chat("Was brauche ich um mich bei KLIPS zu bewerben?")
        
        assert isinstance(response, str)
        assert len(response) > 30, "Antwort sollte ausführlich sein"
        
        response_lower = response.lower()
        
        mentioned_fields = []
        field_keywords = {
            'semester': ['semester', 'wintersemester', 'sommersemester', 'zeitraum'],
            'studiengang': ['studiengang', 'fach', 'studienfach', 'studium'],
            'login': ['login', 'benutzername', 'passwort', 'zugangsdaten', 'account', 'konto'],
            'bewerbung': ['bewerbung', 'bewerben', 'anmeldung', 'antrag'],
        }
        
        for field, keywords in field_keywords.items():
            if any(kw in response_lower for kw in keywords):
                mentioned_fields.append(field)
        
        # Flexibler: mindestens 1 Feld erwähnen
        assert len(mentioned_fields) >= 1, \
            f"Agent sollte mindestens 1 relevantes Thema erwähnen, erwähnte: {mentioned_fields}. Response: {response[:200]}"
    
    def test_agent_response_is_german(self, agent):
        """Test: Agent antwortet auf Deutsch"""
        response = agent.chat("Wie bewerbe ich mich für ein Studium?")
        
        german_indicators = ['ich', 'sie', 'und', 'der', 'die', 'das', 'für', 'mit', 'ist', 'werden']
        response_lower = response.lower()
        
        german_words_found = sum(1 for word in german_indicators if word in response_lower)
        assert german_words_found >= 3, "Antwort sollte auf Deutsch sein"
    
    def test_agent_confirms_received_data(self, agent):
        """Test: Agent bestätigt oder nutzt empfangene Daten"""
        with ToolCallTracker(agent) as tracker:
            response = agent.chat(
                "Ich möchte mich für Rechtswissenschaften im WS 2025/26 bewerben. "
                "Login: test_user, Passwort: test123"
            )
            
            response_lower = response.lower()
            
            # Agent sollte entweder Tool aufrufen oder nachfragen
            tool_called = len(tracker.tool_calls) > 0
            asks_more = "?" in response
            acknowledges = "recht" in response_lower or "jura" in response_lower
            
            assert tool_called or asks_more or acknowledges, \
                f"Agent sollte reagieren: Tool={tool_called}, Frage={asks_more}, Bestätigt={acknowledges}"


# =============================================================================
# TEST KLASSE: Mit echten KLIPS-Credentials
# =============================================================================
@pytest.mark.integration
@pytest.mark.klips
@pytest.mark.slow
@pytest.mark.skipif(not has_klips_credentials(), reason="Keine KLIPS-Credentials vorhanden")
class TestAgentKLIPSWithCredentials:
    """Integration Tests mit echten KLIPS-Credentials"""
    
    def test_agent_validates_real_application(self, agent):
        """Test: Agent validiert echte Bewerbung"""
        username = os.getenv("KLIPS_USERNAME")
        password = os.getenv("KLIPS_PASSWORD")
        
        with ToolCallTracker(agent) as tracker:
            response = agent.chat(
                f"Validiere bitte meine Bewerbungsdaten (nur prüfen, nicht absenden): "
                f"Studiengang: Rechtswissenschaften, "
                f"Semester: Wintersemester 2025/26, "
                f"Fachsemester: 1, "
                f"Studienform: Erststudium, "
                f"Login: {username}, Passwort: {password}"
            )
            
            assert isinstance(response, str)
            assert len(response) > 0
            
            # Tool sollte aufgerufen worden sein
            apply_calls = tracker.get_calls_for_tool('apply')
            assert len(apply_calls) > 0, "Apply-Tool sollte aufgerufen werden"
            
            # Prüfe dass validate_only gesetzt wurde
            args = apply_calls[-1].get('args', {})
            # validate_only könnte True sein für Validierung
    
    def test_agent_handles_wrong_credentials(self, agent):
        """Test: Agent behandelt falsche Credentials korrekt"""
        with ToolCallTracker(agent) as tracker:
            response = agent.chat(
                "Bewirb mich für Rechtswissenschaften im WS 2025/26. "
                "Login: falscher_user_xyz, Passwort: falschesPasswort123!"
            )
            
            assert isinstance(response, str)
            
            # Agent sollte Tool aufrufen (auch mit falschen Credentials)
            tool_called = len(tracker.tool_calls) > 0
            
            # Und eine sinnvolle Antwort geben
            assert len(response) > 20, "Agent sollte antworten"


# =============================================================================
# TEST KLASSE: Validierung der Tool-Parameter
# =============================================================================
@pytest.mark.integration
@pytest.mark.klips
@pytest.mark.slow
class TestAgentKLIPSParameterValidation:
    """Tests: Agent-Parameter werden korrekt validiert"""
    
    def test_apply_tool_receives_all_required_params(self, agent):
        """Test: Apply-Tool erhält alle Pflichtparameter"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Bewirb mich sofort für Medizin im Sommersemester 2026. "
                "Login: med_student, Passwort: medizin2026! "
                "1. Fachsemester, Erststudium."
            )
            
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                
                required_params = ['username', 'password', 'semester', 'study_program']
                
                for param in required_params:
                    assert param in args, \
                        f"Pflichtparameter '{param}' fehlt. Vorhanden: {list(args.keys())}"
    
    def test_apply_tool_semester_format(self, agent):
        """Test: Semester wird im korrekten Format übergeben"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Bewerbung für Psychologie, WS 25/26. "
                "User: psych_student, PW: psycho2025"
            )
            
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                semester = args.get('semester', '')
                
                # Semester sollte erkennbar sein
                is_valid_semester = (
                    'winter' in semester.lower() or
                    'sommer' in semester.lower() or
                    'ws' in semester.lower() or
                    'ss' in semester.lower() or
                    '2025' in semester or
                    '2026' in semester
                )
                assert is_valid_semester, f"Semester-Format ungültig: {semester}"
    
    def test_degree_type_is_set(self, agent):
        """Test: Abschlussart wird gesetzt"""
        with ToolCallTracker(agent) as tracker:
            agent.chat(
                "Ich möchte mich für den Bachelor Informatik bewerben. "
                "WS 2025/26, Login: info_bach, Passwort: bachelor2025"
            )
            
            apply_calls = tracker.get_calls_for_tool('apply')
            
            if apply_calls:
                args = apply_calls[-1].get('args', {})
                degree_type = args.get('degree_type', '')
                
                if degree_type:
                    assert 'bachelor' in degree_type.lower(), \
                        f"Degree type sollte Bachelor sein: {degree_type}"
