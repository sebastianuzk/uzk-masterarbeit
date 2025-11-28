"""
KLIPS2 Bewerbungs-Tool
"""
import time
import os
from typing import Type, Optional
from pydantic import BaseModel, Field
from .base import KLIPS2BaseTool, KLIPS2AuthenticatedInput
from .browser_session import KLIPSBrowserSession

class KLIPS2ApplyInput(KLIPS2AuthenticatedInput):
    """Input für Studienbewerbung"""
    semester: str = Field(description="Semester für die Bewerbung (z.B. 'Wintersemester 2025/26')")
    degree_type: str = Field(description="Art des Abschlusses (z.B. 'Bachelor', 'Master', 'Promotionsstudium')")
    study_program: str = Field(description="Name des Studiengangs (z.B. 'Rechtswissenschaften')")
    entry_semester: str = Field(default="1", description="Fachsemester (Standard: '1')")
    study_form: Optional[str] = Field(default=None, description="Studienform (z.B. 'Erststudium', 'Zweitstudium'). Wenn leer, wird die erste verfügbare Option gewählt.")
    
    # Personal Data Fields
    birth_place: Optional[str] = Field(default=None, description="Geburtsort (falls nicht vorausgefüllt)")
    birth_country: Optional[str] = Field(default="Deutschland", description="Geburtsland")
    nationality: Optional[str] = Field(default="Deutschland", description="Staatsangehörigkeit")
    gender: Optional[str] = Field(default=None, description="Geschlecht (z.B. 'Männlich', 'Weiblich', 'Divers')")

    # Address Fields
    street: Optional[str] = Field(default=None, description="Straße und Hausnummer")
    zip_code: Optional[str] = Field(default=None, description="Postleitzahl")
    city: Optional[str] = Field(default=None, description="Stadt/Ort")
    country: Optional[str] = Field(default="Deutschland", description="Land der Adresse")
    phone: Optional[str] = Field(default=None, description="Telefonnummer")

    # HZB Fields
    hzb_date: Optional[str] = Field(default=None, description="Datum der HZB (TT.MM.JJJJ)")
    hzb_type: Optional[str] = Field(default=None, description="Art der HZB (z.B. 'Allgemeine Hochschulreife')")
    hzb_name: Optional[str] = Field(default="Abitur", description="Bezeichnung des Zeugnisses")
    hzb_grade: Optional[str] = Field(default=None, description="Note der HZB (z.B. '2,3')")
    hzb_school: Optional[str] = Field(default="Gymnasium", description="Name der Schule")
    hzb_country: Optional[str] = Field(default="Deutschland", description="Land der HZB")
    hzb_place: Optional[str] = Field(default=None, description="Ort/Kreis der HZB")

    # Vorbildung Fields
    prev_uni: Optional[str] = Field(default=None, description="Name der vorherigen Hochschule")
    prev_program: Optional[str] = Field(default=None, description="Vorheriger Studiengang")
    prev_degree: Optional[str] = Field(default=None, description="Angestrebter/Erreichter Abschluss")
    prev_semesters: Optional[str] = Field(default=None, description="Anzahl Semester")

