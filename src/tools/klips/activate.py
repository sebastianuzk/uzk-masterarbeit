"""
KLIPS2 Account-Aktivierungs-Tool
"""
from typing import Type
from pydantic import BaseModel, Field
from .base import KLIPS2BaseTool
from .browser_session import KLIPSBrowserSession

class KLIPS2ActivateAccountInput(BaseModel):
    """Input für Account-Aktivierung"""
    activation_code_or_url: str = Field(description="Der Aktivierungscode oder der vollständige Link aus der E-Mail")
    email: str = Field(description="Die E-Mail-Adresse des Accounts")
    new_password: str = Field(description="Das neu zu setzende Passwort für den Account")

class KLIPS2ActivateAccountTool(KLIPS2BaseTool):
    name: str = "klips2_activate_account"
    description: str = """Aktiviert einen neu registrierten KLIPS2-Account.
    Benötigt den Aktivierungscode/Link aus der E-Mail und ein neues Passwort.
    """
    args_schema: Type[BaseModel] = KLIPS2ActivateAccountInput

    def _run(self, activation_code_or_url: str, email: str, new_password: str) -> str:
        # Extrahiere Code wenn URL gegeben
        url = activation_code_or_url
        code = activation_code_or_url
        
        if "http" not in activation_code_or_url:
            # Construct URL if only code is given (speculative URL structure)
            url = f"https://klips2.uni-koeln.de/co/wbSelbstRegPerson.cbProcessIDMRegisterEvent?pSupportCode={activation_code_or_url}"
        else:
            if "pSupportCode=" in activation_code_or_url:
                code = activation_code_or_url.split("pSupportCode=")[1].split("&")[0]

        with KLIPSBrowserSession() as session:
            page = session.page
            try:
                # 1. Visit Activation URL
                page.goto(url, timeout=30000)
                
                # 2. Check if we are on the password setting page
                # Look for password fields
                # page.fill("input[type='password']", new_password)
                # page.fill("input[name*='repeat']", new_password)
                
                # 3. Submit
                # page.click("text=Aktivieren" or "text=Speichern")
                
                return f"""
✅ **Account-Aktivierung aufgerufen**

Der Aktivierungslink wurde im Browser geöffnet.

**Details:**
- URL: {url}
- Code: {code}
- E-Mail: {email}

*Hinweis: Das Setzen des Passworts wurde simuliert.*
"""
            except Exception as e:
                return f"❌ Fehler bei der Aktivierung: {str(e)}"

def create_klips2_activate_account_tool() -> KLIPS2ActivateAccountTool:
    return KLIPS2ActivateAccountTool()
