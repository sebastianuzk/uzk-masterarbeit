"""
KLIPS2 Registrierungs-Tool für den Autonomen Chatbot-Agenten
Führt die vollständige 3-Schritt-Registrierung eines Basis-Accounts auf KLIPS2 durch
"""
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from urllib.parse import urljoin
import re


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
    """Tool für KLIPS2 Account-Registrierung (vollständige Durchführung)"""
    
    name: str = "klips2_register"
    description: str = """Nützlich zum Erstellen eines neuen Basis-Accounts auf KLIPS2 (Universitätssystem).
    Verwende dieses Tool, wenn jemand einen neuen Account auf KLIPS2 erstellen möchte.
    
    WICHTIG: 
    - Dieses Tool führt die vollständige Registrierung automatisch durch (3 Schritte)
    - Für einen Basis-Account: nur für Personen, die NOCH NIE an der Universität zu Köln studiert haben
    - Für aktuelle Studierende/Beschäftigte: Verwenden Sie Ihren bestehenden S-Mail/Uni-Account
    - Für ehemalige Studierende: Der Account bleibt 1 Jahr nach Exmatrikulation gültig
    
    Erforderliche Informationen:
    - Vorname und Nachname
    - Geschlecht (männlich/weiblich/divers)
    - Geburtsdatum (TT.MM.JJJJ)
    - E-Mail-Adresse
    - Staatsangehörigkeit
    - Optional: Geburtsname, Sprache (Standard: Deutsch)
    
    Der Registrierungsprozess umfasst 3 Schritte:
    1. Formular holen und erste Daten senden
    2. Bestätigungsseite - "Daten abschicken" klicken
    3. Finales Event-Processing für E-Mail-Versand
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
            return "X"  # KLIPS2 verwendet X, nicht D
        elif geschlecht_lower in ["d", "x"]:
            return "X"
        else:
            return "M"  # Default
    
    def _map_language(self, sprache: str) -> str:
        """Mappe Sprache auf KLIPS2-Werte"""
        sprache_lower = sprache.lower()
        if "english" in sprache_lower or "englisch" in sprache_lower:
            return "2"  # KLIPS2 verwendet numerische IDs
        else:
            return "1"  # Deutsch
    
    def _map_nationality(self, staatsangehoerigkeit: str) -> str:
        """Mappe Staatsangehörigkeit auf KLIPS2 numerische Codes"""
        # Häufigste Länder-Codes (aus KLIPS2-Formular extrahiert)
        nationality_map = {
            "deutschland": "56",
            "germany": "56",
            "österreich": "168",
            "austria": "168",
            "schweiz": "192",
            "switzerland": "192",
            "niederlande": "160",
            "netherlands": "160",
            "belgien": "34",
            "belgium": "34",
            "frankreich": "68",
            "france": "68",
            "polen": "178",
            "poland": "178",
            "italien": "98",
            "italy": "98",
            "spanien": "201",
            "spain": "201",
        }
        
        staatsangehoerigkeit_lower = staatsangehoerigkeit.lower().strip()
        return nationality_map.get(staatsangehoerigkeit_lower, "56")  # Default: Deutschland
    
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
        """Führe vollständige KLIPS2-Registrierung durch (3 Schritte)"""
        
        # Validierungen
        if not self._validate_date(geburtsdatum):
            return f"❌ Fehler: Ungültiges Datumsformat. Bitte verwende TT.MM.JJJJ (z.B. 15.03.1995)"
        
        if not self._validate_email(email):
            return f"❌ Fehler: Ungültige E-Mail-Adresse: {email}"
        
        try:
            # HTTP-Session für Cookie-Management (wichtig für mehrstufigen Prozess)
            session = requests.Session()
            
            # User-Agent Header
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            register_url = "https://klips2.uni-koeln.de/co/wbSelbstRegPerson.register"
            
            # ===== SCHRITT 1: Formular holen und erste Daten senden =====
            response = session.get(register_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Suche nach Formular
            form = soup.find('form')
            if not form:
                return "❌ Fehler: Registrierungsformular konnte nicht gefunden werden. KLIPS2 ist möglicherweise nicht erreichbar."
            
            # Extrahiere Submit-URL vom Confirm-Button
            submit_link = soup.find('a', {'id': 'idBtnRegConfirm'})
            if submit_link and submit_link.get('href'):
                submit_url = urljoin(register_url, submit_link.get('href'))
            else:
                form_action = form.get('action')
                submit_url = urljoin(register_url, form_action) if form_action else register_url
            
            # Extrahiere versteckte Felder (CSRF-Tokens etc.)
            hidden_fields = {}
            for hidden_input in form.find_all('input', type='hidden'):
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    hidden_fields[name] = value
            
            # Extrahiere Feldnamen-Mapping (KLIPS2 verwendet obfuskierte Feldnamen)
            field_mapping = {}
            inputs = form.find_all(['input', 'select'])
            
            for inp in inputs:
                field_name = inp.get('name')
                field_type = inp.get('type', inp.name)
                
                if not field_name or field_type == 'hidden':
                    continue
                
                # Suche Label für das Feld
                field_id = inp.get('id')
                if field_id:
                    label_elem = soup.find('label', {'for': field_id})
                    if label_elem:
                        label_text = label_elem.get_text(strip=True).lower()
                        
                        # Mapping basierend auf erkannten Labels
                        if 'vorname' in label_text or 'first name' in label_text:
                            field_mapping['vorname'] = field_name
                        elif 'nachname' in label_text or 'familienname' in label_text or 'familien' in label_text:
                            field_mapping['nachname'] = field_name
                        elif 'geschlecht' in label_text or 'gender' in label_text:
                            field_mapping['geschlecht'] = field_name
                        elif 'geburtsdatum' in label_text or 'birth' in label_text:
                            field_mapping['geburtsdatum'] = field_name
                        elif 'e-mail' in label_text or 'email' in label_text:
                            field_mapping['email'] = field_name
                        elif 'staatsangehörigkeit' in label_text or 'nationality' in label_text:
                            field_mapping['staatsangehoerigkeit'] = field_name
                        elif 'geburtsname' in label_text:
                            field_mapping['geburtsname'] = field_name
                        elif 'sprache' in label_text or 'language' in label_text:
                            field_mapping['sprache'] = field_name
            
            # Prüfe ob alle erforderlichen Felder gefunden wurden
            required_fields = ['vorname', 'nachname', 'geschlecht', 'geburtsdatum', 'email']
            missing_fields = [f for f in required_fields if f not in field_mapping]
            
            if missing_fields:
                return f"❌ Fehler: Konnte folgende Formularfelder nicht identifizieren: {', '.join(missing_fields)}\n\nDas KLIPS2-Formular hat sich möglicherweise geändert."
            
            # Bereite Formulardaten vor
            form_data = {**hidden_fields}
            
            # Füge Daten mit gemappten Feldnamen und korrekten KLIPS2-Codes hinzu
            form_data[field_mapping['vorname']] = vorname
            form_data[field_mapping['nachname']] = nachname
            form_data[field_mapping['geschlecht']] = self._map_gender(geschlecht)
            form_data[field_mapping['geburtsdatum']] = geburtsdatum
            form_data[field_mapping['email']] = email
            form_data[field_mapping['staatsangehoerigkeit']] = self._map_nationality(staatsangehoerigkeit)
            form_data[field_mapping['sprache']] = self._map_language(sprache)
            
            if geburtsname and 'geburtsname' in field_mapping:
                form_data[field_mapping['geburtsname']] = geburtsname
            
            # Sende Schritt 1
            step1_response = session.post(
                submit_url,
                data=form_data,
                headers=headers,
                timeout=15,
                allow_redirects=True
            )
            step1_response.raise_for_status()
            
            # Prüfe ob Bestätigungsseite erreicht wurde
            if 'idBtnRegSend' not in step1_response.text:
                return f"""
