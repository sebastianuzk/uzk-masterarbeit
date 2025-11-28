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
            print(f"Skipping '{description}' - no value provided")
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
            
            # Strategy 2: Table row
            if not sel.count():
                sel = page.locator(f"//tr[td[contains(text(), '{label_pattern}')]]//select").first
                
            if sel.count() > 0 and sel.is_visible():
                current_val = sel.input_value()
                # Assuming empty/default value is "" or "0" or "-1"
                if not current_val or current_val in ["0", "-1", ""]:
                    # Try to select by label (text)
                    try:
                        sel.select_option(label=value)
                        print(f"Selected '{value}' for '{description}'")
                    except:
                        # Fuzzy match manually
                        options = sel.locator("option").all()
                        found = False
                        for opt in options:
                            txt = opt.text_content()
                            if value.lower() in txt.lower():
                                val = opt.get_attribute("value")
                                if val:
                                    sel.select_option(value=val)
                                    print(f"Fuzzy selected '{txt}' for '{description}'")
                                    found = True
                                    break
                        if not found:
                            print(f"Option '{value}' not found for '{description}'")
                else:
                    print(f"'{description}' already selected (Value: {current_val})")
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
            # Wait for any loading mask to disappear
            try:
                page.wait_for_selector(".pageDisabled", state="hidden", timeout=3000)
            except:
                pass

            # Check for validation errors before clicking
            error_msg = page.locator("text=Alle Pflichtfelder müssen ausgefüllt sein")
            if error_msg.count() > 0 and error_msg.first.is_visible():
                print("⚠️  Validation error: Required fields missing")
                # List all visible select and input elements to debug
                selects = page.query_selector_all("select:visible")
                inputs = page.query_selector_all("input:visible[type='text']")
                print(f"   Found {len(selects)} visible selects and {len(inputs)} visible text inputs")
                
                print("\n   All select fields:")
                for sel in selects:
                    val = sel.input_value()
                    name = sel.get_attribute("name") or sel.get_attribute("id") or "unknown"
                    # Get label if possible
                    try:
                        parent = sel.evaluate("el => el.closest('tr')")
                        if parent:
                            label = page.evaluate("tr => tr.querySelector('td:first-child')?.textContent", parent)
                            print(f"   Select [{name}] (Label: {label}): '{val}'")
                        else:
                            print(f"   Select [{name}]: '{val}'")
                    except:
                        print(f"   Select [{name}]: '{val}'")
                
                print("\n   All text input fields:")
                for inp in inputs:
                    val = inp.input_value()
                    name = inp.get_attribute("name") or inp.get_attribute("id") or "unknown"
                    print(f"   Input [{name}]: '{val}'")
                
                return False

            # Try ID first
            btn = page.query_selector("#idNextButton")
            if btn:
                btn.click(force=True)
            else:
                page.click("text=Weiter", force=True)
            
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1.5)
            
            # Check if validation error appeared after click
            time.sleep(0.5)
            error_msg = page.locator("text=Alle Pflichtfelder müssen ausgefüllt sein")
            if error_msg.count() > 0 and error_msg.first.is_visible():
                print("⚠️  Validation error appeared after clicking Next")
                
                # Debug: Save page HTML
                try:
                    html_content = page.content()
                    with open("debug_page.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    print("📄 Page HTML saved to debug_page.html")
                except:
                    pass
                
                # List all form fields
                selects = page.query_selector_all("select:visible")
                inputs = page.query_selector_all("input:visible[type='text']")
                print(f"\n   Current page has {len(selects)} selects and {len(inputs)} text inputs")
                
                for sel in selects:
                    val = sel.input_value()
                    sel_id = sel.get_attribute("id") or sel.get_attribute("name") or "unknown"
                    print(f"   Select [{sel_id}]: '{val}'")
                
                for inp in inputs:
                    val = inp.input_value()
                    inp_id = inp.get_attribute("id") or inp.get_attribute("name") or "unknown"
                    print(f"   Input [{inp_id}]: '{val}'")
                
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
        
        # Try to fill by ID if label-based filling didn't work
        time.sleep(0.5)
        
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
                        time.sleep(0.3)
                        print(f"✓ Filled {desc} via ID: {value}")
            except Exception as e:
                print(f"  Could not fill {desc}: {e}")
        
        # Check if all required fields are filled
        empty_fields = []
        for inp in page.query_selector_all("input:visible[type='text']"):
            val = inp.input_value()
            if not val or val.strip() == "":
                inp_id = inp.get_attribute("id") or inp.get_attribute("name") or "unknown"
                # Skip fields that are typically optional (CoName = Country Name fields)
                if inp_id not in ["idSCoName", "idHCoName"]:
                    empty_fields.append(inp_id)
        
        if empty_fields:
            print(f"⚠️  Still empty required fields: {empty_fields}")
        else:
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
            time.sleep(1)
            
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
                    time.sleep(1)  # Wait longer for page to update after select change
                    
                    # Re-query inputs after select change (DOM may have updated)
                    all_inputs = page.query_selector_all("input[type='text']:visible")
                    all_inputs = [inp for inp in all_inputs if not inp.get_attribute("readonly")]
            
            # 2. Zeugnisname (First input)
            if len(all_inputs) > 0 and hzb_name:
                inp = all_inputs[0]
                if not inp.input_value():
                    inp.fill(hzb_name)
                    inp.press("Tab")
                    print(f"  ✓ Filled Zeugnisname: {hzb_name}")
                    time.sleep(0.3)
            
            # 3. Zeugnisdatum (Second input)
            if len(all_inputs) > 1 and hzb_date:
                inp = all_inputs[1]
                if not inp.input_value():
                    inp.fill(hzb_date)
                    inp.press("Tab")
                    print(f"  ✓ Filled Zeugnisdatum: {hzb_date}")
                    time.sleep(0.3)
            
            # 4. Durchschnittsnote (Third input)
            if len(all_inputs) > 2 and hzb_grade:
                inp = all_inputs[2]
                if not inp.input_value():
                    inp.fill(hzb_grade)
                    inp.press("Tab")
                    print(f"  ✓ Filled Durchschnittsnote: {hzb_grade}")
                    time.sleep(0.3)
            
            # 5. Name der Schule (Fourth input)
            if len(all_inputs) > 3 and hzb_school:
                inp = all_inputs[3]
                if not inp.input_value():
                    inp.fill(hzb_school)
                    inp.press("Tab")
                    print(f"  ✓ Filled Name der Schule: {hzb_school}")
                    time.sleep(0.3)
            
            # 6. Ort der Schule (Fifth input)
            if len(all_inputs) > 4 and hzb_place:
                inp = all_inputs[4]
                if not inp.input_value():
                    inp.fill(hzb_place)
                    inp.press("Tab")
                    print(f"  ✓ Filled Ort der Schule: {hzb_place}")
                    time.sleep(0.3)
            
            # 7. Land der Schule - This appears to be a text label "Deutschland" in the screenshot, not a select
            # Skip this one as it's pre-filled
            
            # 8. Bundesland (Second select)
            if len(all_selects) > 1:
                sel = all_selects[1]
                current_val = sel.input_value()
                if not current_val or current_val in ["", "0", "-1"]:
                    self._select_from_element(sel, "Nordrhein-Westfalen", "Bundesland")
                    time.sleep(0.5)
            
            # 9. Landkreis (Third select)
            if len(all_selects) > 2 and hzb_place:
                sel = all_selects[2]
                current_val = sel.input_value()
                if not current_val or current_val in ["", "0", "-1"]:
                    self._select_from_element(sel, hzb_place, "Landkreis")
                    time.sleep(0.3)
            
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
            if not session.login(username, password):
                return "❌ Login fehlgeschlagen. Bitte überprüfen Sie Benutzername und Passwort."
            
            page = session.page
            
            try:
                # 1. Navigate to "Bewerbungen"
                print("Navigating to Bewerbungen...")
                # Wait for the page to be ready after login
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # Click on "Bewerbungen" menu item
                page.click("text=Bewerbungen")
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # 2. Start new application
                print("Starting new application...")
                
                # Try to find the button with multiple strategies
                found_btn = False
                
                # Strategy 1: Exact text match
                btn = page.get_by_text("Bewerbung erfassen")
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.click()
                    found_btn = True
                
                # Strategy 2: Button role
                if not found_btn:
                    btn = page.get_by_role("button", name="Bewerbung erfassen")
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        found_btn = True

                # Strategy 3: Partial text in any element (e.g. span inside button)
                if not found_btn:
                    btn = page.locator("text=Bewerbung erfassen")
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        found_btn = True
                        
                if not found_btn:
                    # Debug info
                    print("DEBUG: Page content text (first 500 chars):")
                    print(page.locator("body").text_content()[:500])
                    return "❌ Button 'Bewerbung erfassen' nicht gefunden. Bitte prüfen Sie, ob Sie bereits eingeloggt sind und Zugriff auf Bewerbungen haben."
                
                page.wait_for_load_state("networkidle")
                time.sleep(5)
                
                # 3. Step 1: Select Semester
                if not self._select_fuzzy(page, "select[name='pStSemNr']", semester, "Semester"):
                    return f"❌ Semester '{semester}' nicht gefunden."
                
                if not self._click_next(page):
                    return "❌ Fehler beim Klicken auf 'Weiter' (Schritt 1)."
                
                # 4. Step 2: Select Degree Type
                try:
                    page.wait_for_selector("#idStStudArtNr", timeout=10000)
                except:
                    return "❌ Auswahlfeld für Abschlussart nicht geladen."

                if not self._select_fuzzy(page, "#idStStudArtNr", degree_type, "Abschlussart"):
                    return f"❌ Abschlussart '{degree_type}' nicht gefunden."
                
                # Wait a bit for any dynamic fields
                time.sleep(1)
                
                if not self._click_next(page):
                    return "❌ Fehler beim Klicken auf 'Weiter' (Schritt 2)."
                
                # 5. Step 3: Select Program
                try:
                    page.wait_for_selector("#idBwStsCfgNr", timeout=10000)
                except:
                    return "❌ Auswahlfeld für Studiengang nicht geladen."

                if not self._select_fuzzy(page, "#idBwStsCfgNr", study_program, "Studiengang"):
                    return f"❌ Studiengang '{study_program}' nicht gefunden."
                
                # Wait for dynamic fields (Entry Semester & Study Form) to appear on the SAME page
                time.sleep(2)
                
                # 6. Select Entry Semester (Fachsemester)
                # Selector idBwStFsCfgNr
                if page.query_selector("#idBwStFsCfgNr"):
                    if not self._select_fuzzy(page, "#idBwStFsCfgNr", entry_semester, "Fachsemester"):
                        # Fallback to first available if specific one fails
                        self._select_first_available(page, "#idBwStFsCfgNr", "Fachsemester (Fallback)")
                
                # 7. Select Study Form (Studienform)
                # Selector idStudFormAuswahl
                if page.query_selector("#idStudFormAuswahl"):
                    if study_form:
                        if not self._select_fuzzy(page, "#idStudFormAuswahl", study_form, "Studienform"):
                             self._select_first_available(page, "#idStudFormAuswahl", "Studienform (Fallback)")
                    else:
                        # Auto-select first available (e.g. Erststudium or Zweitstudium)
                        self._select_first_available(page, "#idStudFormAuswahl", "Studienform (Auto)")
                
                # Wait a bit for any dynamic fields to appear
                time.sleep(2)
                
                # Check for any other required fields on this page
                print("Checking for additional required fields on Studiengangsauswahl...")
                all_selects = page.query_selector_all("select:visible")
                for sel in all_selects:
                    sel_id = sel.get_attribute("id") or sel.get_attribute("name")
                    val = sel.input_value()
                    if not val or val in ["0", "-1", ""]:
                        print(f"⚠️  Warning: Empty select field found: {sel_id}")
                        # Try to select first available option
                        try:
                            options = sel.query_selector_all("option")
                            for opt in options:
                                opt_val = opt.get_attribute("value")
                                if opt_val and opt_val not in ["0", "-1", ""]:
                                    sel.select_option(opt_val)
                                    print(f"   Auto-filled {sel_id} with: {opt.text_content().strip()}")
                                    time.sleep(0.5)
                                    break
                        except Exception as e:
                            print(f"   Could not auto-fill {sel_id}: {e}")

                # Click Next to finish Study Selection and go to Personal Data
                if not self._click_next(page):
                    # Take screenshot for debugging
                    try:
                        page.screenshot(path="debug_studiengangsauswahl.png")
                        print("📸 Screenshot saved to debug_studiengangsauswahl.png")
                    except:
                        pass
                    return "❌ Fehler beim Klicken auf 'Weiter' (nach Studiengangswahl). Pflichtfelder fehlen möglicherweise."
                
                # 8. Navigate through tabs
                tabs_visited = []
                max_steps = 10
                last_tab_name = None
                stuck_count = 0
                
                for _ in range(max_steps):
                    try:
                        # Check active tab
                        active_tab = page.query_selector("li.selected a")
                        if not active_tab:
                            # Sometimes tab structure is different or we are at the end
                            break
                            
                        tab_name = active_tab.text_content().strip()
                        
                        # Check if we're stuck on the same tab
                        if tab_name == last_tab_name:
                            stuck_count += 1
                            if stuck_count > 2:
                                print(f"⚠️  Stuck on tab '{tab_name}' - trying to force next...")
                                # Maybe the data is OK and we just need to click next
                                # Check if validation message is NOT visible
                                error_visible = page.locator("text=Alle Pflichtfelder müssen ausgefüllt sein").first.is_visible() if page.locator("text=Alle Pflichtfelder müssen ausgefüllt sein").count() > 0 else False
                                
                                if not error_visible:
                                    print("  No validation error visible, attempting to proceed...")
                                    if not self._click_next(page):
                                        print("  Could not proceed. Breaking loop.")
                                        break
                                    # If click succeeded, reset counter
                                    stuck_count = 0
                                else:
                                    print("  Validation error present. Breaking loop.")
                                    # Save debug info
                                    try:
                                        page.screenshot(path=f"debug_{tab_name.replace(' ', '_')}.png")
                                        print(f"📸 Screenshot saved")
                                    except:
                                        pass
                                    break
                        else:
                            stuck_count = 0
                            tabs_visited.append(tab_name)
                            print(f"Current Tab: {tab_name}")
                        
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
                            print("Reached 'Akademische Vorbildung'. Stopping navigation as requested.")
                            return f"✅ Bewerbung bis 'Akademische Vorbildung' ausgefüllt.\nTabs: {', '.join(tabs_visited)}"

                        # Click Next to proceed to next tab
                        if not self._click_next(page):
                            print("Could not click Next. Stopping.")
                            break
                            
                    except Exception as e:
                        print(f"Error in navigation loop: {e}")
                        break

                # Success (Draft created)
                return f"✅ Bewerbung für '{study_program}' ({degree_type}, {semester}) erfolgreich angelegt.\nStatus: Wizard durchlaufen bis '{tabs_visited[-1] if tabs_visited else 'Studiengangswahl'}'.\nBitte prüfen Sie den Entwurf in KLIPS2 und ergänzen Sie fehlende Nachweise."
                
            except Exception as e:
                return f"❌ Ein unerwarteter Fehler ist aufgetreten: {str(e)}"

def create_klips2_apply_tool() -> KLIPS2ApplyTool:
    return KLIPS2ApplyTool()
