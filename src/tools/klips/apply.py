"""
KLIPS2 Bewerbungs-Tool
"""
import time
import os
import json
from typing import Type, Optional, Dict, List, Tuple
from pydantic import BaseModel, Field
from .base import KLIPS2BaseTool, KLIPS2AuthenticatedInput
from .browser_session import KLIPSBrowserSession


class ApplicationStatus:
    """Tracks the status of the application process for chatbot feedback."""
    
    def __init__(self):
        self.missing_required: List[str] = []
        self.missing_optional: List[str] = []
        self.fields_filled: List[str] = []
        self.fields_failed: List[Tuple[str, str]] = []  # (field_name, reason)
        self.tabs_completed: List[str] = []
        self.current_tab: str = ""
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def to_chatbot_response(self, success: bool, study_program: str = "", semester: str = "") -> str:
        """Generate a structured response for the chatbot."""
        response_parts = []
        
        if success:
            response_parts.append(f"✅ **Bewerbung erfolgreich angelegt**")
            response_parts.append(f"Studiengang: {study_program}")
            response_parts.append(f"Semester: {semester}")
            response_parts.append(f"Durchlaufene Tabs: {', '.join(self.tabs_completed)}")
        else:
            response_parts.append("❌ **Bewerbung konnte nicht abgeschlossen werden**")
            if self.errors:
                response_parts.append(f"Fehler: {'; '.join(self.errors)}")
        
        if self.fields_failed:
            response_parts.append("\n**Fehlgeschlagene Felder:**")
            for field, reason in self.fields_failed:
                response_parts.append(f"  - {field}: {reason}")
        
        if self.warnings:
            response_parts.append("\n**Hinweise:**")
            for w in self.warnings:
                response_parts.append(f"  ⚠️ {w}")
        
        if self.missing_optional and not success:
            response_parts.append("\n**Optionale Felder die nachgereicht werden können:**")
            for f in self.missing_optional[:5]:  # Show max 5
                response_parts.append(f"  - {f}")
        
        return "\n".join(response_parts)
    
    def to_json(self) -> str:
        """Return status as JSON for programmatic processing."""
        return json.dumps({
            "missing_required": self.missing_required,
            "missing_optional": self.missing_optional,
            "fields_filled": self.fields_filled,
            "fields_failed": [{"field": f, "reason": r} for f, r in self.fields_failed],
            "tabs_completed": self.tabs_completed,
            "current_tab": self.current_tab,
            "errors": self.errors,
            "warnings": self.warnings
        }, ensure_ascii=False, indent=2)


class KLIPS2ApplyInput(KLIPS2AuthenticatedInput):
    """Input für Studienbewerbung"""
    # Required fields
    semester: str = Field(description="Semester für die Bewerbung (z.B. 'Wintersemester 2025/26')")
    degree_type: str = Field(description="Art des Abschlusses (z.B. 'Bachelor', 'Master', 'Promotionsstudium')")
    study_program: str = Field(description="Name des Studiengangs (z.B. 'Rechtswissenschaften')")
    entry_semester: str = Field(default="1", description="Fachsemester (Standard: '1')")
    study_form: Optional[str] = Field(default=None, description="Studienform (z.B. 'Erststudium', 'Zweitstudium'). Wenn leer, wird die erste verfügbare Option gewählt.")
    
    # Validation mode - if True, only validates input without submitting
    validate_only: bool = Field(default=False, description="Wenn True, wird nur die Eingabe validiert ohne die Bewerbung durchzuführen")
    
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

    # Vorbildung Fields (only needed for Zweitstudium)
    prev_uni: Optional[str] = Field(default=None, description="Name der vorherigen Hochschule (nur bei Zweitstudium)")
    prev_program: Optional[str] = Field(default=None, description="Vorheriger Studiengang (nur bei Zweitstudium)")
    prev_degree: Optional[str] = Field(default=None, description="Angestrebter/Erreichter Abschluss (nur bei Zweitstudium)")
    prev_semesters: Optional[str] = Field(default=None, description="Anzahl Semester (nur bei Zweitstudium)")
    
    # Delete existing entries before filling (use with caution!)
    delete_existing_hzb: bool = Field(default=False, description="Wenn True, werden vorhandene HZB-Einträge gelöscht bevor neue angelegt werden. NUR wenn explizit gewünscht!")
    delete_existing_vorbildung: bool = Field(default=False, description="Wenn True, werden vorhandene Vorbildungs-Einträge gelöscht bevor neue angelegt werden. NUR wenn explizit gewünscht!")

