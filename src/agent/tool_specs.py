"""
Gemeinsame Tool-Spezifikationen für alle Agenten
Diese Spezifikationen definieren Parameter und Beschreibungen für Tools
und werden von verschiedenen Agent-Implementierungen verwendet.
"""

# Tool-Parameter-Spezifikationen
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
            "degree_type": "Bachelor, Master oder Promotionsstudium",
            "study_program": "Name des Studiengangs (z.B. Informatik, Medizin)",
            "gender": "Geschlecht (männlich, weiblich, divers)",
            "birth_place": "Geburtsort",
            "nationality": "Staatsangehörigkeit",
            "hzb_date": "Datum der HZB (TT.MM.JJJJ, z.B. 15.06.2018)",
            "hzb_type": "Art der HZB (z.B. Allgemeine Hochschulreife, Fachhochschulreife)",
            "hzb_grade": "Note der HZB (z.B. 2,3 oder 2.3)",
            "hzb_place": "Ort/Kreis der HZB",
            "study_form": "Studienform: Erststudium oder Zweitstudium"
        },
        "optional_params": {
            "entry_semester": "Fachsemester (Standard: 1)",
            "birth_country": "Geburtsland (Standard: Deutschland)",
            "hzb_name": "Bezeichnung des Zeugnisses (Standard: Abitur)",
            "hzb_school": "Name der Schule (Standard: Gymnasium)",
            "hzb_country": "Land der HZB (Standard: Deutschland)",
            "street": "Straße und Hausnummer",
            "zip_code": "Postleitzahl",
            "city": "Stadt",
            "country": "Land (Standard: Deutschland)",
            "phone": "Telefonnummer",
            "prev_uni": "Vorherige Hochschule (PFLICHT bei Zweitstudium)",
            "prev_program": "Vorheriger Studiengang (PFLICHT bei Zweitstudium)",
            "prev_degree": "Angestrebter/erreichter Abschluss (optional bei Zweitstudium)",
            "prev_semesters": "Anzahl Semester an vorheriger Hochschule (PFLICHT bei Zweitstudium)"
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
        "optional_params": {}
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


def get_tool_spec(tool_name: str) -> dict:
    """
    Gibt die Spezifikation für ein bestimmtes Tool zurück.
    
    Args:
        tool_name: Name des Tools
        
    Returns:
        Dictionary mit Tool-Spezifikation
    """
    return TOOL_SPECS.get(tool_name, {})


def format_tool_params_for_prompt(tool_name: str) -> str:
    """
    Formatiert Tool-Parameter für System-Prompts.
    
    Args:
        tool_name: Name des Tools
        
    Returns:
        Formatierter String mit Tool-Parametern
    """
    spec = get_tool_spec(tool_name)
    if not spec:
        return ""
    
    lines = [f"**{tool_name}**"]
    lines.append(f"  {spec.get('description', '')}")
    
    if spec.get('required_params'):
        lines.append("  Pflichtparameter:")
        for param, desc in spec['required_params'].items():
            lines.append(f"    - {param}: {desc}")
    
    if spec.get('optional_params'):
        lines.append("  Optionale Parameter:")
        for param, desc in spec['optional_params'].items():
            lines.append(f"    - {param}: {desc}")
    
    return "\n".join(lines)
