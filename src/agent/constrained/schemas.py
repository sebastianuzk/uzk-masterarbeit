"""
Pydantic-Schemas für den Constrained Agent.

Definiert die strukturierten Input/Output-Schemata für alle Tool-Calls
sowie die TOOL_SCHEMAS-Mapping-Tabelle.
"""

import re
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, ValidationError, field_validator


# ============================================================================
# PYDANTIC SCHEMAS FÜR TOOL-CALLS
# ============================================================================

class ToolDecision(BaseModel):
    """Entscheidung des Agenten: Tool aufrufen oder direkt antworten."""
    action: str = Field(
        description="'tool' wenn ein Tool aufgerufen werden soll, 'respond' für direkte Antwort, 'insufficient_data' wenn Daten fehlen"
    )
    tool_names: Optional[List[str]] = Field(
        default=None,
        description="Liste der Tool-Namen (nur wenn action='tool'). Kann ein oder mehrere Tools enthalten."
    )
    reason: Optional[str] = Field(
        default=None,
        description="Kurze Begründung für die Entscheidung"
    )
    missing_fields: Optional[List[str]] = Field(
        default=None,
        description="Liste der fehlenden Pflichtfelder (nur wenn action='insufficient_data')"
    )

    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ('tool', 'respond', 'insufficient_data'):
            raise ValueError("action must be 'tool', 'respond', or 'insufficient_data'")
        return v

    @field_validator('tool_names')
    @classmethod
    def validate_tool_names(cls, v, info):
        """Stelle sicher, dass tool_names bei action='tool' vorhanden ist."""
        action = info.data.get('action')
        if action == 'tool' and not v:
            raise ValueError("tool_names muss gesetzt sein wenn action='tool'")
        # Bei insufficient_data ist tool_names optional (zeigt an welches Tool gemeint war)
        return v


class RegisterToolCall(BaseModel):
    """Schema für klips2_register Tool-Aufruf."""
    vorname: str = Field(description="Vorname der Person")
    nachname: str = Field(description="Nachname der Person")
    geschlecht: str = Field(description="männlich, weiblich oder divers")
    geburtsdatum: str = Field(description="Geburtsdatum im Format TT.MM.JJJJ")
    email: str = Field(description="E-Mail-Adresse mit @")
    staatsangehoerigkeit: str = Field(description="Staatsangehörigkeit")
    geburtsname: Optional[str] = Field(default=None, description="Geburtsname falls abweichend")
    sprache: str = Field(default="Deutsch", description="Deutsch oder Englisch")

    @field_validator('vorname', 'nachname')
    @classmethod
    def validate_not_empty(cls, v, info):
        """Verhindere leere Strings für kritische Felder."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} darf nicht leer sein")
        return v.strip()

    @field_validator('geburtsdatum')
    @classmethod
    def validate_date(cls, v):
        v = v.strip()
        patterns = [
            (r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', '{:02d}.{:02d}.{}'),
            (r'^(\d{1,2})/(\d{1,2})/(\d{4})$', '{:02d}.{:02d}.{}'),
            (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', '{:02d}.{:02d}.{}'),  # ISO
        ]
        for pattern, fmt in patterns:
            match = re.match(pattern, v)
            if match:
                groups = match.groups()
                if pattern.startswith(r'^(\d{4})'):  # ISO format
                    return fmt.format(int(groups[2]), int(groups[1]), groups[0])
                return fmt.format(int(groups[0]), int(groups[1]), groups[2])
        return v  # Return as-is, let tool handle validation

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError("E-Mail muss @ enthalten")
        return v.strip()

    @field_validator('geschlecht')
    @classmethod
    def normalize_gender(cls, v):
        v_lower = v.lower().strip()
        if v_lower in ('m', 'male', 'männlich', 'mann'):
            return 'männlich'
        if v_lower in ('f', 'w', 'female', 'weiblich', 'frau'):
            return 'weiblich'
        if v_lower in ('d', 'diverse', 'divers'):
            return 'divers'
        return v


class ApplyToolCall(BaseModel):
    """Schema für klips2_apply_study Tool-Aufruf."""
    username: str = Field(description="KLIPS2-Benutzername")
    password: str = Field(description="KLIPS2-Passwort")
    semester: str = Field(description="Zielsemester (z.B. Wintersemester 2024/25, WS 2024)")
    degree_type: str = Field(description="Bachelor, Master oder Promotionsstudium")
    study_program: str = Field(description="Name des Studiengangs (z.B. Informatik, Medizin)")
    entry_semester: str = Field(default="1", description="Fachsemester (Standard: 1)")
    study_form: str = Field(description="Studienform: Erststudium oder Zweitstudium")
    gender: str = Field(description="Geschlecht (männlich, weiblich, divers)")
    birth_place: str = Field(description="Geburtsort")
    birth_country: Optional[str] = Field(default="Deutschland", description="Geburtsland (Standard: Deutschland)")
    nationality: str = Field(description="Staatsangehörigkeit")
    hzb_date: str = Field(description="Datum der HZB (TT.MM.JJJJ, z.B. 15.06.2018)")
    hzb_type: str = Field(description="Art der HZB (z.B. Allgemeine Hochschulreife, Fachhochschulreife)")
    hzb_name: Optional[str] = Field(default="Abitur", description="Bezeichnung des Zeugnisses (Standard: Abitur)")
    hzb_grade: str = Field(description="Note der HZB (z.B. 2,3 oder 2.3)")
    hzb_school: Optional[str] = Field(default="Gymnasium", description="Name der Schule (Standard: Gymnasium)")
    hzb_country: Optional[str] = Field(default="Deutschland", description="Land der HZB (Standard: Deutschland)")
    hzb_place: str = Field(description="Ort/Kreis der HZB")
    # Optional
    street: Optional[str] = Field(default=None, description="Straße und Hausnummer")
    zip_code: Optional[str] = Field(default=None, description="Postleitzahl")
    city: Optional[str] = Field(default=None, description="Stadt")
    country: Optional[str] = Field(default="Deutschland", description="Land (Standard: Deutschland)")
    phone: Optional[str] = Field(default=None, description="Telefonnummer")
    prev_uni: Optional[str] = Field(default=None, description="Vorherige Hochschule (PFLICHT bei Zweitstudium)")
    prev_program: Optional[str] = Field(default=None, description="Vorheriger Studiengang (PFLICHT bei Zweitstudium)")
    prev_degree: Optional[str] = Field(default=None, description="Angestrebter/erreichter Abschluss (optional bei Zweitstudium)")
    prev_semesters: Optional[str] = Field(default=None, description="Anzahl Semester an vorheriger Hochschule (PFLICHT bei Zweitstudium)")

    @field_validator('username', 'password', 'nationality')
    @classmethod
    def validate_not_empty(cls, v, info):
        """Verhindere leere Strings für kritische Felder."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} darf nicht leer sein")
        return v.strip()

    @field_validator('gender')
    @classmethod
    def normalize_gender(cls, v):
        v_lower = v.lower().strip()
        if v_lower in ('m', 'male', 'männlich', 'mann'):
            return 'männlich'
        if v_lower in ('f', 'w', 'female', 'weiblich', 'frau'):
            return 'weiblich'
        if v_lower in ('d', 'diverse', 'divers'):
            return 'divers'
        return v

    @field_validator('study_form')
    @classmethod
    def normalize_study_form(cls, v):
        v_lower = v.lower().strip()
        if v_lower in ('erststudium', 'first', 'first-time', 'erstmals', 'first study', 'erster'):
            return 'Erststudium'
        if v_lower in ('zweitstudium', 'second', 'second degree', 'zweites', 'zweites studium'):
            return 'Zweitstudium'
        if v.strip():
            return v.strip().capitalize() if v.strip()[0].islower() else v.strip()
        return v


