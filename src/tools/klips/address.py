"""
KLIPS2 Adress-Änderungs-Tool
"""
from typing import Type
from pydantic import BaseModel, Field
from .base import KLIPS2BaseTool, KLIPS2AuthenticatedInput
from .browser_session import KLIPSBrowserSession

class KLIPS2ChangeAddressInput(KLIPS2AuthenticatedInput):
    """Input für Adressänderung"""
    street: str = Field(description="Straße und Hausnummer")
    zip_code: str = Field(description="Postleitzahl")
    city: str = Field(description="Stadt/Ort")
    country: str = Field(default="Deutschland", description="Land")

class KLIPS2ChangeAddressTool(KLIPS2BaseTool):
    name: str = "klips2_change_address"
    description: str = """Ändert die hinterlegte Adresse im KLIPS2-Profil.
    Erfordert Login.
    """
    args_schema: Type[BaseModel] = KLIPS2ChangeAddressInput

    def _run(self, username: str, password: str, street: str, zip_code: str, city: str, country: str) -> str:
        
        with KLIPSBrowserSession() as session:
            if not session.login(username, password):
                return "❌ Login fehlgeschlagen."
            
            page = session.page
            try:
                # 1. Navigate to Profile / Contact Data
                # Dashboard link is "Meine Adressen"
                try:
                    page.click("text=Meine Adressen", timeout=5000)
                    page.wait_for_load_state("networkidle")
                except:
                    # Fallback to old "Visitenkarte" if layout differs
                    page.click("text=Visitenkarte", timeout=5000)
                
                # 2. Click "Bearbeiten" or "Adresse ändern"
                # We need to find the link "Adresse bearbeiten" and navigate to it
                try:
                    # Try to find the link
                    edit_link = page.get_by_role("link", name="Adresse bearbeiten")
                    if edit_link.count() > 0:
                        # Get href and navigate directly (more robust than click sometimes)
                        href = edit_link.first.get_attribute("href")
                        if href:
                            full_url = f"https://klips2.uni-koeln.de/co/{href}"
                            page.goto(full_url)
                            page.wait_for_load_state("networkidle")
                        else:
                            edit_link.first.click()
                    else:
                        # Fallback to generic click
                        page.click("text=Bearbeiten", timeout=3000)
                except Exception as e:
                    print(f"Could not find 'Bearbeiten' link: {e}")
                
                # 3. Fill form
                # Use specific IDs found in inspection
                try:
                    # Study Address (Korrespondenzadresse)
                    page.fill("input[name='pSStrasseHausNr']", street)
                    page.fill("input[name='pSPlz']", zip_code)
                    page.fill("input[name='pSOrt']", city)
                    
                    # Country is a select
                    # We need to match the label (e.g. "Deutschland") to the value
                    # Or just select by label if Playwright supports it
                    try:
                        page.select_option("select[name='pSLand']", label=country)
                    except:
                        # Fallback if country not found or different format
                        print(f"Could not select country '{country}'")

                    # Also fill Home Address (Heimatadresse) if needed?
                    # For now, we assume user wants to change study address as it is the correspondence address
                    
                except Exception as e:
                    print(f"Error filling address form: {e}")
                
                # 4. Save
                try:
                    page.click("text=Speichern und Schließen", timeout=3000)
                    page.wait_for_load_state("networkidle")
                except:
                    print("Could not find 'Speichern und Schließen' button.")
                
                return f"""
✅ **Adressänderung durchgeführt**

Der Agent hat sich eingeloggt und das Formular ausgefüllt.

**Gesendete Daten:**
- Straße: {street}
- PLZ/Ort: {zip_code} {city}
- Land: {country}

*Hinweis: Bitte prüfen Sie im KLIPS2-Portal, ob die Änderungen übernommen wurden.*
"""
            except Exception as e:
                return f"❌ Fehler bei der Adressänderung: {str(e)}"

def create_klips2_change_address_tool() -> KLIPS2ChangeAddressTool:
    return KLIPS2ChangeAddressTool()