❌ **Registrierung fehlgeschlagen in Schritt 1**

Die Bestätigungsseite wurde nicht erreicht.

**Mögliche Gründe:**
- E-Mail-Adresse bereits registriert
- Ungültige Eingabedaten
- KLIPS2-System-Fehler

**Empfehlung:**
Versuchen Sie die manuelle Registrierung: {register_url}
Oder kontaktieren Sie den ITCC-Helpdesk: https://uni.koeln/MQPZL
"""
            
            # ===== SCHRITT 2: "Daten abschicken" klicken =====
            # Extrahiere den Submit-Link aus der Antwort
            match = re.search(r'href="([^"]*pMaskAction=S[^"]*)"', step1_response.text)
            if not match:
                return "❌ Fehler in Schritt 2: Submit-Link nicht gefunden"
            
            final_submit_url = urljoin(register_url, match.group(1))
            final_submit_url = final_submit_url.replace('&amp;', '&')
            
            step2_response = session.post(
                final_submit_url,
                data=form_data,
                headers=headers,
                timeout=15,
                allow_redirects=True
            )
            step2_response.raise_for_status()
            
            # Extrahiere vSupportCode für Schritt 3
            support_code_match = re.search(r'vSupportCode\s*=\s*(\d+)', step2_response.text)
            if not support_code_match:
                return "❌ Fehler in Schritt 2: Support-Code nicht erhalten"
            
            support_code = support_code_match.group(1)
            
            # ===== SCHRITT 3: Finale Event-Verarbeitung (E-Mail-Versand) =====
            event_url = urljoin(register_url, f"wbSelbstRegPerson.cbProcessIDMRegisterEvent?pSupportCode={support_code}")
            
            step3_response = session.get(
                event_url,
                headers=headers,
                timeout=15,
                allow_redirects=True
            )
            step3_response.raise_for_status()
            
            # Prüfe Erfolg
            response_lower = step3_response.text.lower()
            
            # Suche nach Erfolgs-Indikatoren
            success_indicators = ['versendet', 'bestätigung', 'aktivierung', 'e-mail wurde', 'bestätigungs-e-mail']
            error_indicators = ['fehler', 'error', 'bereits registriert', 'ungültig']
            
            has_success = any(indicator in response_lower for indicator in success_indicators)
            has_error = any(indicator in response_lower for indicator in error_indicators)
            
            if has_error and not has_success:
                return f"""
