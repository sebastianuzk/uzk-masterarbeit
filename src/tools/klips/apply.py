"""
KLIPS2 Bewerbungs-Tool
"""
import time
from typing import Type, Optional
from pydantic import BaseModel, Field
from .base import KLIPS2BaseTool, KLIPS2AuthenticatedInput
from .browser_session import KLIPSBrowserSession

class KLIPS2ApplyInput(KLIPS2AuthenticatedInput):
    """Input für Studienbewerbung"""
    semester: str = Field(description="Semester für die Bewerbung (z.B. 'Wintersemester 2025/26')")
    degree_type: str = Field(description="Art des Abschlusses (z.B. 'Bachelor', 'Master', 'Promotionsstudium')")
    study_program: str = Field(description="Name des Studiengangs (z.B. 'Rechtswissenschaften')")

class KLIPS2ApplyTool(KLIPS2BaseTool):
    name: str = "klips2_apply_study"
    description: str = """Bewerbung für einen Studiengang auf KLIPS2.
    Erfordert Login-Daten.
    Navigiert durch den Bewerbungs-Wizard.
    """
    args_schema: Type[BaseModel] = KLIPS2ApplyInput

    def _select_fuzzy(self, page, selector: str, search_text: str, description: str) -> bool:
        """Selects an option in a dropdown that fuzzily matches the search text."""
        try:
            page.wait_for_selector(selector, timeout=10000)
            select_handle = page.query_selector(selector)
            if not select_handle:
                print(f"Select '{description}' ({selector}) not found.")
                return False
            
            options = select_handle.query_selector_all("option")
            val_to_select = None
            text_found = ""
            
            # 1. Exact match (case-insensitive)
            for opt in options:
                text = opt.text_content().strip()
                val = opt.get_attribute("value")
                if not val: continue
                if text.lower() == search_text.lower():
                    val_to_select = val
                    text_found = text
                    break
            
            # 2. Contains match
            if not val_to_select:
                for opt in options:
                    text = opt.text_content().strip()
                    val = opt.get_attribute("value")
                    if not val: continue
                    if search_text.lower() in text.lower():
                        val_to_select = val
                        text_found = text
                        break
            
            if val_to_select:
                page.select_option(selector, val_to_select)
                
                # Force change event with evaluate to ensure state update
                # Using evaluate with argument to avoid quote escaping issues
                try:
                    page.evaluate("""
                        (selector) => {
                            const el = document.querySelector(selector);
                            if (el) {
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                // Some frameworks listen to input or blur
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('blur', { bubbles: true }));
                            }
                        }
                    """, selector)
                except Exception as e:
                    print(f"Warning: Could not dispatch events via evaluate: {e}")
                
                time.sleep(1) # Wait for any JS to process
                print(f"Selected '{text_found}' for '{description}'")
                return True
            else:
                print(f"No option found for '{description}' matching '{search_text}'. Available options: {[o.text_content().strip() for o in options if o.get_attribute('value')]}")
                return False
                
        except Exception as e:
            print(f"Error selecting '{description}': {e}")
            return False

    def _click_next(self, page) -> bool:
        """Clicks the 'Weiter' button and waits for navigation."""
        try:
            # Wait for any loading mask to disappear
            # The error indicated <div class="pageDisabled"></div> intercepts clicks
            try:
                page.wait_for_selector(".pageDisabled", state="hidden", timeout=10000)
            except:
                print("Warning: .pageDisabled overlay still present or timeout waiting for it.")

            # Try ID first
            btn = page.query_selector("#idNextButton")
            if btn:
                # Use force=True to bypass overlays if they are still there
                btn.click(force=True)
            else:
                # Try text
                page.click("text=Weiter", force=True)
            
            page.wait_for_load_state("networkidle")
            time.sleep(5) # Wait for dynamic content
            return True
        except Exception as e:
            print(f"Error clicking Next: {e}")
            return False

    def _run(self, username: str, password: str, study_program: str, semester: str, degree_type: str) -> str:
        
        with KLIPSBrowserSession() as session:
            if not session.login(username, password):
                return "❌ Login fehlgeschlagen. Bitte überprüfen Sie Benutzername und Passwort."
            
            page = session.page
            
            try:
                # 1. Navigate to "Bewerbungen"
                print("Navigating to Bewerbungen...")
                page.goto("https://klips2.uni-koeln.de/co/ee/ui/ca2/app/desktop/#/home")
                page.wait_for_load_state("networkidle")
                
                link = page.get_by_role("link", name="Bewerbungen")
                if link.count() > 0:
                    link.first.click()
                else:
                    # Fallback direct URL
                    page.goto("https://klips2.uni-koeln.de/co/ee/ui/ca2/app/desktop/#/pl/ui/$ctx/wbBewerbung.wbBewerbung")
                
                page.wait_for_load_state("networkidle")
                time.sleep(3) # Wait for tiles to load
                
                # 2. Start new application
                print("Starting new application...")
                new_app_btn = page.get_by_text("Bewerbung erfassen")
                if new_app_btn.count() > 0:
                    new_app_btn.first.click()
                else:
                    return "❌ Button 'Bewerbung erfassen' nicht gefunden."
                
                page.wait_for_load_state("networkidle")
                time.sleep(5) # Wait for wizard (increased from 3s)
                
                # 3. Step 1: Select Semester
                if not self._select_fuzzy(page, "select[name='pStSemNr']", semester, "Semester"):
                    return f"❌ Semester '{semester}' nicht gefunden."
                
                if not self._click_next(page):
                    return "❌ Fehler beim Klicken auf 'Weiter' (Schritt 1)."
                
                # 4. Step 2: Select Degree Type
                # Wait for the select to appear
                try:
                    page.wait_for_selector("#idStStudArtNr", timeout=20000)
                except:
                    # Debug: Check if we are still on step 1
                    if page.query_selector("select[name='pStSemNr']"):
                        return "❌ Weiterleitung fehlgeschlagen. Immer noch auf Semester-Auswahlseite."
                    return "❌ Auswahlfeld für Abschlussart nicht geladen (Timeout)."

                if not self._select_fuzzy(page, "#idStStudArtNr", degree_type, "Abschlussart"):
                    return f"❌ Abschlussart '{degree_type}' nicht gefunden."
                
                if not self._click_next(page):
                    return "❌ Fehler beim Klicken auf 'Weiter' (Schritt 2)."
                
                # 5. Step 3: Select Program
                try:
                    page.wait_for_selector("#idBwStsCfgNr", timeout=20000)
                except:
                    return "❌ Auswahlfeld für Studiengang nicht geladen (Timeout)."

                if not self._select_fuzzy(page, "#idBwStsCfgNr", study_program, "Studiengang"):
                    return f"❌ Studiengang '{study_program}' nicht gefunden."
                
                if not self._click_next(page):
                    return "❌ Fehler beim Klicken auf 'Weiter' (Schritt 3)."
                
                # Success (Draft created)
                return f"✅ Bewerbung für '{study_program}' ({degree_type}, {semester}) erfolgreich gestartet/angelegt. Bitte prüfen Sie den Entwurf in KLIPS2."
                
            except Exception as e:
                return f"❌ Ein unerwarteter Fehler ist aufgetreten: {str(e)}"

def create_klips2_apply_tool() -> KLIPS2ApplyTool:
    return KLIPS2ApplyTool()
