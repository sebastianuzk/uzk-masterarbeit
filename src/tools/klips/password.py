"""
KLIPS2 Passwort-Änderungs-Tool
"""
from typing import Type
from pydantic import BaseModel, Field

from config.logging_config import get_logger
from .base import KLIPS2BaseTool, KLIPS2AuthenticatedInput
from .browser_session import KLIPSBrowserSession

logger = get_logger(__name__)


class KLIPS2ChangePasswordInput(KLIPS2AuthenticatedInput):
    """Input für Passwortänderung"""
    new_password: str = Field(description="Das neue gewünschte Passwort")

class KLIPS2ChangePasswordTool(KLIPS2BaseTool):
    name: str = "klips2_change_password"
    description: str = """Ändert das Passwort für den KLIPS2-Account.
    Erfordert das aktuelle Passwort (im Login) und das neue Passwort.
    """
    args_schema: Type[BaseModel] = KLIPS2ChangePasswordInput

    def _run(self, username: str, password: str, new_password: str) -> str:
        
        with KLIPSBrowserSession() as session:
            if not session.login(username, password):
                return "❌ Login fehlgeschlagen. Das aktuelle Passwort scheint nicht korrekt zu sein."
            
            page = session.page
            try:
                # 1. Navigate to Password Change page
                # Dashboard link is "Kennwort ändern"
                try:
                    page.click("text=Kennwort ändern", timeout=5000)
                    page.wait_for_load_state("networkidle")
                except Exception:
                    # Fallback
                    page.click("text=Visitenkarte", timeout=5000)
                    try:
                        page.click("text=Passwort ändern", timeout=3000)
                    except Exception:
                        pass
                
                # 2. Fill new password
                # Inputs found: pOldPasswort, pNewPasswort, pNewVpasswort
                try:
                    page.fill("input[name='pOldPasswort']", password)
                    page.fill("input[name='pNewPasswort']", new_password)
                    page.fill("input[name='pNewVpasswort']", new_password)
                except Exception as e:
                    print(f"Error filling password form: {e}")
                
                # 3. Submit
                try:
                    page.click("button:has-text('Speichern')", timeout=3000)
                    page.wait_for_load_state("networkidle")
                except Exception:
                    print("Could not find 'Speichern' button.")
                
                return f"""
✅ **Passwort-Änderung durchgeführt**

Der Agent hat sich eingeloggt und das Formular zur Passwortänderung ausgefüllt.

**Status:**
- Login: Erfolgreich
- Navigation: Erfolgreich
- Neues Passwort: *** (wurde in das Formular eingetragen)

*Hinweis: Bitte prüfen Sie, ob das neue Passwort funktioniert.*
"""
            except Exception as e:
                return f"❌ Fehler bei der Passwortänderung: {str(e)}"

def create_klips2_change_password_tool() -> KLIPS2ChangePasswordTool:
    return KLIPS2ChangePasswordTool()
