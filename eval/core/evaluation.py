"""
Tool-Evaluierungslogik

Dieses Modul implementiert die Kernlogik zur Bewertung des Aufgabenerfolgs
basierend auf Tool-Aufrufsequenzen und Gold-Standard-Vergleichen.

Das Evaluierungsframework unterstützt:
- Einzelne Tool-Szenarien mit exaktem Argument-Matching
- Multi-Tool-Szenarien mit Sequenzvalidierung  
- Flexibles Argument-Matching mit Normalisierungsoptionen
- Detaillierte Fehlerursachen-Berichterstattung

Teil der Masterarbeit: KI-gestützter Universitätsassistent - Evaluierungsframework
Autor: Sebastian
Datum: 2024
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
import re


class ArgumentMatchMode(Enum):
    """
    Definiert, wie strikt Argumente abgeglichen werden sollen.
    
    - EXACT: Argumente müssen exakt übereinstimmen (Groß-/Kleinschreibung, Leerzeichen relevant)
    - NORMALIZED: Kleine Formatierungsunterschiede erlaubt (Leerzeichen, Groß-/Kleinschreibung)
    - SEMANTIC: Bedeutung muss übereinstimmen (z.B. "WiSe 2025" == "Wintersemester 2025")
    """
    EXACT = "exact"
    NORMALIZED = "normalized"
    SEMANTIC = "semantic"


@dataclass
class ToolCall:
    """
    Repräsentiert einen einzelnen Tool-Aufruf des KI-Agenten.
    
    Attribute:
        name: Name des aufgerufenen Tools
        arguments: Dictionary mit Argumentnamen und deren Werten
        timestamp: Optionaler Zeitstempel des Aufrufs
        result: Optionales Ergebnis des Tools
    """
    name: str
    arguments: Dict[str, Any]
    timestamp: Optional[float] = None
    result: Optional[str] = None
    
    def __post_init__(self):
        """Validiere Tool-Aufruf nach Initialisierung."""
        if not self.name:
            raise ValueError("Tool-Name darf nicht leer sein")
        if self.arguments is None:
            self.arguments = {}


@dataclass  
class GoldStandard:
    """
    Definiert die erwartete korrekte Tool-Nutzung für ein Szenario.
    
    Attribute:
        required_tools: Liste der Tools, die aufgerufen werden MÜSSEN (in Reihenfolge wenn ordered=True)
        required_arguments: Dict mit Tool-Namen und erforderlichen Argumenten
        forbidden_tools: Set von Tool-Namen, die NICHT aufgerufen werden dürfen
        optional_tools: Set von Tools, die aufgerufen werden können, aber nicht müssen
        ordered: Ob die erforderlichen Tools in exakter Reihenfolge aufgerufen werden müssen
        argument_match_mode: Wie strikt Argumentwerte abgeglichen werden
    """
    required_tools: List[str]
    required_arguments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    forbidden_tools: Set[str] = field(default_factory=set)
    optional_tools: Set[str] = field(default_factory=set)
    ordered: bool = False
    argument_match_mode: ArgumentMatchMode = ArgumentMatchMode.NORMALIZED

    def __post_init__(self):
        """Validiere Gold-Standard nach Initialisierung."""
        # Erlaube leere required_tools wenn forbidden_tools angegeben (negative Testfälle)
        if not self.required_tools and not self.forbidden_tools:
            raise ValueError("Mindestens ein erforderliches oder verbotenes Tool muss angegeben werden")
        # Konvertiere zu Set für forbidden_tools falls Liste übergeben
        if isinstance(self.forbidden_tools, list):
            self.forbidden_tools = set(self.forbidden_tools)
        if isinstance(self.optional_tools, list):
            self.optional_tools = set(self.optional_tools)


@dataclass
class EvaluationResult:
    """
    Result of evaluating a tool run against a gold standard.
    
    Attributes:
        success: Whether the task was completed successfully
        failure_reasons: List of reasons why the task failed (empty if success)
        matched_tools: Tools that were correctly called
        missing_tools: Required tools that were not called
        wrong_tools: Forbidden tools that were incorrectly called
        missing_arguments: Dict mapping tools to missing required arguments
        wrong_arguments: Dict mapping tools to arguments with wrong values
        extra_tools: Non-required tools that were called (informational)
    """
    success: bool
    failure_reasons: List[str] = field(default_factory=list)
    matched_tools: List[str] = field(default_factory=list)
    missing_tools: List[str] = field(default_factory=list)
    wrong_tools: List[str] = field(default_factory=list)
    missing_arguments: Dict[str, List[str]] = field(default_factory=dict)
    wrong_arguments: Dict[str, Dict[str, tuple]] = field(default_factory=dict)
    extra_tools: List[str] = field(default_factory=list)
    sequence_error: Optional[str] = None


def _normalize_string(value: str) -> str:
    """
    Normalize a string value for comparison.
    
    - Strips leading/trailing whitespace
    - Collapses multiple whitespace to single space
    - Converts to lowercase
    
    Args:
        value: String to normalize
        
    Returns:
        Normalized string
    """
    if not isinstance(value, str):
        return str(value)
    # Strip whitespace, collapse multiple spaces, lowercase
    normalized = re.sub(r'\s+', ' ', value.strip()).lower()
    return normalized


def _normalize_date(value: str) -> str:
    """
    Normalize date formats for comparison.
    
    Handles various German date formats:
    - 01.01.2000
    - 1.1.2000
    - 01/01/2000
    
    Args:
        value: Date string to normalize
        
    Returns:
        Normalized date string in DD.MM.YYYY format
    """
    # Try to extract day, month, year from various formats
    patterns = [
        r'(\d{1,2})[./](\d{1,2})[./](\d{4})',  # DD.MM.YYYY or DD/MM/YYYY
        r'(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})',  # YYYY-MM-DD
    ]
    
    for pattern in patterns:
        match = re.match(pattern, value.strip())
        if match:
            groups = match.groups()
            if len(groups[0]) == 4:  # YYYY-MM-DD format
                return f"{int(groups[2]):02d}.{int(groups[1]):02d}.{groups[0]}"
            else:  # DD.MM.YYYY format
                return f"{int(groups[0]):02d}.{int(groups[1]):02d}.{groups[2]}"
    
    return value.strip()


def _semantic_match_semester(expected: str, actual: str) -> bool:
    """
    Check if two semester strings refer to the same semester.
    
    Handles variations like:
    - "Wintersemester 2025/26" == "WiSe 2025/26" == "WS 2025"
    - "Sommersemester 2025" == "SoSe 2025" == "SS 2025"
    
    Args:
        expected: Expected semester string
        actual: Actual semester string provided
        
    Returns:
        True if both refer to same semester
    """
    def normalize_semester(s: str) -> tuple:
        s_lower = s.lower().strip()
        
        # Determine type (Winter or Summer)
        is_winter = any(x in s_lower for x in ['winter', 'wise', 'ws', 'wi'])
        is_summer = any(x in s_lower for x in ['sommer', 'summer', 'sose', 'ss', 'so'])
        
        if not is_winter and not is_summer:
            return None
            
        semester_type = 'winter' if is_winter else 'summer'
        
        # Extract year(s)
        years = re.findall(r'(\d{2,4})', s)
        if years:
            year = years[0]
            if len(year) == 2:
                year = '20' + year
            return (semester_type, year)
        
        return None
    
    exp_norm = normalize_semester(expected)
    act_norm = normalize_semester(actual)
    
    if exp_norm is None or act_norm is None:
        return False
        
    return exp_norm == act_norm


def _values_match(expected: Any, actual: Any, mode: ArgumentMatchMode) -> bool:
    """
    Compare two argument values based on the match mode.
    
    Args:
        expected: Expected value from gold standard
        actual: Actual value from tool call
        mode: How strictly to match
        
    Returns:
        True if values match according to the mode
    """
    # Handle None values
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False
    
    # Wildcard: "*" matches any non-empty value
    if expected == "*":
        return actual is not None and str(actual).strip() != ""
    
    # Handle exact mode
    if mode == ArgumentMatchMode.EXACT:
        return expected == actual
    
    # Convert to strings for comparison
    exp_str = str(expected)
    act_str = str(actual)
    
    # Handle normalized mode
    if mode == ArgumentMatchMode.NORMALIZED:
        return _normalize_string(exp_str) == _normalize_string(act_str)
    
    # Handle semantic mode
    if mode == ArgumentMatchMode.SEMANTIC:
        # First try normalized comparison
        if _normalize_string(exp_str) == _normalize_string(act_str):
            return True
        
        # Try semantic semester matching
        if _semantic_match_semester(exp_str, act_str):
            return True
        
        # Try date normalization
        if _normalize_date(exp_str) == _normalize_date(act_str):
            return True

        # Decimal separator equivalence: "1.5" == "1,5" (German vs English locale)
        def _normalize_decimal(s: str) -> str:
            # Only swap if it looks like a decimal number (digits, one separator, digits)
            import re as _re
            if _re.fullmatch(r'\d+[.,]\d+', s.strip()):
                return s.strip().replace(',', '.')
            return s
        if _normalize_decimal(exp_str) == _normalize_decimal(act_str):
            return True

        # Lower-cased forms used by all remaining checks
        exp_lower = exp_str.strip().lower()
        act_lower = act_str.strip().lower()

        # Gender equivalence: English/German forms
        _GENDER_VARIANTS = {
            "m": {"male", "männlich", "mann", "m"},
            "f": {"female", "weiblich", "frau", "f", "w"},
            "d": {"diverse", "divers", "d"},
        }
        for variants in _GENDER_VARIANTS.values():
            if exp_lower in variants and act_lower in variants:
                return True

        # Language name equivalence: English/Englisch, German/Deutsch
        _LANGUAGE_VARIANTS = {
            "english": {"english", "englisch"},
            "deutsch": {"deutsch", "german"},
        }
        for variants in _LANGUAGE_VARIANTS.values():
            if exp_lower in variants and act_lower in variants:
                return True

        # Nationality equivalence: adjective form ↔ country name
        # e.g. "deutsch" / "Deutschland" / "german" / "Germany"
        # Also strip "Staatsangehörigkeit" suffix: "ägyptische Staatsangehörigkeit" → "ägyptische"
        def _strip_nationality_suffix(s: str) -> str:
            return re.sub(
                r'\s+(staatsangehörigkeit|staatsbürger(?:in)?|citizen|bürger|national)$',
                '', s, flags=re.IGNORECASE
            ).strip()

        exp_nat = _strip_nationality_suffix(exp_lower)
        act_nat = _strip_nationality_suffix(act_lower)

        _NATIONALITY_VARIANTS = {
            "de": {"deutsch", "deutsche", "deutscher", "deutschen", "deutsches", "deutschland", "german", "germany"},
            "at": {"österreichisch", "österreichische", "österreich", "oesterreich", "austrian", "austria"},
            "ch": {"schweizerisch", "schweizer", "schweiz", "swiss", "switzerland"},
            "us": {"amerikanisch", "amerikanische", "usa", "united states", "american"},
            "gb": {
                "britisch", "britische", "britischer", "british",
                "großbritannien", "uk", "united kingdom",
                "vereinigtes königreich", "vereinigtes königreich (uk)",
            },
            "fr": {"französisch", "französische", "frankreich", "french", "france"},
            "eg": {
                "ägyptisch", "ägyptische", "ägyptischer", "egyptian",
                "ägypten", "egypt", "egyptisch", "egyptische",
            },
        }
        for variants in _NATIONALITY_VARIANTS.values():
            if exp_nat in variants and act_nat in variants:
                return True
            # also try original (non-stripped) forms
            if exp_lower in variants and act_lower in variants:
                return True

        # City / place name translations (EN ↔ DE)
        _CITY_VARIANTS = {
            "cairo":   {"cairo", "kairo"},
            "cologne": {"cologne", "köln"},
            "munich":  {"munich", "münchen"},
            "vienna":  {"vienna", "wien"},
            "rome":    {"rome", "rom"},
            "prague":  {"prague", "prag"},
            "warsaw":  {"warsaw", "warschau"},
            "beijing": {"beijing", "peking"},
            "moscow":  {"moscow", "moskau"},
        }
        for variants in _CITY_VARIANTS.values():
            if exp_lower in variants and act_lower in variants:
                return True

        # Country name translations (EN ↔ DE), separate from nationality adjectives
        _COUNTRY_NAME_VARIANTS = {
            "de": {"deutschland", "germany"},
            "at": {"österreich", "austria"},
            "ch": {"schweiz", "switzerland"},
            "us": {"usa", "united states", "vereinigte staaten"},
            "gb": {"großbritannien", "uk", "united kingdom"},
            "fr": {"frankreich", "france"},
            "eg": {"ägypten", "egypt"},
            "cn": {"china"},
            "jp": {"japan"},
            "in": {"indien", "india"},
            "ru": {"russland", "russia"},
            "tr": {"türkei", "turkey"},
            "it": {"italien", "italy"},
            "es": {"spanien", "spain"},
            "pl": {"polen", "poland"},
        }
        for variants in _COUNTRY_NAME_VARIANTS.values():
            if exp_lower in variants and act_lower in variants:
                return True

        # Education qualification equivalence
        # e.g. "Abitur" == "Allgemeine Hochschulreife"
        _EDUCATION_VARIANTS = {
            "ahr": {"abitur", "allgemeine hochschulreife", "allg. hochschulreife"},
            "fachabitur": {"fachabitur", "fachhochschulreife", "fachgebundene hochschulreife"},
        }
        for variants in _EDUCATION_VARIANTS.values():
            if exp_lower in variants and act_lower in variants:
                return True

        # Study program abbreviation / translation equivalence
        _PROGRAM_VARIANTS = {
            "bwl":  {"bwl", "betriebswirtschaftslehre", "betriebswirtschaft", "business administration"},
            "cs":   {"computer science", "informatik", "computerwissenschaften"},
            "winfo": {"wirtschaftsinformatik", "business informatics", "business information systems"},
            "mathe": {"mathematik", "mathematics", "math"},
            "physik": {"physik", "physics"},
            "bio":   {"biologie", "biology"},
            "chem":  {"chemie", "chemistry"},
            "vwl":   {"vwl", "volkswirtschaftslehre", "volkswirtschaft", "economics"},
            "jura":  {"jura", "rechtswissenschaft", "rechtswissenschaften", "law"},
        }
        for variants in _PROGRAM_VARIANTS.values():
            if exp_lower in variants and act_lower in variants:
                return True

        # Word-boundary containment: handles merged school+place ("Gymnasium Berlin" ↔ "Berlin")
        # and program+degree suffix ("Maschinenbau Bachelor" ↔ "Maschinenbau")
        if (act_lower.startswith(exp_lower + " ") or act_lower.endswith(" " + exp_lower)
                or exp_lower.startswith(act_lower + " ") or exp_lower.endswith(" " + act_lower)):
            return True

        return False
    
    return expected == actual


def evaluate_tool_run(
    tool_calls: List[ToolCall],
    gold_standard: GoldStandard
) -> EvaluationResult:
    """
    Evaluate a sequence of tool calls against a gold standard.
    
    This is the main evaluation function. It checks:
    1. All required tools were called
    2. No forbidden tools were called
    3. Required arguments are present with correct values
    4. Tool sequence matches if ordering is required
    
    Args:
        tool_calls: List of tool calls made by the agent
        gold_standard: The expected correct behavior
        
    Returns:
        EvaluationResult with success status and detailed information
        
    Example:
        >>> calls = [ToolCall(name="send_email", arguments={"subject": "Test", "body": "Hello"})]
        >>> gold = GoldStandard(
        ...     required_tools=["send_email"],
        ...     required_arguments={"send_email": {"subject": "Test", "body": "Hello"}}
        ... )
        >>> result = evaluate_tool_run(calls, gold)
        >>> print(result.success)
        True
    """
    result = EvaluationResult(success=True)
    
    # Extract called tool names
    called_tool_names = [call.name for call in tool_calls]
    called_tools_set = set(called_tool_names)
    
    # --- Check 1: No tool called at all ---
    if not tool_calls:
        # For forbidden-tools-only scenarios (no required tools), no call = correct behaviour
        if not gold_standard.required_tools:
            pass  # fall through to check 2 (forbidden tools)
        else:
            result.success = False
            result.failure_reasons.append("No tool was called")
            result.missing_tools = list(gold_standard.required_tools)
            return result
    
    # --- Check 2: Forbidden tools ---
    forbidden_called = called_tools_set & gold_standard.forbidden_tools
    if forbidden_called:
        result.success = False
        result.wrong_tools = list(forbidden_called)
        for tool in forbidden_called:
            result.failure_reasons.append(f"Forbidden tool '{tool}' was called")
    
    # --- Check 3: Required tools were called ---
    required_set = set(gold_standard.required_tools)
    missing = required_set - called_tools_set
    if missing:
        result.success = False
        result.missing_tools = list(missing)
        for tool in missing:
            result.failure_reasons.append(f"Required tool '{tool}' was not called")
    
    matched = required_set & called_tools_set
    result.matched_tools = list(matched)
    
    # --- Check 4: Tool sequence (if ordered) ---
    if gold_standard.ordered and len(gold_standard.required_tools) > 1:
        # Extract indices of required tools in the call sequence
        indices = []
        for required_tool in gold_standard.required_tools:
            for i, call in enumerate(tool_calls):
                if call.name == required_tool:
                    indices.append(i)
                    break
        
        # Check if indices are in ascending order
        if indices != sorted(indices):
            result.success = False
            result.sequence_error = f"Tools called in wrong order. Expected: {gold_standard.required_tools}"
            result.failure_reasons.append(result.sequence_error)
    
    # --- Check 5: Required arguments ---
    for tool_name, required_args in gold_standard.required_arguments.items():
        # Find the tool call for this tool
        matching_calls = [c for c in tool_calls if c.name == tool_name]
        
        if not matching_calls:
            # Tool wasn't called - already handled above
            continue
        
        # Use the last call for this tool (in case of retries)
        tool_call = matching_calls[-1]
        actual_args = tool_call.arguments
        
        # Check each required argument
        for arg_name, expected_value in required_args.items():
            if arg_name not in actual_args:
                # Missing argument
                result.success = False
                if tool_name not in result.missing_arguments:
                    result.missing_arguments[tool_name] = []
                result.missing_arguments[tool_name].append(arg_name)
                result.failure_reasons.append(
                    f"Missing required argument '{arg_name}' for tool '{tool_name}'"
                )
            else:
                actual_value = actual_args[arg_name]
                if not _values_match(expected_value, actual_value, gold_standard.argument_match_mode):
                    # Wrong argument value
                    result.success = False
                    if tool_name not in result.wrong_arguments:
                        result.wrong_arguments[tool_name] = {}
                    result.wrong_arguments[tool_name][arg_name] = (expected_value, actual_value)
                    result.failure_reasons.append(
                        f"Wrong value for argument '{arg_name}' in tool '{tool_name}': "
                        f"expected '{expected_value}', got '{actual_value}'"
                    )
    
    # --- Check 6: Extra tools (always a failure) ---
    all_known = required_set | gold_standard.optional_tools | gold_standard.forbidden_tools
    extra = called_tools_set - all_known
    if extra:
        result.extra_tools = list(extra)
        result.success = False
        for tool in extra:
            result.failure_reasons.append(f"Unexpected tool '{tool}' was called")
    
    return result


def is_task_successful(
    tool_calls: List[ToolCall],
    gold_standard: GoldStandard
) -> bool:
    """
    Convenience function to check if a task was successful.
    
    Args:
        tool_calls: List of tool calls made by the agent
        gold_standard: The expected correct behavior
        
    Returns:
        True if the task was successful, False otherwise
    """
    result = evaluate_tool_run(tool_calls, gold_standard)
    return result.success


def create_tool_call_from_dict(data: Dict[str, Any]) -> ToolCall:
    """
    Create a ToolCall from a dictionary (e.g., from JSON log).
    
    Args:
        data: Dictionary with 'name' and 'arguments' keys
        
    Returns:
        ToolCall instance
    """
    return ToolCall(
        name=data.get('name', ''),
        arguments=data.get('arguments', {}),
        timestamp=data.get('timestamp'),
        result=data.get('result')
    )


def parse_tool_calls_from_log(log_entries: List[Dict[str, Any]]) -> List[ToolCall]:
    """
    Parse a list of log entries into ToolCall objects.
    
    Args:
        log_entries: List of dictionaries representing tool calls
        
    Returns:
        List of ToolCall objects
    """
    return [create_tool_call_from_dict(entry) for entry in log_entries]