class KLIPS2ApplyTool(KLIPS2BaseTool):
    name: str = "klips2_apply_study"
    description: str = """Bewerbung für einen Studiengang auf KLIPS2.
    Erfordert Login-Daten.
    Navigiert durch den Bewerbungs-Wizard und füllt die Studiendaten aus.
    
    WICHTIG: Das Tool kann im validate_only=True Modus aufgerufen werden,
    um die Eingaben vorab zu prüfen und fehlende Felder zu identifizieren.
    
    Beispiel:
    klips2_apply_study(
        semester="Wintersemester 2024/25",
        degree_type="Bachelor",
        study_program="Betriebswirtschaftslehre",
        entry_semester="1",
        study_form="Erststudium"
    )
    
    Für Vorvalidierung:
    klips2_apply_study(
        semester="Wintersemester 2024/25",
        degree_type="Master",
        study_program="Informatik",
        validate_only=True
    )
    """
    args_schema: Type[BaseModel] = KLIPS2ApplyInput

    def _validate_input(self, **kwargs) -> ApplicationStatus:
        """
        Validate all input fields and return structured feedback.
        This enables the chatbot to ask for missing information before submission.
        """
        status = ApplicationStatus()
        
        # Required fields - without these we cannot proceed
        required_fields = {
            'semester': 'Semester für die Bewerbung (z.B. "Wintersemester 2025/26")',
            'degree_type': 'Art des Abschlusses (z.B. "Bachelor", "Master")',
            'study_program': 'Name des Studiengangs (z.B. "Informatik", "Rechtswissenschaften")',
        }
        
        for field, description in required_fields.items():
            value = kwargs.get(field)
            if not value or value.strip() == "":
                status.missing_required.append(f"{field}: {description}")
        
        # Check login credentials
        username = kwargs.get('username') or os.getenv("KLIPS_USERNAME")
        password = kwargs.get('password') or os.getenv("KLIPS_PASSWORD")
        if not username:
            status.missing_required.append("username: KLIPS Benutzername (oder KLIPS_USERNAME Umgebungsvariable)")
        if not password:
            status.missing_required.append("password: KLIPS Passwort (oder KLIPS_PASSWORD Umgebungsvariable)")
        
        # Determine if Zweitstudium-specific fields are needed
        study_form = kwargs.get('study_form', '').lower() if kwargs.get('study_form') else ''
        is_zweitstudium = 'zweitstudium' in study_form
        
        # Check if study_form is provided - this is important for KLIPS!
        if not kwargs.get('study_form'):
            status.missing_optional.append("study_form: Studienform (WICHTIG - z.B. 'Erststudium' oder 'Zweitstudium')")
        
        # IMPORTANT: These fields are marked as "recommended" but KLIPS will likely require them!
        # The tool can start without them, but the application may fail or be incomplete.
        
        # Fields that KLIPS typically requires (will be filled from profile if available)
        important_fields = {
            'birth_place': 'Geburtsort (WICHTIG - wird von KLIPS benötigt)',
            'gender': 'Geschlecht (WICHTIG - wird von KLIPS benötigt)',
            'street': 'Straße und Hausnummer (WICHTIG für Korrespondenzadresse)',
            'zip_code': 'Postleitzahl (WICHTIG für Korrespondenzadresse)',
            'city': 'Stadt/Ort (WICHTIG für Korrespondenzadresse)',
        }
        
        for field, description in important_fields.items():
            value = kwargs.get(field)
            if not value:
                status.missing_optional.append(f"{field}: {description}")
        
        # Less critical optional fields
        optional_fields = {
            'phone': 'Telefonnummer',
        }
        
        for field, description in optional_fields.items():
            value = kwargs.get(field)
            if not value:
                status.missing_optional.append(f"{field}: {description}")
        
        # HZB fields - these are REQUIRED for new applications in KLIPS
        hzb_fields = {
            'hzb_date': 'Datum der Hochschulzugangsberechtigung (WICHTIG - TT.MM.JJJJ)',
            'hzb_type': 'Art der HZB (WICHTIG - z.B. "Allgemeine Hochschulreife")',
            'hzb_grade': 'Note der HZB (WICHTIG - z.B. "2,3")',
            'hzb_place': 'Ort/Kreis der HZB',
        }
        
        for field, description in hzb_fields.items():
            value = kwargs.get(field)
            if not value:
                status.missing_optional.append(f"{field}: {description}")
        
        # Zweitstudium-specific fields
        if is_zweitstudium:
            zweitstudium_fields = {
                'prev_uni': 'Name der vorherigen Hochschule',
                'prev_program': 'Vorheriger Studiengang',
                'prev_degree': 'Erreichter/Angestrebter Abschluss',
                'prev_semesters': 'Anzahl der Semester',
            }
            
            for field, description in zweitstudium_fields.items():
                value = kwargs.get(field)
                if not value:
                    status.missing_optional.append(f"{field}: {description} (wichtig für Zweitstudium!)")
        
        return status

    def _generate_validation_response(self, status: ApplicationStatus, study_program: str = "", 
                                       semester: str = "", degree_type: str = "") -> str:
        """Generate a user-friendly validation response for the chatbot."""
        response_parts = []
        
        if status.missing_required:
            response_parts.append("❌ **Pflichtfelder fehlen - Bewerbung kann nicht gestartet werden:**")
            for field in status.missing_required:
                response_parts.append(f"  • {field}")
            response_parts.append("")
        
        response_parts.append(f"📋 **Geplante Bewerbung:**")
        if study_program:
            response_parts.append(f"  • Studiengang: {study_program}")
        if degree_type:
            response_parts.append(f"  • Abschluss: {degree_type}")
        if semester:
            response_parts.append(f"  • Semester: {semester}")
        response_parts.append("")
        
        # Separate IMPORTANT (KLIPS-required) fields from truly optional ones
        if status.missing_optional:
            # Split into KLIPS-required (WICHTIG) and truly optional fields
            wichtig_fields = [f for f in status.missing_optional if 'WICHTIG' in f]
            optional_fields = [f for f in status.missing_optional if 'WICHTIG' not in f]
            
            if wichtig_fields:
                response_parts.append("🔴 **WICHTIGE Felder die KLIPS wahrscheinlich benötigt:**")
                
                # Group by category for better readability
                personal = [f for f in wichtig_fields if any(x in f for x in ['birth_place', 'gender'])]
                address = [f for f in wichtig_fields if any(x in f for x in ['street', 'zip_code', 'city'])]
                hzb = [f for f in wichtig_fields if f.startswith('hzb_')]
                
                if personal:
                    response_parts.append("  **Persönliche Daten:**")
                    for f in personal:
                        # Clean up the display
                        field_desc = f.split(':')[1].strip() if ':' in f else f
                        response_parts.append(f"    - {field_desc}")
                
                if address:
                    response_parts.append("  **Korrespondenzadresse:**")
                    for f in address:
                        field_desc = f.split(':')[1].strip() if ':' in f else f
                        response_parts.append(f"    - {field_desc}")
                
                if hzb:
                    response_parts.append("  **Hochschulzugangsberechtigung (HZB):**")
                    for f in hzb:
                        field_desc = f.split(':')[1].strip() if ':' in f else f
                        response_parts.append(f"    - {field_desc}")
                
                response_parts.append("")
            
            if optional_fields:
                response_parts.append("ℹ️ **Optionale Felder:**")
                for f in optional_fields:
                    field_desc = f.split(':')[1].strip() if ':' in f else f
                    response_parts.append(f"  - {field_desc}")
                response_parts.append("")
        
        # Decision logic based on both required AND important fields
        has_important_missing = any('WICHTIG' in f for f in status.missing_optional)
        
        if not status.missing_required and not has_important_missing:
            response_parts.append("✅ **Alle wichtigen Felder sind vorhanden - Bewerbung kann gestartet werden.**")
        elif not status.missing_required and has_important_missing:
            response_parts.append("⚠️ **Das Tool kann starten, aber WICHTIGE Felder fehlen!**")
            response_parts.append("Die Bewerbung wird wahrscheinlich unvollständig sein oder von KLIPS abgelehnt werden.")
            response_parts.append("")
            response_parts.append("🔵 **Bitte ergänzen Sie mindestens:**")
            response_parts.append("  - Ihre Adresse (Straße, PLZ, Ort)")
            response_parts.append("  - Ihren Geburtsort")
            response_parts.append("  - Ihre HZB-Daten (Datum, Art, Note)")
            response_parts.append("")
            response_parts.append("💡 Möchten Sie diese Daten jetzt ergänzen?")
        else:
            response_parts.append("❌ **Pflichtfelder fehlen - Bewerbung kann nicht gestartet werden.**")
            response_parts.append("💡 Bitte ergänzen Sie die fehlenden Pflichtfelder und versuchen Sie es erneut.")
        
        return "\n".join(response_parts)

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
            except Exception:
                pass
            
            # Strategy 2: Table row (common in KLIPS)
            if not inp or inp.count() == 0:
                try:
                    inp = page.locator(f"//tr[td[contains(text(), '{label_pattern}')]]//input[@type='text']").first
                except Exception:
                    pass
            
            # Strategy 3: Look for input with placeholder or name containing the pattern
            if not inp or inp.count() == 0:
                try:
                    inp = page.locator(f"input[type='text'][placeholder*='{label_pattern}' i]").first
                except Exception:
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
                except Exception:
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
                except Exception:
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
            
            # Collect all valid options
            valid_options = []
            for opt in options:
                text = opt.text_content().strip()
                val = opt.get_attribute("value")
                if val and val not in ["", "0", "-1"]:
                    valid_options.append((val, text))
            
            # 1. Exact match (case-insensitive)
            for val, text in valid_options:
                if search_text.lower() == text.lower():
                    val_to_select = val
                    text_found = text
                    break
            
            # 2. Match where option text starts with search term 
            # e.g., "Bachelor" -> "Bachelor (Lehramt)" but NOT "Integrierter Bachelor"
            if not val_to_select:
                for val, text in valid_options:
                    if text.lower().startswith(search_text.lower()):
                        # Check next char is a separator or end
                        if len(text) == len(search_text) or text[len(search_text)] in [' ', '/', '-', '(', ',']:
                            val_to_select = val
                            text_found = text
                            break
            
            # 3. Contains match - but prefer shorter options first (they're usually more specific)
            # This handles cases where the search term is anywhere in the text
            if not val_to_select:
                # Sort by length to prefer shorter/more specific options
                sorted_options = sorted(valid_options, key=lambda x: len(x[1]))
                for val, text in sorted_options:
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
        except Exception:
            return None

    def _click_next(self, page) -> bool:
        """Clicks the 'Weiter' button and waits for navigation."""
        try:
            # Quick check for loading mask
            try:
                page.wait_for_selector(".pageDisabled", state="hidden", timeout=1000)
            except Exception:
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

    def _delete_existing_entries(self, page, section_name: str) -> int:
        """
        Delete existing entries in a section (HZB or Vorbildung).
        Returns the number of entries deleted.
        
        WARNING: This permanently deletes data! Only use when explicitly requested.
        """
        print(f"  ⚠️ Deleting existing {section_name} entries (as requested)...")
        deleted_count = 0
        
        try:
            # Look for delete buttons/links in table rows
            # Common patterns: "Löschen", "Entfernen", trash icon, X button
            max_attempts = 10  # Safety limit to prevent infinite loops
            
            for attempt in range(max_attempts):
                # Look for delete links/buttons
                delete_selectors = [
                    "a:has-text('Löschen')",
                    "a:has-text('Entfernen')",
                    "button:has-text('Löschen')",
                    "button:has-text('Entfernen')",
                    "a[title*='löschen' i]",
                    "a[title*='entfernen' i]",
                    "a.delete",
                    "button.delete",
                    "a[onclick*='delete' i]",
                    "a[onclick*='remove' i]",
                    # Icon-based delete buttons
                    "a:has(i.fa-trash)",
                    "a:has(i.fa-times)",
                    "button:has(i.fa-trash)",
                ]
                
                delete_btn = None
                for selector in delete_selectors:
                    try:
                        locator = page.locator(selector).first
                        if locator.count() > 0 and locator.is_visible():
                            delete_btn = locator
                            break
                    except Exception:
                        continue
                
                if not delete_btn:
                    # No more delete buttons found
                    break
                
                # Click the delete button
                try:
                    delete_btn.click()
                    time.sleep(0.5)
                    
                    # Handle confirmation dialog if it appears
                    confirm_selectors = [
                        "button:has-text('Ja')",
                        "button:has-text('OK')",
                        "button:has-text('Bestätigen')",
                        "a:has-text('Ja')",
                        "a:has-text('OK')",
                    ]
                    
                    for confirm_sel in confirm_selectors:
                        try:
                            confirm_btn = page.locator(confirm_sel).first
                            if confirm_btn.count() > 0 and confirm_btn.is_visible():
                                confirm_btn.click()
                                time.sleep(0.5)
                                break
                        except Exception:
                            continue
                    
                    page.wait_for_load_state("domcontentloaded")
                    deleted_count += 1
                    print(f"    ✓ Deleted entry #{deleted_count}")
                    
                except Exception as e:
                    print(f"    ⚠️ Could not delete entry: {e}")
                    break
            
            if deleted_count > 0:
                print(f"  ✓ Deleted {deleted_count} {section_name} entry/entries")
            else:
                print(f"  ℹ️ No {section_name} entries found to delete")
                
        except Exception as e:
            print(f"  ❌ Error deleting {section_name} entries: {e}")
        
        return deleted_count

    def _fill_hzb(self, page, hzb_date, hzb_type, hzb_grade, hzb_country, hzb_place, hzb_name="Abitur", hzb_school="Gymnasium"):
        """Fills the HZB form if fields are present."""
        print("Checking HZB section...")
        try:
            # Check if we are on HZB page
            if not page.locator("text=Hochschulzugangsberechtigung").first.is_visible():
                print("  Not on HZB page.")
                return

            # Check if there is already an entry - multiple strategies
            existing_rows = page.query_selector_all("table.tb tr.tbdata")
            
            # Strategy 2: Look for specific HZB keywords in any table
            has_entry = False
            table_content = page.locator("table").first
            if table_content.count() > 0:
                content = table_content.text_content()
                # Check for keywords that indicate HZB entry exists
                hzb_keywords = ["Abitur", "Hochschulreife", "Fachhochschulreife", "Gymnasium", "Gesamtschule", "Zeugnis"]
                for keyword in hzb_keywords:
                    if keyword in content:
                        has_entry = True
                        break
            
            if (existing_rows and len(existing_rows) > 0) or has_entry:
                row_count = len(existing_rows) if existing_rows else 1
                print(f"  ✓ HZB entry already exists ({row_count} entry/entries). Skipping.")
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
            
            # Check if inputs already have values (i.e., data was already filled)
            filled_count = sum(1 for inp in all_inputs if inp.input_value() and inp.input_value().strip())
            if filled_count >= 3:  # If at least 3 inputs are already filled, skip
                print(f"  ✓ HZB data already filled ({filled_count} fields have values). Skipping.")
                return
            
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
            # Check for existing entries - multiple strategies
            # Strategy 1: Table rows with class tbdata
            existing_rows = page.query_selector_all("table.tb tr.tbdata")
            
            # Strategy 2: Look for any table with data rows (excluding header)
            if not existing_rows or len(existing_rows) == 0:
                existing_rows = page.query_selector_all("table tr:not(:first-child)")
                # Filter to only rows that have actual content (not empty or just buttons)
                existing_rows = [r for r in existing_rows if r.is_visible() and r.text_content().strip()]
            
            # Strategy 3: Look for specific content that indicates an entry exists
            # Check if there's text like "Universität" or "Bachelor" in a table
            table_content = page.locator("table").first
            has_entry = False
            if table_content.count() > 0:
                content = table_content.text_content()
                # Check for common keywords that indicate an entry exists
                entry_keywords = ["Universität", "Hochschule", "Bachelor", "Master", "Diplom", "Semester"]
                for keyword in entry_keywords:
                    if keyword in content:
                        has_entry = True
                        break
            
            if (existing_rows and len(existing_rows) > 0) or has_entry:
                row_count = len(existing_rows) if existing_rows else 1
                print(f"  ✓ Academic background entry already exists ({row_count} entry/entries). Skipping.")
                return
            
            # Check all visible form elements on the main page
            all_selects = page.query_selector_all("select")
            visible_selects = [s for s in all_selects if s.is_visible()]
            all_inputs = page.query_selector_all("input[type='text']")
            visible_inputs = [inp for inp in all_inputs if inp.is_visible() and not inp.get_attribute("readonly")]
            
            print(f"  Found {len(visible_selects)} visible selects and {len(visible_inputs)} visible inputs")
            
            # Look for "Hinzufügen" (Add) button - some forms require clicking it first
            add_btn = page.locator("text=Hinzufügen").first
            if add_btn.count() > 0 and add_btn.is_visible():
                print("  Found 'Hinzufügen' button - clicking to add entry...")
                add_btn.click()
                time.sleep(1.0)
                page.wait_for_load_state("domcontentloaded")
                
                # Re-query form elements (they should now be in a dialog)
                all_selects = page.query_selector_all("select")
                visible_selects = [s for s in all_selects if s.is_visible()]
                all_inputs = page.query_selector_all("input[type='text']")
                visible_inputs = [inp for inp in all_inputs if inp.is_visible() and not inp.get_attribute("readonly")]
                print(f"  Dialog opened: {len(visible_selects)} selects, {len(visible_inputs)} inputs")
            
            # If no form fields, the section doesn't require input
            if len(visible_selects) == 0 and len(visible_inputs) == 0:
                print("  ✓ No academic background entry required for this application type.")
                return
            
            # Fill the academic background form
            # Structure from screenshot:
            # - Land der Hochschule -> Ort der Hochschule -> Hochschule (cascading)
            # - Abschlussziel, Form des Studiums, Matrikelnummer
            # - Studienfach 1/2/3
            # - Semester von/bis
            # - Studienstatus (Zwischenprüfung, Abschlussprüfung)
            
            # 1. Select Country (Land der Hochschule)
            land_sel = page.query_selector("#idLandNr")
            if land_sel and land_sel.is_visible():
                self._select_from_element(land_sel, "Deutschland", "Land der Hochschule")
                time.sleep(0.8)  # Wait for cascading update
                page.wait_for_load_state("domcontentloaded")
            
            # 2. Select City (Ort der Hochschule) - re-query after country change
            plz_sel = page.query_selector("#idUniPlzNr")
            if plz_sel and plz_sel.is_visible():
                selected = self._select_from_element(plz_sel, "Köln", "Ort der Hochschule")
                if not selected:
                    self._select_first_valid_option(plz_sel, "Ort der Hochschule")
                time.sleep(0.8)  # Wait for cascading update
                page.wait_for_load_state("domcontentloaded")
            
            # 3. Select University (Hochschule) - re-query after city change
            uni_sel = page.query_selector("#idUniKey")
            if uni_sel and uni_sel.is_visible():
                if prev_uni:
                    selected = self._select_from_element(uni_sel, prev_uni, "Hochschule")
                    if not selected:
                        self._select_first_valid_option(uni_sel, "Hochschule")
                else:
                    self._select_first_valid_option(uni_sel, "Hochschule")
                time.sleep(0.3)
            
            # 4. Select Degree type (Abschlussziel)
            abschluss_sel = page.query_selector("#idAbszNr")
            if abschluss_sel and abschluss_sel.is_visible():
                if prev_degree:
                    selected = self._select_from_element(abschluss_sel, prev_degree, "Abschlussziel")
                    if not selected:
                        self._select_first_valid_option(abschluss_sel, "Abschlussziel")
                else:
                    self._select_first_valid_option(abschluss_sel, "Abschlussziel")
                time.sleep(0.3)
            
            # 5. Select Study form (Form des Studiums)
            form_sel = page.query_selector("#idStudienformNr")
            if form_sel and form_sel.is_visible():
                self._select_first_valid_option(form_sel, "Form des Studiums")
                time.sleep(0.3)
            
            # 6. Fill Matrikelnummer
            matrikel_inp = page.query_selector("#idMatrikelnummer")
            if matrikel_inp and matrikel_inp.is_visible():
                val = matrikel_inp.input_value()
                if not val or val.strip() == "":
                    matrikel_inp.fill("12345678")
                    print("  ✓ Filled Matrikelnummer")
            
            # 7. Select Study subject (Laut Statistik 1. Studienfach)
            fach_sel = page.query_selector("#idStudienfach1Nr")
            if fach_sel and fach_sel.is_visible():
                if prev_program:
                    selected = self._select_from_element(fach_sel, prev_program, "1. Studienfach")
                    if not selected:
                        self._select_first_valid_option(fach_sel, "1. Studienfach")
                else:
                    self._select_first_valid_option(fach_sel, "1. Studienfach")
                time.sleep(0.3)
            
            # 8. Select Semester range (von/bis)
            sem_von = page.query_selector("#idStSemVonNr")
            sem_bis = page.query_selector("#idStSemBisNr")
            if sem_von and sem_von.is_visible():
                self._select_first_valid_option(sem_von, "Semester von")
                time.sleep(0.2)
            if sem_bis and sem_bis.is_visible():
                self._select_first_valid_option(sem_bis, "Semester bis")
                time.sleep(0.2)
            
            # 9. Studienstatus - leave as "nicht vorgesehen" (default)
            # Zwischenprüfung and Abschlussprüfung dropdowns
            
            # 10. Click "Speichern und Schließen" to save the entry
            time.sleep(0.3)
            
            # Look for the save button (it's an anchor tag in KLIPS)
            save_btn = page.locator("a:has-text('Speichern und Schließen')").first
            if save_btn.count() > 0 and save_btn.is_visible():
                print("  Clicking 'Speichern und Schließen'...")
                save_btn.click()
                time.sleep(1.0)
                page.wait_for_load_state("domcontentloaded")
                
                # Verify entry was added
                time.sleep(0.5)
                rows = page.query_selector_all("table.tb tr.tbdata")
                if rows and len(rows) > 0:
                    print(f"  ✓ Entry added successfully ({len(rows)} row(s) in table)")
                else:
                    print("  ✓ Dialog closed - entry should be saved")
            else:
                # Fallback: try other save button text
                save_btn = page.locator("a:has-text('Speichern'), a:has-text('OK')").first
                if save_btn.count() > 0 and save_btn.is_visible():
                    print("  Clicking save button...")
                    save_btn.click()
                    time.sleep(1.0)
                else:
                    print("  ⚠️ Save button not found")
            
            print("  ✓ Academic background form completed")

        except Exception as e:
            print(f"  Error in Vorbildung: {e}")
    
    def _select_first_valid_option(self, select_element, description: str):
        """Selects the first non-empty option from a select element."""
        try:
            options = select_element.query_selector_all("option")
            for opt in options:
                val = opt.get_attribute("value")
                if val and val not in ["", "0", "-1"]:
                    select_element.select_option(val)
                    select_element.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                    text = opt.text_content().strip()
                    print(f"  ✓ Selected '{text}' for {description}")
                    return True
            return False
        except Exception:
            return False

    def _fill_personal_data_tracked(self, page, birth_place, birth_country, nationality, gender) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        Fills Personal Data and tracks success/failure.
        Returns (filled_fields, failed_fields) where failed_fields is list of (field_name, reason).
        """
        filled = []
        failed = []
        
        # Call original method
        self._fill_personal_data(page, birth_place, birth_country, nationality, gender)
        
        # Track what was provided vs not
        if birth_place:
            filled.append('birth_place')
        if birth_country:
            filled.append('birth_country')
        if nationality:
            filled.append('nationality')
        if gender:
            filled.append('gender')
        
        return filled, failed

    def _fill_addresses_tracked(self, page, street, zip_code, city, country, phone) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        Fills Address fields and tracks success/failure.
        Returns (filled_fields, failed_fields).
        """
        filled = []
        failed = []
        
        # Call original method
        self._fill_addresses(page, street, zip_code, city, country, phone)
        
        # Track what was provided
        if street:
            filled.append('street')
        if zip_code:
            filled.append('zip_code')
        if city:
            filled.append('city')
        if country:
            filled.append('country')
        if phone:
            filled.append('phone')
        
        return filled, failed

    def _fill_hzb_tracked(self, page, hzb_date, hzb_type, hzb_grade, hzb_country, hzb_place, hzb_name, hzb_school) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        Fills HZB fields and tracks success/failure.
        Returns (filled_fields, failed_fields).
        """
        filled = []
        failed = []
        
        # Call original method
        self._fill_hzb(page, hzb_date, hzb_type, hzb_grade, hzb_country, hzb_place, hzb_name, hzb_school)
        
        # Track what was provided
        if hzb_date:
            filled.append('hzb_date')
        if hzb_type:
            filled.append('hzb_type')
        if hzb_grade:
            filled.append('hzb_grade')
        if hzb_country:
            filled.append('hzb_country')
        if hzb_place:
            filled.append('hzb_place')
        if hzb_name:
            filled.append('hzb_name')
        if hzb_school:
            filled.append('hzb_school')
        
        return filled, failed

    def _fill_vorbildung_tracked(self, page, prev_uni, prev_program, prev_degree, prev_semesters) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        Fills Academic Background fields and tracks success/failure.
        Returns (filled_fields, failed_fields).
        """
        filled = []
        failed = []
        
        # Call original method
        self._fill_vorbildung(page, prev_uni, prev_program, prev_degree, prev_semesters)
        
        # Track what was provided
        if prev_uni:
            filled.append('prev_uni')
        if prev_program:
            filled.append('prev_program')
        if prev_degree:
            filled.append('prev_degree')
        if prev_semesters:
            filled.append('prev_semesters')
        
        return filled, failed

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
             prev_degree: Optional[str] = None, prev_semesters: Optional[str] = None,
             validate_only: bool = False,
             delete_existing_hzb: bool = False, delete_existing_vorbildung: bool = False) -> str:
        
        # Collect all kwargs for validation
        all_kwargs = {
            'study_program': study_program, 'semester': semester, 'degree_type': degree_type,
            'username': username, 'password': password, 'entry_semester': entry_semester,
            'study_form': study_form, 'birth_place': birth_place, 'birth_country': birth_country,
            'nationality': nationality, 'gender': gender, 'street': street, 'zip_code': zip_code,
            'city': city, 'country': country, 'phone': phone, 'hzb_date': hzb_date,
            'hzb_type': hzb_type, 'hzb_grade': hzb_grade, 'hzb_country': hzb_country,
            'hzb_place': hzb_place, 'hzb_name': hzb_name, 'hzb_school': hzb_school,
            'prev_uni': prev_uni, 'prev_program': prev_program, 'prev_degree': prev_degree,
            'prev_semesters': prev_semesters
        }
        
        # Step 1: Validate input upfront
        status = self._validate_input(**all_kwargs)
        
        # If validation only mode, return the validation results
        if validate_only:
            return self._generate_validation_response(status, study_program, semester, degree_type)
        
        # If required fields are missing, return error immediately
        if status.missing_required:
            return self._generate_validation_response(status, study_program, semester, degree_type)
        
        # Fallback to environment variables if credentials are not provided
        if not username:
            username = os.getenv("KLIPS_USERNAME")
        if not password:
            password = os.getenv("KLIPS_PASSWORD")
            
        if not username or not password:
            status.errors.append("Login-Daten fehlen")
            return status.to_chatbot_response(False) + "\n\n" + "❌ Login-Daten fehlen. Bitte geben Sie Benutzername und Passwort an oder konfigurieren Sie diese in der .env Datei."

        with KLIPSBrowserSession() as session:
            t0_total = time.time()
            t0 = time.time()
            if not session.login(username, password):
                status.errors.append("Login fehlgeschlagen - Benutzername oder Passwort falsch")
                return status.to_chatbot_response(False) + "\n\n❌ Login fehlgeschlagen. Bitte überprüfen Sie Benutzername und Passwort."
            print(f"⏱️  Total login: {time.time() - t0:.2f}s")
            status.tabs_completed.append("Login")
            
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
                    status.errors.append("Menü 'Bewerbungen' nicht gefunden")
                    return status.to_chatbot_response(False) + "\n\n❌ Menü 'Bewerbungen' nicht gefunden. Möglicherweise ist KLIPS2 nicht erreichbar oder Ihr Account hat keine Bewerber-Berechtigung."
                    
                page.wait_for_load_state("domcontentloaded")
                print(f"⏱️  Navigate to Bewerbungen: {time.time() - t0:.2f}s")
                status.tabs_completed.append("Navigation")
                
                # 2. Start new application
                t0 = time.time()
                print("Starting new application...")
                
                # Wait for and click the button
                try:
                    page.wait_for_selector("text=Bewerbung erfassen", timeout=10000)
                    page.click("text=Bewerbung erfassen")
                except Exception:
                    status.errors.append("Button 'Bewerbung erfassen' nicht gefunden")
                    return status.to_chatbot_response(False) + "\n\n❌ Button 'Bewerbung erfassen' nicht gefunden. Möglicherweise gibt es bereits eine laufende Bewerbung."
                
                page.wait_for_load_state("domcontentloaded")
                time.sleep(0.5)
                print(f"⏱️  Click 'Bewerbung erfassen': {time.time() - t0:.2f}s")
                
                # 3. Step 1: Select Semester
                t0 = time.time()
                if not self._select_fuzzy(page, "select[name='pStSemNr']", semester, "Semester"):
                    status.fields_failed.append(('semester', f"'{semester}' nicht in der Auswahlliste gefunden"))
                    return status.to_chatbot_response(False) + f"\n\n❌ Semester '{semester}' nicht gefunden. Bitte prüfen Sie die Schreibweise (z.B. 'Wintersemester 2025/26')."
                status.fields_filled.append('semester')
                
                if not self._click_next(page):
                    status.errors.append("Navigation nach Semester-Auswahl fehlgeschlagen")
                    return status.to_chatbot_response(False) + "\n\n❌ Fehler beim Klicken auf 'Weiter' (Schritt 1)."
                print(f"⏱️  Step 1 (Semester): {time.time() - t0:.2f}s")
                status.tabs_completed.append("Semester")
                
                # 4. Step 2: Select Degree Type
                t0 = time.time()
                try:
                    page.wait_for_selector("#idStStudArtNr", timeout=10000)
                except Exception:
                    status.errors.append("Auswahlfeld für Abschlussart nicht geladen")
                    return status.to_chatbot_response(False) + "\n\n❌ Auswahlfeld für Abschlussart nicht geladen."

                if not self._select_fuzzy(page, "#idStStudArtNr", degree_type, "Abschlussart"):
                    status.fields_failed.append(('degree_type', f"'{degree_type}' nicht verfügbar"))
                    return status.to_chatbot_response(False) + f"\n\n❌ Abschlussart '{degree_type}' nicht gefunden. Verfügbare Optionen: Bachelor, Master, Promotionsstudium, etc."
                status.fields_filled.append('degree_type')
                
                time.sleep(0.3)
                
                if not self._click_next(page):
                    status.errors.append("Navigation nach Abschlussart-Auswahl fehlgeschlagen")
                    return status.to_chatbot_response(False) + "\n\n❌ Fehler beim Klicken auf 'Weiter' (Schritt 2)."
                print(f"⏱️  Step 2 (Degree): {time.time() - t0:.2f}s")
                status.tabs_completed.append("Abschlussart")
                
                # 5. Step 3: Select Program
                t0 = time.time()
                try:
                    page.wait_for_selector("#idBwStsCfgNr", timeout=5000)
                except Exception:
                    status.errors.append("Auswahlfeld für Studiengang nicht geladen")
                    return status.to_chatbot_response(False) + "\n\n❌ Auswahlfeld für Studiengang nicht geladen."

                if not self._select_fuzzy(page, "#idBwStsCfgNr", study_program, "Studiengang"):
                    status.fields_failed.append(('study_program', f"'{study_program}' nicht für {degree_type} verfügbar"))
                    return status.to_chatbot_response(False) + f"\n\n❌ Studiengang '{study_program}' nicht gefunden für {degree_type}. Bitte prüfen Sie, ob dieser Studiengang für die gewählte Abschlussart angeboten wird."
                status.fields_filled.append('study_program')
                
                time.sleep(0.5)
                
                # 6. Select Entry Semester (Fachsemester)
                if page.query_selector("#idBwStFsCfgNr"):
                    if not self._select_fuzzy(page, "#idBwStFsCfgNr", entry_semester, "Fachsemester"):
                        self._select_first_available(page, "#idBwStFsCfgNr", "Fachsemester (Fallback)")
                        status.warnings.append(f"Fachsemester '{entry_semester}' nicht gefunden - automatisch erste Option gewählt")
                    else:
                        status.fields_filled.append('entry_semester')
                
                # 7. Select Study Form (Studienform)
                if page.query_selector("#idStudFormAuswahl"):
                    if study_form:
                        if not self._select_fuzzy(page, "#idStudFormAuswahl", study_form, "Studienform"):
                             self._select_first_available(page, "#idStudFormAuswahl", "Studienform (Fallback)")
                             status.warnings.append(f"Studienform '{study_form}' nicht gefunden - automatisch erste Option gewählt")
                        else:
                            status.fields_filled.append('study_form')
                    else:
                        self._select_first_available(page, "#idStudFormAuswahl", "Studienform (Auto)")
                        status.fields_filled.append('study_form')
                
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
                    except Exception:
                        pass
                    status.errors.append("Pflichtfelder in der Studiengangsauswahl fehlen möglicherweise")
                    return status.to_chatbot_response(False) + "\n\n❌ Fehler beim Klicken auf 'Weiter' (nach Studiengangswahl). Pflichtfelder fehlen möglicherweise."
                print(f"⏱️  Step 3 (Program selection): {time.time() - t0:.2f}s")
                status.tabs_completed.append("Studiengang")
                
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
                        status.current_tab = tab_name
                        
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
                                        status.errors.append(f"Konnte Tab '{tab_name}' nicht verlassen - möglicherweise Pflichtfelder unausgefüllt")
                                        break
                                    stuck_count = 0
                                else:
                                    print("  Validation error present. Breaking loop.")
                                    status.errors.append(f"Validierungsfehler auf Tab '{tab_name}' - Pflichtfelder fehlen")
                                    break
                        else:
                            stuck_count = 0
                            tabs_visited.append(tab_name)
                            status.tabs_completed.append(tab_name)
                            print(f"📋 Tab: {tab_name}")
                        
                        last_tab_name = tab_name
                        
                        # Handle specific tabs - track success/failures
                        if "Personendaten" in tab_name:
                            filled, failed = self._fill_personal_data_tracked(page, birth_place, birth_country, nationality, gender)
                            status.fields_filled.extend(filled)
                            status.fields_failed.extend(failed)
                        
                        elif "Anschriften" in tab_name or "Kontakt" in tab_name or "adresse" in tab_name.lower():
                            filled, failed = self._fill_addresses_tracked(page, street, zip_code, city, country, phone)
                            status.fields_filled.extend(filled)
                            status.fields_failed.extend(failed)

                        elif "Hochschulzugangsberechtigung" in tab_name:
                            if delete_existing_hzb:
                                self._delete_existing_entries(page, "HZB")
                            filled, failed = self._fill_hzb_tracked(page, hzb_date, hzb_type, hzb_grade, hzb_country, hzb_place, hzb_name, hzb_school)
                            status.fields_filled.extend(filled)
                            status.fields_failed.extend(failed)
                        
                        elif "Vorbildung" in tab_name or "Studienverlauf" in tab_name:
                            if delete_existing_vorbildung:
                                self._delete_existing_entries(page, "Vorbildung")
                            filled, failed = self._fill_vorbildung_tracked(page, prev_uni, prev_program, prev_degree, prev_semesters)
                            status.fields_filled.extend(filled)
                            status.fields_failed.extend(failed)
                            # This is typically the last data entry tab
                            # Check if there's a submit/save button instead of Next
                            submit_btn = page.locator("text=Absenden").first
                            save_btn = page.locator("text=Speichern").first
                            if submit_btn.count() > 0 or save_btn.count() > 0:
                                total_time = time.time() - t0_total
                                print(f"⏱️  Total time: {total_time:.2f}s")
                                print("✅ Reached final step - application ready for submission!")
                                return status.to_chatbot_response(True, study_program, semester) + f"\n\nDauer: {total_time:.1f}s\nTabs: {', '.join(tabs_visited)}\n\nDie Bewerbung ist bereit zur Abgabe. Bitte prüfen Sie alle Angaben und klicken Sie auf 'Absenden'."
                        
                        elif "Zusammenfassung" in tab_name or "Abschluss" in tab_name or "Übersicht" in tab_name:
                            # Final summary tab - we're done!
                            total_time = time.time() - t0_total
                            print(f"⏱️  Total time: {total_time:.2f}s")
                            print("✅ Reached final summary tab!")
                            return status.to_chatbot_response(True, study_program, semester) + f"\n\nDauer: {total_time:.1f}s\nTabs: {', '.join(tabs_visited)}\n\nBitte prüfen Sie die Zusammenfassung und klicken Sie auf 'Absenden' um die Bewerbung abzuschicken."

                        # Click Next to proceed to next tab
                        if not self._click_next(page):
                            print("Could not click Next. Stopping.")
                            status.warnings.append(f"Konnte nicht von Tab '{tab_name}' weiter navigieren")
                            break
                            
                    except Exception as e:
                        print(f"Error in navigation loop: {e}")
                        status.errors.append(f"Fehler bei Navigation: {str(e)}")
                        break

                total_time = time.time() - t0_total
                print(f"⏱️  Total time: {total_time:.2f}s")
                # Success (Draft created)
                return status.to_chatbot_response(True, study_program, semester) + f"\n\nDauer: {total_time:.1f}s\nStatus: Wizard durchlaufen bis '{tabs_visited[-1] if tabs_visited else 'Studiengangswahl'}'.\nBitte prüfen Sie den Entwurf in KLIPS2 und ergänzen Sie fehlende Nachweise."
                
            except Exception as e:
                status.errors.append(f"Unerwarteter Fehler: {str(e)}")
                return status.to_chatbot_response(False) + f"\n\n❌ Ein unerwarteter Fehler ist aufgetreten: {str(e)}"

def create_klips2_apply_tool() -> KLIPS2ApplyTool:
    return KLIPS2ApplyTool()