❌ **KLIPS2 Registrierung fehlgeschlagen**

**Status:** Fehler in Schritt 3 (Finale Verarbeitung)

**Versuchte Daten:**
- Vorname: {vorname}
- Nachname: {nachname}
- E-Mail: {email}
- Geburtsdatum: {geburtsdatum}

**Mögliche Ursachen:**
- E-Mail-Adresse bereits verwendet
- System-Fehler bei der E-Mail-Zustellung
- Temporäres Problem auf KLIPS2-Server

**Empfehlung:**
1. Prüfen Sie, ob die E-Mail-Adresse bereits registriert ist
2. Versuchen Sie die "Passwort vergessen"-Funktion
3. Kontaktieren Sie den ITCC-Helpdesk: https://uni.koeln/MQPZL
"""
            
            # Erfolgreiche Registrierung!
            mailinator_link = ""
            if '@mailinator.com' in email:
                email_user = email.split('@')[0]
                mailinator_link = f"\n🔗 Mailinator-Postfach: https://www.mailinator.com/v4/public/inboxes.jsp?to={email_user}"
            
            return f"""
✅✅✅ **KLIPS2 Registrierung erfolgreich abgeschlossen!** ✅✅✅

**Registrierte Daten:**
- Vorname: {vorname}
- Nachname: {nachname}
- Geschlecht: {geschlecht}
- Geburtsdatum: {geburtsdatum}
- E-Mail: {email}
- Staatsangehörigkeit: {staatsangehoerigkeit}
- Geburtsname: {geburtsname if geburtsname else 'nicht angegeben'}
- Sprache: {sprache}

**Registrierungsprozess:**
✅ Schritt 1: Formular ausgefüllt und gesendet
✅ Schritt 2: Bestätigung durchgeführt  
✅ Schritt 3: E-Mail-Versand initiiert

📧 **Nächste Schritte:**

1. **Prüfen Sie Ihr E-Mail-Postfach: {email}**
   - Sie sollten eine Bestätigungs-E-Mail von KLIPS2 erhalten haben
   - Die E-Mail enthält einen Aktivierungslink
   - **Wichtig:** Prüfen Sie auch Ihren SPAM-Ordner!

2. **Klicken Sie auf den Aktivierungslink**
   - Der Link ist zeitlich begrenzt
   - Folgen Sie den Anweisungen zur Account-Aktivierung

3. **Nach der Aktivierung:**
   - Sie können sich mit Ihrer E-Mail-Adresse bei KLIPS2 anmelden
   - Sie müssen ein Passwort festlegen{mailinator_link}

⚠️ **Wichtige Hinweise:**
- Der Aktivierungslink ist nur für eine begrenzte Zeit gültig
- Falls Sie keine E-Mail erhalten: Prüfen Sie SPAM-Ordner
- Bei Problemen: ITCC-Helpdesk https://uni.koeln/MQPZL (Tel: +49 221 470-8888)

🎓 **Account-Typ:** Basis-Account (für Personen ohne aktuelle Uni-Zugehörigkeit)
"""
            
        except requests.exceptions.RequestException as e:
            return f"❌ Fehler beim Verbinden mit KLIPS2: {str(e)}\n\nMögliche Ursachen:\n- Keine Internetverbindung\n- KLIPS2-Server nicht erreichbar\n- Zeitüberschreitung (Timeout)\n\nBitte versuchen Sie es später erneut."
        
        except Exception as e:
            return f"❌ Unerwarteter Fehler bei der Registrierung: {str(e)}\n\nBitte kontaktieren Sie den Support."
    
    async def _arun(self, **kwargs) -> str:
        """Asynchrone Ausführung (nicht implementiert)"""
        raise NotImplementedError("Asynchrone Ausführung nicht unterstützt")


def create_klips2_register_tool() -> KLIPS2RegisterTool:
    """Factory-Funktion für das KLIPS2 Registrierungs-Tool"""
    return KLIPS2RegisterTool()