class ChangeAddressToolCall(BaseModel):
    """Schema für klips2_change_address Tool-Aufruf."""
    username: str = Field(description="KLIPS2-Benutzername")
    password: str = Field(description="KLIPS2-Passwort")
    street: str = Field(description="Straße und Hausnummer")
    zip_code: str = Field(description="Postleitzahl")
    city: str = Field(description="Stadt")
    country: str = Field(default="Deutschland", description="Land")

    @field_validator('username', 'password')
    @classmethod
    def validate_not_empty(cls, v, info):
        """Verhindere leere Strings für Zugangsdaten."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} darf nicht leer sein")
        return v.strip()

    @field_validator('zip_code')
    @classmethod
    def validate_zip(cls, v):
        v = v.strip()
        # Erlaube internationale Postleitzahlen/ZIP-Codes:
        # - 2 bis 10 Zeichen
        # - Buchstaben, Ziffern, Leerzeichen oder Bindestrich
        # Beispiele: "50678" (DE), "1010" (AT), "SW1A 1AA" (UK), "K1A 0B1" (CA)
        if not re.match(r'^[A-Za-z0-9 -]{2,10}$', v):
            raise ValueError("Postleitzahl/ZIP muss 2-10 Zeichen (Buchstaben, Ziffern, Leerzeichen oder '-') enthalten")
        return v


class ChangePasswordToolCall(BaseModel):
    """Schema für klips2_change_password Tool-Aufruf."""
    username: str = Field(description="Benutzername")
    password: str = Field(description="Aktuelles Passwort")
    new_password: str = Field(description="Neues Passwort")

    @field_validator('username', 'password', 'new_password')
    @classmethod
    def validate_not_empty(cls, v, info):
        """Verhindere leere Strings für Zugangsdaten."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} darf nicht leer sein")
        return v.strip()


class CourseDetailsToolCall(BaseModel):
    """Schema für klips2_get_course_details Tool-Aufruf."""
    course_id: str = Field(description="Kursnummer")
    semester: Optional[str] = Field(default=None, description="Semester")


class SearchToolCall(BaseModel):
    """Schema für Suchanfragen (RAG, DuckDuckGo)."""
    query: str = Field(description="Suchanfrage")


class WebScraperToolCall(BaseModel):
    """Schema für web_scraper Tool-Aufruf."""
    url: str = Field(description="URL der Webseite")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            v = 'https://' + v
        return v


class EmailToolCall(BaseModel):
    """Schema für send_email Tool-Aufruf."""
    subject: str = Field(description="Betreff der E-Mail")
    body: str = Field(description="Nachrichteninhalt")


class DirectResponse(BaseModel):
    """Schema für direkte Antwort ohne Tool-Aufruf."""
    response: str = Field(description="Antwort an den Nutzer")
    missing_info: Optional[List[str]] = Field(
        default=None,
        description="Liste fehlender Informationen falls nachgefragt werden muss"
    )


# Mapping Tool-Name -> Schema
TOOL_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "klips2_register": RegisterToolCall,
    "klips2_apply_study": ApplyToolCall,
    "klips2_change_address": ChangeAddressToolCall,
    "klips2_change_password": ChangePasswordToolCall,
    "klips2_get_course_details": CourseDetailsToolCall,
    "university_knowledge_search": SearchToolCall,
    "duckduckgo_search": SearchToolCall,
    "web_scraper": WebScraperToolCall,
    "send_email": EmailToolCall,
}
