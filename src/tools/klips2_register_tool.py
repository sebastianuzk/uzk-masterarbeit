"""
KLIPS2 Registrierungs-Tool für den Autonomen Chatbot-Agenten
Ermöglicht die automatische Erstellung eines Basis-Accounts auf KLIPS2
"""
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class KLIPS2RegisterInput(BaseModel):
    """Input für KLIPS2 Registrierung"""
    vorname: str = Field(description="Vorname der Person")
    nachname: str = Field(description="Familien- oder Nachname der Person")
    geschlecht: str = Field(description="Geschlecht: 'männlich', 'weiblich' oder 'divers'")
    geburtsdatum: str = Field(description="Geburtsdatum im Format TT.MM.JJJJ (z.B. 15.03.1995)")
    email: str = Field(description="E-Mail-Adresse für den Account (z.B. john.doe@example.com)")
    staatsangehoerigkeit: str = Field(description="Staatsangehörigkeit (z.B. 'Deutschland', 'Österreich')")
    geburtsname: Optional[str] = Field(default=None, description="Geburtsname (optional, falls abweichend vom Nachnamen)")
    sprache: str = Field(default="Deutsch", description="Bevorzugte Sprache: 'Deutsch' oder 'Englisch'")


class KLIPS2RegisterTool(BaseTool):
    """Tool für KLIPS2 Account-Registrierung"""
    
    name: str = "klips2_register"
    description: str = """Nützlich zum Erstellen eines neuen Basis-Accounts auf KLIPS2 (Universitätssystem).
    Verwende dieses Tool, wenn jemand einen neuen Account auf KLIPS2 erstellen möchte.
    
    WICHTIG: 
    - Dieses Tool erstellt einen Basis-Account für Personen, die NOCH NIE an der Universität zu Köln studiert haben
    - Für aktuelle Studierende/Beschäftigte: Verwenden Sie Ihren bestehenden S-Mail/Uni-Account
    - Für ehemalige Studierende: Der Account bleibt 1 Jahr nach Exmatrikulation gültig
    
    Erforderliche Informationen:
    - Vorname und Nachname
    - Geschlecht (männlich/weiblich/divers)
    - Geburtsdatum (TT.MM.JJJJ)
    - E-Mail-Adresse
    - Staatsangehörigkeit
    - Optional: Geburtsname, Sprache (Standard: Deutsch)
    """
    args_schema: Type[BaseModel] = KLIPS2RegisterInput
    
    def _validate_date(self, date_str: str) -> bool:
        """Validiere Datumsformat TT.MM.JJJJ"""
        try:
            datetime.strptime(date_str, "%d.%m.%Y")
            return True
        except ValueError:
            return False
    
    def _validate_email(self, email: str) -> bool:
        """Einfache E-Mail-Validierung"""
        if "@" not in email:
            return False
        parts = email.split("@")
        if len(parts) != 2:
            return False
        local, domain = parts
        if not local or not domain:
            return False
        if "." not in domain:
            return False
        return True
    
    def _map_gender(self, geschlecht: str) -> str:
        """Mappe Geschlecht auf KLIPS2-Werte"""
        geschlecht_lower = geschlecht.lower().strip()
        # Prüfe zuerst auf "female" wegen "male" substring
        if "weiblich" in geschlecht_lower or "female" in geschlecht_lower:
            return "W"
        elif geschlecht_lower in ["w", "f"]:
            return "W"
        elif "männlich" in geschlecht_lower or "male" in geschlecht_lower:
            return "M"
        elif geschlecht_lower == "m":
            return "M"
        elif "divers" in geschlecht_lower or "diverse" in geschlecht_lower:
            return "D"
        elif geschlecht_lower == "d":
            return "D"
        else:
            return "M"  # Default
    
    def _map_language(self, sprache: str) -> str:
        """Mappe Sprache auf KLIPS2-Werte"""
        sprache_lower = sprache.lower()
        if "english" in sprache_lower or "englisch" in sprache_lower:
            return "en"
        else:
            return "de"
    
    def _run(
        self,
        vorname: str,
        nachname: str,
        geschlecht: str,
        geburtsdatum: str,
        email: str,
        staatsangehoerigkeit: str,
        geburtsname: Optional[str] = None,
        sprache: str = "Deutsch"
    ) -> str:
        """Führe KLIPS2-Registrierung aus"""
        
        # Validierungen
        if not self._validate_date(geburtsdatum):
            return f"❌ Fehler: Ungültiges Datumsformat. Bitte verwende TT.MM.JJJJ (z.B. 15.03.1995)"
        
        if not self._validate_email(email):
            return f"❌ Fehler: Ungültige E-Mail-Adresse: {email}"
        
        try:
            # HTTP-Session für Cookie-Management
            session = requests.Session()
            
            # User-Agent Header
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # 1. Hole Registrierungsseite, um CSRF-Token und Formular-Parameter zu extrahieren
            register_url = "https://klips2.uni-koeln.de/co/wbSelbstRegPerson.register"
            response = session.get(register_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Suche nach Formular
            form = soup.find('form')
            if not form:
                return "❌ Fehler: Registrierungsformular konnte nicht gefunden werden"
            
            # Extrahiere versteckte Felder (CSRF-Tokens etc.)
            hidden_fields = {}
            for hidden_input in form.find_all('input', type='hidden'):
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    hidden_fields[name] = value
            
            # 2. Bereite Formulardaten vor
            form_data = {
                **hidden_fields,  # Versteckte Felder
                'pVorname': vorname,
                'pNachname': nachname,
                'pGeschlecht': self._map_gender(geschlecht),
                'pGeburtsdatum': geburtsdatum,
                'pEmail': email,
                'pStaatsangehoerigkeit': staatsangehoerigkeit,
                'pSprache': self._map_language(sprache),
            }
            
            # Optional: Geburtsname
            if geburtsname:
                form_data['pGeburtsname'] = geburtsname
            
            # 3. Sende Registrierungsanfrage
            submit_url = "https://klips2.uni-koeln.de/co/wbSelbstRegPerson.registerVerifyAndSave"
            
            # Erstelle Zusammenfassung für Benutzer (OHNE tatsächlich zu senden)
            summary = f"""
📋 **KLIPS2 Registrierungs-Anfrage vorbereitet**

**Persönliche Daten:**
- Vorname: {vorname}
- Nachname: {nachname}
- Geschlecht: {geschlecht}
- Geburtsdatum: {geburtsdatum}
- E-Mail: {email}
- Staatsangehörigkeit: {staatsangehoerigkeit}
- Geburtsname: {geburtsname if geburtsname else 'nicht angegeben'}
- Sprache: {sprache}

⚠️ **WICHTIGER HINWEIS:**
Aus Sicherheitsgründen führe ich die tatsächliche Registrierung NICHT automatisch aus.

**Nächste Schritte für den Benutzer:**
1. Bitte besuchen Sie: {register_url}
2. Füllen Sie das Formular mit den obigen Daten aus
3. Prüfen Sie alle Angaben sorgfältig
4. Klicken Sie auf "Daten bestätigen"
5. Sie erhalten eine Bestätigungs-E-Mail an: {email}
6. Folgen Sie dem Link in der E-Mail, um die Registrierung abzuschließen

**Hinweise:**
- Haben Sie bereits einen Basis-Account? Nutzen Sie die "Passwort vergessen"-Funktion
- Sind Sie bereits immatrikuliert/beschäftigt? Nutzen Sie Ihren S-Mail/Uni-Account
- Waren Sie früher an der Uni Köln? Ihr Account bleibt 1 Jahr gültig

Bei Problemen wenden Sie sich an den ITCC-Helpdesk: https://uni.koeln/MQPZL
"""
            
            return summary
            
        except requests.exceptions.RequestException as e:
            return f"❌ Fehler beim Verbinden mit KLIPS2: {str(e)}\n\nBitte versuchen Sie es später erneut oder besuchen Sie direkt: https://klips2.uni-koeln.de/co/wbSelbstRegPerson.register"
        
        except Exception as e:
            return f"❌ Fehler bei der Registrierungsvorbereitung: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Asynchrone Ausführung (nicht implementiert)"""
        raise NotImplementedError("Asynchrone Ausführung nicht unterstützt")


def create_klips2_register_tool() -> KLIPS2RegisterTool:
    """Factory-Funktion für das KLIPS2 Registrierungs-Tool"""
    return KLIPS2RegisterTool()