class KLIPS2ApplyTool(KLIPS2BaseTool):
    name: str = "klips2_apply_study"
    description: str = """Bewerbung für einen Studiengang auf KLIPS2.
    Erfordert Login-Daten.
    Navigiert durch den Bewerbungs-Wizard und füllt die Studiendaten aus.
    
    Beispiel:
    klips2_apply_study(
        semester="Wintersemester 2024/25",
        degree_type="Bachelor",
        study_program="Betriebswirtschaftslehre",
        entry_semester="1",
        study_form="Erststudium"
    )
    """
    args_schema: Type[BaseModel] = KLIPS2ApplyInput

    def _fill_input_if_empty(self, page, label_pattern: str, value: str, description: str):
        """Helper to fill an input if it is empty."""
        if not value: 
            return
        try:
            inp = None
            
            # Strategy 1: get_by_label
            try:
                inp_locator = page.get_by_label(label_pattern, exact=False).first
                if inp_locator.count() > 0:
                    inp = inp_locator
            except:
                pass
            
            # Strategy 2: Table row (common in KLIPS)
            if not inp or inp.count() == 0:
                try:
                    inp = page.locator(f"//tr[td[contains(text(), '{label_pattern}')]]//input[@type='text']").first
                except:
                    pass
            
            # Strategy 3: Look for input with placeholder or name containing the pattern
            if not inp or inp.count() == 0:
                try:
                    inp = page.locator(f"input[type='text'][placeholder*='{label_pattern}' i]").first
                except:
                    pass
            
            if inp and inp.count() > 0:
                try:
                    if inp.is_visible():
                        current_val = inp.input_value()
                        if not current_val or current_val.strip() == "":
                            inp.fill(value)
                            inp.press("Tab")  # Trigger blur event
                            time.sleep(0.3)
                            print(f"✓ Filled '{description}': {value}")
                        else:
                            print(f"  '{description}' already filled: {current_val}")
                    else:
                        print(f"  Input for '{description}' not visible")
                except:
                    print(f"  Could not interact with '{description}'")
            else:
                print(f"  Input for '{description}' not found")
        except Exception as e:
            print(f"  Error filling '{description}': {e}")

    def _select_option_if_empty(self, page, label_pattern: str, value: str, description: str):
        """Helper to select an option if not already selected."""
        if not value: return
        try:
            # Strategy 1: get_by_label
            sel = page.get_by_label(label_pattern, exact=False).first
            
            # Strategy 2: Table row (fallback)
            if not sel.count():
                sel = page.locator(f"//tr[td[contains(text(), '{label_pattern}')]]//select").first
            
            if sel.count() > 0 and sel.is_visible():
                current_val = sel.input_value()
                # Skip if already has a value
                if current_val and current_val not in ["0", "-1", ""]:
                    print(f"'{description}' already selected (Value: {current_val})")
                    return
                    
                # Try to select by label (text) - with short timeout
                try:
                    sel.select_option(label=value, timeout=2000)
                    print(f"Selected '{value}' for '{description}'")
                except:
                    # Quick fuzzy match
                    options = sel.locator("option").all()
                    for opt in options:
                        txt = opt.text_content()
                        if value.lower() in txt.lower():
                            val = opt.get_attribute("value")
                            if val:
                                sel.select_option(value=val)
                                print(f"Fuzzy selected '{txt}' for '{description}'")
                                return
                    print(f"Option '{value}' not found for '{description}'")
            else:
                print(f"Select for '{description}' not found.")
        except Exception as e:
            print(f"Error selecting '{description}': {e}")

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
                if search_text.lower() == text.lower():
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
                try:
                    page.evaluate("""
                        (selector) => {
                            const el = document.querySelector(selector);
                            if (el) {
                                el.dispatchEvent(new Event('change', { bubbles: true }));
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
            
    def _select_first_available(self, page, selector: str, description: str) -> str:
        """Selects the first available non-empty option."""
        try:
            page.wait_for_selector(selector, timeout=5000)
            select_handle = page.query_selector(selector)
            if not select_handle:
                return None
                
            options = select_handle.query_selector_all("option")
            for opt in options:
                val = opt.get_attribute("value")
                text = opt.text_content().strip()
                if val:
                    page.select_option(selector, val)
                    # Force events
                    page.evaluate(f"document.querySelector('{selector}').dispatchEvent(new Event('change', {{ bubbles: true }}))")
                    print(f"Auto-selected '{text}' for '{description}'")
                    return text
            return None
        except:
            return None

    def _click_next(self, page) -> bool:
        """Clicks the 'Weiter' button and waits for navigation."""
        try:
            # Quick check for loading mask
            try:
                page.wait_for_selector(".pageDisabled", state="hidden", timeout=1000)
            except:
                pass

            # Try ID first (faster)
            btn = page.query_selector("#idNextButton")
            if btn:
                btn.click(force=True)
            else:
                page.click("text=Weiter", force=True)
            
            page.wait_for_load_state("domcontentloaded")
            time.sleep(0.3)
            
            # Quick check for validation error
            error_msg = page.locator("text=Alle Pflichtfelder müssen ausgefüllt sein")
            if error_msg.count() > 0 and error_msg.first.is_visible():
                print("⚠️  Validation error: Required fields missing")
                return False
            
            return True
        except Exception as e:
            print(f"Error clicking Next: {e}")
            return False

    def _fill_personal_data(self, page, birth_place, birth_country, nationality, gender):
        """Fills Personal Data if empty."""
        print("Checking Personal Data...")
        self._fill_input_if_empty(page, "Geburtsort", birth_place, "Geburtsort")
        self._select_option_if_empty(page, "Geburtsland", birth_country, "Geburtsland")
        self._select_option_if_empty(page, "Staatsangehörigkeit", nationality, "Staatsangehörigkeit")
        self._select_option_if_empty(page, "Geschlecht", gender, "Geschlecht")

    def _fill_addresses(self, page, street, zip_code, city, country, phone):
        """Fills Addresses if empty."""
        print("Checking Addresses...")
        
        # Usually "Korrespondenzadresse" is the main one to fill
        self._fill_input_if_empty(page, "Straße", street, "Straße")
        self._fill_input_if_empty(page, "Postleitzahl", zip_code, "PLZ")
        self._fill_input_if_empty(page, "Ort", city, "Ort")
        self._select_option_if_empty(page, "Land", country, "Land")
        self._fill_input_if_empty(page, "Telefon", phone, "Telefon")
        
        # Map for correspondence address (Korrespondenzadresse) fields with 'idS' prefix
        # and home address (Heimatadresse) fields with 'idH' prefix
        id_mappings = [
            ("idSOrt", "idHOrt", city, "City"),
            ("idSStrasseHausNr", "idHStrasseHausNr", street, "Street"),
            ("idSPlz", "idHPlz", zip_code, "ZIP"),
        ]
        
        for correspondence_id, home_id, value, desc in id_mappings:
            if not value:
                continue
            try:
                # Try correspondence address first
                inp = page.query_selector(f"#{correspondence_id}")
                if not inp or not inp.is_visible():
                    # Try home address
                    inp = page.query_selector(f"#{home_id}")
                
                if inp and inp.is_visible():
                    val = inp.input_value()
                    if not val or val.strip() == "":
                        inp.fill(value)
                        inp.press("Tab")
                        print(f"✓ Filled {desc} via ID: {value}")
            except Exception as e:
                print(f"  Could not fill {desc}: {e}")
        
        print("✓ All required address fields filled")

    def _fill_hzb(self, page, hzb_date, hzb_type, hzb_grade, hzb_country, hzb_place, hzb_name="Abitur", hzb_school="Gymnasium"):
        """Fills the HZB form if fields are present."""
        print("Checking HZB section...")
        try:
            # Check if we are on HZB page
            if not page.locator("text=Hochschulzugangsberechtigung").first.is_visible():
                print("  Not on HZB page.")
                return

            # Check if there is already an entry (table row with data)
            existing_rows = page.query_selector_all("table.tb tr.tbdata")
            if existing_rows and len(existing_rows) > 0:
                print(f"✓ HZB entry already exists ({len(existing_rows)} rows). No action needed.")
                return
            
            # No data provided, skip
            if not hzb_date and not hzb_type and not hzb_grade:
                print("  No HZB data provided. Skipping.")
                return
            
            print("  Filling HZB data...")
            
            # Get all visible selects and inputs on the page
            all_selects = page.query_selector_all("select:visible")
            all_inputs = page.query_selector_all("input[type='text']:visible")
            
            # Filter out readonly inputs
            all_inputs = [inp for inp in all_inputs if not inp.get_attribute("readonly")]
            
            print(f"  Found {len(all_selects)} selects and {len(all_inputs)} inputs")
            
            # 1. Art (First select on the page)
            if len(all_selects) > 0 and hzb_type:
                sel = all_selects[0]
                current_val = sel.input_value()
                if not current_val or current_val in ["", "0", "-1"]:
                    self._select_from_element(sel, hzb_type, "Art der HZB")
                    time.sleep(0.5)  # Brief wait for page to update after select change
                    
                    # Re-query inputs after select change (DOM may have updated)
                    all_inputs = page.query_selector_all("input[type='text']:visible")
                    all_inputs = [inp for inp in all_inputs if not inp.get_attribute("readonly")]
            
            # Fill all text inputs quickly
            input_data = [
                (0, hzb_name, "Zeugnisname"),
                (1, hzb_date, "Zeugnisdatum"),
                (2, hzb_grade, "Durchschnittsnote"),
                (3, hzb_school, "Name der Schule"),
                (4, hzb_place, "Ort der Schule"),
            ]
            
            for idx, value, desc in input_data:
                if idx < len(all_inputs) and value:
                    inp = all_inputs[idx]
                    if not inp.input_value():
                        inp.fill(value)
                        print(f"  ✓ Filled {desc}: {value}")
            
            # Press Tab once at the end to trigger any field validation
            if all_inputs:
                all_inputs[-1].press("Tab")
            
            # 8. Bundesland (Second select)
            if len(all_selects) > 1:
                sel = all_selects[1]
                current_val = sel.input_value()
                if not current_val or current_val in ["", "0", "-1"]:
                    self._select_from_element(sel, "Nordrhein-Westfalen", "Bundesland")
                    time.sleep(0.3)
            
            # 9. Landkreis (Third select)
            if len(all_selects) > 2 and hzb_place:
                sel = all_selects[2]
                current_val = sel.input_value()
                if not current_val or current_val in ["", "0", "-1"]:
                    self._select_from_element(sel, hzb_place, "Landkreis")
            
            print("✓ HZB data filled")

        except Exception as e:
            print(f"  Error checking HZB: {e}")
    
    def _select_from_element(self, sel, search_text: str, description: str) -> bool:
        """Select an option from a select element by fuzzy matching."""
        try:
            options = sel.query_selector_all("option")
            
            # Collect all valid options
            valid_options = []
            for opt in options:
                opt_text = opt.text_content().strip()
                opt_val = opt.get_attribute("value")
                if opt_val and opt_val not in ["", "0", "-1"]:
                    valid_options.append((opt_val, opt_text))
            
            if not valid_options:
                print(f"  ⚠️ No valid options for {description}")
                return False
            
            # Try exact match
            for opt_val, opt_text in valid_options:
                if opt_text.lower() == search_text.lower():
                    sel.select_option(opt_val)
                    sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                    print(f"  ✓ Selected {description}: {opt_text}")
                    return True
            
            # Try contains match
            for opt_val, opt_text in valid_options:
                if search_text.lower() in opt_text.lower():
                    sel.select_option(opt_val)
                    sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                    print(f"  ✓ Selected {description} (partial): {opt_text}")
                    return True
            
            # Special case: for "Allgemeine Hochschulreife", prefer "Gymnasium [aHR]" over others
            if "hochschulreife" in search_text.lower() or "abitur" in search_text.lower():
                # First try to find "Gymnasium" specifically
                for opt_val, opt_text in valid_options:
                    if "gymnasium" in opt_text.lower() and "[ahr]" in opt_text.lower():
                        sel.select_option(opt_val)
                        sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                        print(f"  ✓ Selected {description}: {opt_text}")
                        return True
                # Fallback to any [aHR] option
                for opt_val, opt_text in valid_options:
                    if "[ahr]" in opt_text.lower():
                        sel.select_option(opt_val)
                        sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                        print(f"  ✓ Selected {description} (aHR): {opt_text}")
                        return True
            
            # Try word match
            search_words = search_text.lower().split()
            for opt_val, opt_text in valid_options:
                opt_lower = opt_text.lower()
                # Check if any significant word matches
                for word in search_words:
                    if len(word) > 4 and word in opt_lower:
                        sel.select_option(opt_val)
                        sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                        print(f"  ✓ Selected {description} (word): {opt_text}")
                        return True
            
            # Fallback: select first valid option
            opt_val, opt_text = valid_options[0]
            sel.select_option(opt_val)
            sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
            print(f"  ⚠️ No match for '{search_text}' in {description}, auto-selected: {opt_text}")
            return True
            
        except Exception as e:
            print(f"  Error selecting {description}: {e}")
            return False

    def _fill_vorbildung(self, page, prev_uni, prev_program, prev_degree, prev_semesters):
        """Fills the Academic Background form."""
        print("Checking Academic Background...")
        try:
            # We're already on the Vorbildung page if this method is called from the tab handler
            # So we don't need to re-check the page - just process the form
            
            # Check for existing entries
            existing_rows = page.query_selector_all("table.tb tr.tbdata")
            if existing_rows and len(existing_rows) > 0:
                print(f"✓ Academic background entry already exists ({len(existing_rows)} rows).")
                return
            
            # For "Erststudium" (first-time students), usually no previous academic background is needed
            # Check if there's a message indicating no entry is required
            page_text = page.locator("body").text_content()
            if "keine" in page_text.lower() and ("studium" in page_text.lower() or "vorbildung" in page_text.lower()):
                print("  ✓ No academic background entry required for this application type.")
                return
            
            # Check if there are any form fields to fill
            all_selects = page.query_selector_all("select:visible")
            all_inputs = page.query_selector_all("input[type='text']:visible")
            all_inputs = [inp for inp in all_inputs if not inp.get_attribute("readonly")]
            
            print(f"  Found {len(all_selects)} selects and {len(all_inputs)} inputs on Vorbildung page")
            
            # If no form fields, the page might just be informational
            if len(all_selects) == 0 and len(all_inputs) == 0:
                print("  ✓ No form fields to fill on this page.")
                return
            
            # If we have previous study data, try to fill it
            if prev_uni or prev_program:
                print("  Filling previous academic background...")
                
                # Try to fill University name if there's an input
                if len(all_inputs) > 0 and prev_uni:
                    inp = all_inputs[0]
                    if not inp.input_value():
                        inp.fill(prev_uni)
                        inp.press("Tab")
                        print(f"  ✓ Filled Hochschule: {prev_uni}")
                        time.sleep(0.3)
                
                # Try to fill Program if there's a second input
                if len(all_inputs) > 1 and prev_program:
                    inp = all_inputs[1]
                    if not inp.input_value():
                        inp.fill(prev_program)
                        inp.press("Tab")
                        print(f"  ✓ Filled Studiengang: {prev_program}")
                        time.sleep(0.3)
                
                # Try to select Degree type if there's a select
                if len(all_selects) > 0 and prev_degree:
                    sel = all_selects[0]
                    current_val = sel.input_value()
                    if not current_val or current_val in ["", "0", "-1"]:
                        self._select_from_element(sel, prev_degree, "Abschluss")
                        time.sleep(0.3)
                
                # Try to fill Semesters if there's an input for it
                if len(all_inputs) > 2 and prev_semesters:
                    inp = all_inputs[2]
                    if not inp.input_value():
                        inp.fill(prev_semesters)
                        inp.press("Tab")
                        print(f"  ✓ Filled Semester: {prev_semesters}")
                        time.sleep(0.3)
                
                print("✓ Academic background data filled (or attempted)")
            else:
                print("  No previous academic background data provided.")
                # Try to auto-select "keine Vorbildung" or similar if available
                for sel in all_selects:
                    options = sel.query_selector_all("option")
                    for opt in options:
                        opt_text = opt.text_content().strip().lower()
                        if "keine" in opt_text or "nein" in opt_text:
                            opt_val = opt.get_attribute("value")
                            if opt_val and opt_val not in ["", "0", "-1"]:
                                sel.select_option(opt_val)
                                sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                                print(f"  ✓ Selected 'keine Vorbildung' option")
                                break

        except Exception as e:
            print(f"  Error checking Vorbildung: {e}")

    def _run(self, study_program: str, semester: str, degree_type: str, 
             username: Optional[str] = None, password: Optional[str] = None,
             entry_semester: str = "1", study_form: Optional[str] = None,
             birth_place: Optional[str] = None, birth_country: Optional[str] = "Deutschland", 
             nationality: Optional[str] = "Deutschland", gender: Optional[str] = None,
             street: Optional[str] = None, zip_code: Optional[str] = None, 
             city: Optional[str] = None, country: Optional[str] = "Deutschland", phone: Optional[str] = None,
             hzb_date: Optional[str] = None, hzb_type: Optional[str] = None, 
             hzb_grade: Optional[str] = None, hzb_country: Optional[str] = "Deutschland", hzb_place: Optional[str] = None,
             hzb_name: Optional[str] = "Abitur", hzb_school: Optional[str] = "Gymnasium",
             prev_uni: Optional[str] = None, prev_program: Optional[str] = None, 
             prev_degree: Optional[str] = None, prev_semesters: Optional[str] = None) -> str:
        
        # Fallback to environment variables if credentials are not provided
        if not username:
            username = os.getenv("KLIPS_USERNAME")
        if not password:
            password = os.getenv("KLIPS_PASSWORD")
            
        if not username or not password:
            return "❌ Login-Daten fehlen. Bitte geben Sie Benutzername und Passwort an oder konfigurieren Sie diese in der .env Datei."

        with KLIPSBrowserSession() as session:
            t0 = time.time()
            if not session.login(username, password):
                return "❌ Login fehlgeschlagen. Bitte überprüfen Sie Benutzername und Passwort."
            print(f"⏱️  Total login: {time.time() - t0:.2f}s")
            
            page = session.page
            
            try:
                # 1. Navigate to "Bewerbungen" via menu
                t0 = time.time()
                print("Navigating to Bewerbungen...")
                page.wait_for_load_state("domcontentloaded")
                
                # Click on "Bewerbungen" menu item
                try:
                    page.wait_for_selector("text=Bewerbungen", timeout=10000)
                    page.click("text=Bewerbungen")
                except Exception as e:
                    return "❌ Menü 'Bewerbungen' nicht gefunden."
                    
                page.wait_for_load_state("domcontentloaded")
                print(f"⏱️  Navigate to Bewerbungen: {time.time() - t0:.2f}s")
                
                # 2. Start new application
                t0 = time.time()
                print("Starting new application...")
                
                # Wait for and click the button
                try:
                    page.wait_for_selector("text=Bewerbung erfassen", timeout=10000)
                    page.click("text=Bewerbung erfassen")
                except:
                    return "❌ Button 'Bewerbung erfassen' nicht gefunden."
                
                page.wait_for_load_state("domcontentloaded")
                time.sleep(0.5)
                print(f"⏱️  Click 'Bewerbung erfassen': {time.time() - t0:.2f}s")
                
                # 3. Step 1: Select Semester
                t0 = time.time()
                if not self._select_fuzzy(page, "select[name='pStSemNr']", semester, "Semester"):
                    return f"❌ Semester '{semester}' nicht gefunden."
                
                if not self._click_next(page):
                    return "❌ Fehler beim Klicken auf 'Weiter' (Schritt 1)."
                print(f"⏱️  Step 1 (Semester): {time.time() - t0:.2f}s")
                
                # 4. Step 2: Select Degree Type
                t0 = time.time()
                try:
                    page.wait_for_selector("#idStStudArtNr", timeout=10000)
                except:
                    return "❌ Auswahlfeld für Abschlussart nicht geladen."

                if not self._select_fuzzy(page, "#idStStudArtNr", degree_type, "Abschlussart"):
                    return f"❌ Abschlussart '{degree_type}' nicht gefunden."
                
                time.sleep(0.3)
                
                if not self._click_next(page):
                    return "❌ Fehler beim Klicken auf 'Weiter' (Schritt 2)."
                print(f"⏱️  Step 2 (Degree): {time.time() - t0:.2f}s")
                
                # 5. Step 3: Select Program
                t0 = time.time()
                try:
                    page.wait_for_selector("#idBwStsCfgNr", timeout=5000)
                except:
                    return "❌ Auswahlfeld für Studiengang nicht geladen."

                if not self._select_fuzzy(page, "#idBwStsCfgNr", study_program, "Studiengang"):
                    return f"❌ Studiengang '{study_program}' nicht gefunden."
                
                time.sleep(0.5)
                
                # 6. Select Entry Semester (Fachsemester)
                if page.query_selector("#idBwStFsCfgNr"):
                    if not self._select_fuzzy(page, "#idBwStFsCfgNr", entry_semester, "Fachsemester"):
                        self._select_first_available(page, "#idBwStFsCfgNr", "Fachsemester (Fallback)")
                
                # 7. Select Study Form (Studienform)
                if page.query_selector("#idStudFormAuswahl"):
                    if study_form:
                        if not self._select_fuzzy(page, "#idStudFormAuswahl", study_form, "Studienform"):
                             self._select_first_available(page, "#idStudFormAuswahl", "Studienform (Fallback)")
                    else:
                        self._select_first_available(page, "#idStudFormAuswahl", "Studienform (Auto)")
                
                time.sleep(0.3)
                
                # Check for any other required fields on this page
                print("Checking for additional required fields on Studiengangsauswahl...")
                all_selects = page.query_selector_all("select:visible")
                for sel in all_selects:
                    sel_id = sel.get_attribute("id") or sel.get_attribute("name")
                    val = sel.input_value()
                    if not val or val in ["0", "-1", ""]:
                        print(f"⚠️  Warning: Empty select field found: {sel_id}")
                        try:
                            options = sel.query_selector_all("option")
                            for opt in options:
                                opt_val = opt.get_attribute("value")
                                if opt_val and opt_val not in ["0", "-1", ""]:
                                    sel.select_option(opt_val)
                                    print(f"   Auto-filled {sel_id} with: {opt.text_content().strip()}")
                                    time.sleep(0.2)
                                    break
                        except Exception as e:
                            print(f"   Could not auto-fill {sel_id}: {e}")

                # Click Next to finish Study Selection and go to Personal Data
                if not self._click_next(page):
                    try:
                        page.screenshot(path="debug_studiengangsauswahl.png")
                        print("📸 Screenshot saved to debug_studiengangsauswahl.png")
                    except:
                        pass
                    return "❌ Fehler beim Klicken auf 'Weiter' (nach Studiengangswahl). Pflichtfelder fehlen möglicherweise."
                print(f"⏱️  Step 3 (Program selection): {time.time() - t0:.2f}s")
                
                # 8. Navigate through tabs
                t0 = time.time()
                tabs_visited = []
                max_steps = 10
                last_tab_name = None
                stuck_count = 0
                
                for _ in range(max_steps):
                    try:
                        # Check active tab
                        active_tab = page.query_selector("li.selected a")
                        if not active_tab:
                            break
                            
                        tab_name = active_tab.text_content().strip()
                        
                        # Check if we're stuck on the same tab
                        if tab_name == last_tab_name:
                            stuck_count += 1
                            if stuck_count > 2:
                                print(f"⚠️  Stuck on tab '{tab_name}' - trying to force next...")
                                error_visible = page.locator("text=Alle Pflichtfelder müssen ausgefüllt sein").first.is_visible() if page.locator("text=Alle Pflichtfelder müssen ausgefüllt sein").count() > 0 else False
                                
                                if not error_visible:
                                    print("  No validation error visible, attempting to proceed...")
                                    if not self._click_next(page):
                                        print("  Could not proceed. Breaking loop.")
                                        break
                                    stuck_count = 0
                                else:
                                    print("  Validation error present. Breaking loop.")
                                    break
                        else:
                            stuck_count = 0
                            tabs_visited.append(tab_name)
                            print(f"📋 Tab: {tab_name}")
                        
                        last_tab_name = tab_name
                        
                        # Handle specific tabs
                        if "Personendaten" in tab_name:
                            self._fill_personal_data(page, birth_place, birth_country, nationality, gender)
                        
                        elif "Anschriften" in tab_name or "Kontakt" in tab_name or "adresse" in tab_name.lower():
                            self._fill_addresses(page, street, zip_code, city, country, phone)

                        elif "Hochschulzugangsberechtigung" in tab_name:
                            self._fill_hzb(page, hzb_date, hzb_type, hzb_grade, hzb_country, hzb_place, hzb_name, hzb_school)
                        
                        elif "Vorbildung" in tab_name or "Studienverlauf" in tab_name:
                            self._fill_vorbildung(page, prev_uni, prev_program, prev_degree, prev_semesters)
                            print(f"⏱️  Total time: {time.time() - t0:.2f}s")
                            print("Reached 'Akademische Vorbildung'. Stopping navigation as requested.")
                            return f"✅ Bewerbung bis 'Akademische Vorbildung' ausgefüllt.\nTabs: {', '.join(tabs_visited)}"

                        # Click Next to proceed to next tab
                        if not self._click_next(page):
                            print("Could not click Next. Stopping.")
                            break
                            
                    except Exception as e:
                        print(f"Error in navigation loop: {e}")
                        break

                print(f"⏱️  Total time: {time.time() - t0:.2f}s")
                # Success (Draft created)
                return f"✅ Bewerbung für '{study_program}' ({degree_type}, {semester}) erfolgreich angelegt.\nStatus: Wizard durchlaufen bis '{tabs_visited[-1] if tabs_visited else 'Studiengangswahl'}'.\nBitte prüfen Sie den Entwurf in KLIPS2 und ergänzen Sie fehlende Nachweise."
                
            except Exception as e:
                return f"❌ Ein unerwarteter Fehler ist aufgetreten: {str(e)}"

def create_klips2_apply_tool() -> KLIPS2ApplyTool:
    return KLIPS2ApplyTool()
