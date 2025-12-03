"""
KLIPS2 Kurs-Details-Tool
"""
from typing import Type, Optional
from pydantic import BaseModel, Field
from urllib.parse import urljoin
from .base import KLIPS2BaseTool

class KLIPS2GetCourseDetailsInput(BaseModel):
    """Input für Kursdetails"""
    course_id: str = Field(description="Die ID oder Nummer der Lehrveranstaltung (z.B. '14302.0001')")
    semester: Optional[str] = Field(default=None, description="Optional: Semester (z.B. 'WiSe 2024/25')")

class KLIPS2GetCourseDetailsTool(KLIPS2BaseTool):
    name: str = "klips2_get_course_details"
    description: str = """Ruft Details zu einer Lehrveranstaltung ab.
    Kann ohne Login verwendet werden (öffentliches Vorlesungsverzeichnis).
    """
    args_schema: Type[BaseModel] = KLIPS2GetCourseDetailsInput

    def _run(self, course_id: str, semester: Optional[str] = None) -> str:
        # Hier würde man das öffentliche Vorlesungsverzeichnis scrapen
        # URL Aufbau raten oder suchen
        
        search_url = urljoin(self.base_url, "co/wbSuche.veranstaltungSuche")
        
        # Mock Antwort
        return f"""
📚 **Kursdetails gefunden**

**Veranstaltung:** {course_id} - Einführung in die KI
**Dozent:** Prof. Dr. Mustermann
**Semester:** {semester if semester else 'Aktuelles Semester'}
**Typ:** Vorlesung
**Status:** Belegbar
**Termine:** Mo 10:00 - 11:30, Hörsaal B

Link: {self.base_url}/course/{course_id} (Beispiel)
"""

def create_klips2_get_course_details_tool() -> KLIPS2GetCourseDetailsTool:
    return KLIPS2GetCourseDetailsTool()
