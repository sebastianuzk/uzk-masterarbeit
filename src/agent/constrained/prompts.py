"""
Prompt-Builder für den Constrained Agent.

Enthält die Logik zur dynamischen Generierung der System-Prompts und
Extraktions-Prompts basierend auf den verfügbaren Tools.
"""

from typing import Set, Type

from pydantic import BaseModel

from src.agent.constrained.schemas import TOOL_SCHEMAS


def get_system_prompt(available_tool_names: Set[str]) -> str:
    """Kompakter System-Prompt für Constrained Agent."""
    # Dynamische Tool-Kategorien
    tool_categories = []
    if any(name.startswith("klips2_") for name in available_tool_names):
        tool_categories.append("KLIPS2-Aktionen")
    if "university_knowledge_search" in available_tool_names:
        tool_categories.append("Uni-Wissensfragen")
    if "duckduckgo_search" in available_tool_names:
        tool_categories.append("Internet-Suche")
    if "web_scraper" in available_tool_names:
        tool_categories.append("URLs")
    if "send_email" in available_tool_names:
        tool_categories.append("E-Mails")

    tool_categories_text = ", ".join(tool_categories) if tool_categories else "Verfügbare Tools je nach Anfrage"

    # Dynamische Tool-Liste mit Pflichtparametern
    klips_tools = []
    if "klips2_register" in available_tool_names:
        klips_tools.append("- klips2_register: vorname, nachname, geschlecht, geburtsdatum, email, staatsangehoerigkeit")
    if "klips2_apply_study" in available_tool_names:
        klips_tools.append("- klips2_apply_study: username, password, semester, degree_type, study_program, study_form, gender, birth_place, nationality, hzb_date, hzb_type, hzb_grade, hzb_place")
    if "klips2_change_address" in available_tool_names:
        klips_tools.append("- klips2_change_address: username, password, street, zip_code, city")
    if "klips2_change_password" in available_tool_names:
        klips_tools.append("- klips2_change_password: username, password, new_password")
    if "klips2_get_course_details" in available_tool_names:
        klips_tools.append("- klips2_get_course_details: course_id")

    search_tools = []
    if "duckduckgo_search" in available_tool_names:
        search_tools.append("- duckduckgo_search: query (bei \"Search for\", \"Suche im Internet\", \"online\")")
    if "university_knowledge_search" in available_tool_names:
        search_tools.append("- university_knowledge_search: query (bei Uni-Fragen ohne Internet-Keywords)")
    if "web_scraper" in available_tool_names:
        search_tools.append("- web_scraper: url (bei URLs)")

    comm_tools = []
    if "send_email" in available_tool_names:
        comm_tools.append("- send_email: subject, body")

    # Baue Tool-Sektionen zusammen
    tools_section = ""
    if klips_tools:
        tools_section += "\n### KLIPS2-Aktionen:\n" + "\n".join(klips_tools) + "\n"
    if search_tools:
        tools_section += "\n### Suche & Wissen:\n" + "\n".join(search_tools) + "\n"
    if comm_tools:
        tools_section += "\n### Kommunikation:\n" + "\n".join(comm_tools)

    # Dynamic multi-tool examples based on available tools
    multi_tool_examples = []
    if len(available_tool_names) >= 2:
        if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
            multi_tool_examples.append('- "Suche X **und dann** hole Y" → BEIDE Tools aufrufen: [duckduckgo_search, klips2_get_course_details]')
        if "klips2_get_course_details" in available_tool_names and "send_email" in available_tool_names:
            multi_tool_examples.append('- "Hole Kursdetails **und schicke** E-Mail" → BEIDE Tools aufrufen: [klips2_get_course_details, send_email]')
        if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
            multi_tool_examples.append('- "Recherchiere X, **dann** Details zu Y" → BEIDE Tools aufrufen: [duckduckgo_search, klips2_get_course_details]')

    # Build multi-tool section
    multi_tool_section = ""
    if multi_tool_examples:
        multi_tool_section = f"""## MULTI-TOOL-ANFRAGEN (WICHTIG!)

**Wenn der User MEHRERE Aktionen in EINER Nachricht fordert:**
{chr(10).join(multi_tool_examples)}

Signalwörter für Multi-Tool:
- "und dann", "danach", "anschließend", "then"
- "und schicke", "und sende", "and send"
- Mehrere Aktionsverben in einer Anfrage

**REGEL:** Bei Multi-Tool-Anfragen → ALLE relevanten Tools aufrufen!

"""

    return f"""Du bist ein KI-Assistent für KLIPS 2.0, das Campus-Management-System der Universität zu Köln.

## WANN EIN TOOL AUFRUFEN?

✅ Tool aufrufen bei: {tool_categories_text}
❌ KEIN Tool bei: Begrüßungen, Fragen über dich, Rechenaufgaben, allgemeine Fragen

## REGELN

1. Wenn Tool passend UND alle Pflichtdaten vorhanden → Tool aufrufen
2. Wenn Tool passend ABER Daten fehlen → Nachfragen (KEIN Tool-Aufruf)
3. Wenn KEIN Tool passend → Direkt antworten

## TOOLS (Pflichtparameter)
{tools_section}

## MULTI-STEP KONVERSATIONEN

Wenn im Prompt "Previous conversation:" steht:
1. Analysiere ALLE Informationen aus vorherigen Nachrichten
2. Kombiniere sie mit der aktuellen Nachricht
3. Wenn dadurch ALLE Pflichtparameter vorhanden sind → Tool aufrufen

{multi_tool_section}

Antworte in der Sprache des Nutzers."""


def get_decision_prompt(available_tool_names: Set[str]) -> str:
    """Prompt für die Tool-Entscheidung mit expliziten Anforderungen."""
    # Tool-spezifische Pflichtfelder
    tool_requirements = {
        "klips2_register": ["vorname", "nachname", "geschlecht", "geburtsdatum", "email", "staatsangehoerigkeit"],
        "klips2_apply_study": ["username", "password", "semester", "degree_type", "study_program", "study_form", "gender", "birth_place", "nationality", "hzb_date", "hzb_type", "hzb_grade", "hzb_place"],
        "klips2_change_password": ["username", "password", "new_password"],
        "klips2_change_address": ["username", "password", "street", "zip_code", "city"],
        "klips2_get_course_details": ["course_id"],
        "send_email": ["subject", "body"],
        "duckduckgo_search": ["query"],
        "university_knowledge_search": ["query"],
        "web_scraper": ["url"],
    }

    # Nur Tools auflisten, die auch tatsächlich verfügbar sind
    tool_list = []
    for name, schema in TOOL_SCHEMAS.items():
        if name not in available_tool_names:
            continue
        desc = schema.__doc__ or 'Keine Beschreibung'
        required = tool_requirements.get(name, [])
        req_str = ", ".join(required) if required else "keine"
        tool_list.append(f"- {name}: {desc}\n  PFLICHT: {req_str}")

    tools_str = "\n".join(tool_list)

    # Build dynamic tool trigger sections based on available tools
    tool_trigger_sections = []

    if any(name in available_tool_names for name in ("klips2_register", "klips2_apply_study", "klips2_change_password", "klips2_change_address")):
        klips_examples = []
        if "klips2_register" in available_tool_names:
            klips_examples.append('- "Registriere mich" → klips2_register')
        if "klips2_apply_study" in available_tool_names:
            klips_examples.append('- "Bewerbe mich für [Studiengang]" → klips2_apply_study')
        if "klips2_change_password" in available_tool_names:
            klips_examples.append('- "Ändere mein Passwort" → klips2_change_password')
        if "klips2_change_address" in available_tool_names:
            klips_examples.append('- "Ändere meine Adresse" → klips2_change_address')
        tool_trigger_sections.append("**KLIPS2-Aktionen (Tool aufrufen):**\n" + "\n".join(klips_examples))

    if "klips2_get_course_details" in available_tool_names:
        tool_trigger_sections.append('''**KURS-ABFRAGEN (Tool aufrufen):**
- "Mehr über Kurs [X] erfahren" → klips2_get_course_details
- "Wann findet Kurs [X] statt?" → klips2_get_course_details
- "Wer hält Kurs [X]?" → klips2_get_course_details
- "Details zu Kurs [X]" → klips2_get_course_details''')

    # Multi-tool examples (only if we have 2+ tools available)
    if len(available_tool_names) >= 2:
        multi_tool_examples = []
        if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
            multi_tool_examples.append('1. "Suche im Internet nach Kurs X **und** hole dann Details aus KLIPS"\n   → ["duckduckgo_search", "klips2_get_course_details"]')
        if "klips2_get_course_details" in available_tool_names and "send_email" in available_tool_names:
            multi_tool_examples.append('2. "Hole Kursdetails **und** sende E-Mail"\n   → ["klips2_get_course_details", "send_email"]')
        if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
            multi_tool_examples.append('3. "Recherchiere X, **dann** Details zu Kurs Y"\n   → ["duckduckgo_search", "klips2_get_course_details"]')

        if multi_tool_examples:
            tool_trigger_sections.append(f'''**MULTI-TOOL-ANFRAGEN (MEHRERE TOOLS - WICHTIG!):**

PRÜFE ZUERST: Fordert der User MEHRERE Aktionen nacheinander?

Signalwörter für Multi-Tool (= MEHRERE Tools erforderlich):
- "und dann", "danach", "anschließend"
- "and then", "then", "after that"
- Mehrere Verben in EINER Anfrage: "Suche... hole...", "Search... get...", "Schau... schicke..."

BEISPIELE für Multi-Tool (= tool_names muss LISTE mit 2+ Tools sein):
{chr(10).join(multi_tool_examples)}

WICHTIG: 
- Reihenfolge der Tools beachten (chronologisch wie in Anfrage)!''')

    if "university_knowledge_search" in available_tool_names or "duckduckgo_search" in available_tool_names:
        search_rules = []
        if "duckduckgo_search" in available_tool_names:
            search_rules.append('''1. **IMMER duckduckgo_search bei:**
   - Expliziten Such-Keywords: "Search", "Suche", "Such", "Find", "Finde", "Look up" mit Suchbegriff
   - "Search for [X]" → duckduckgo_search
   - "Suche nach [X]" → duckduckgo_search
   - "Google [X]" → duckduckgo_search''')

        if "university_knowledge_search" in available_tool_names:
            search_rules.append('''2. **NUR university_knowledge_search bei:**
   - Direkten Fragen OHNE Such-Keywords:
     * "Wie bewerbe ich mich für Master?" (Frage, kein Such-Keyword)
     * "Welche Fristen gibt es?" (Frage, kein Such-Keyword)
     * "Was kostet das Studium?" (Frage, kein Such-Keyword)''')

        if search_rules:
            tool_trigger_sections.append("**WISSENS-SUCHE (Tool aufrufen):**\n\nWICHTIG - Entscheidungslogik für Suchen:\n\n" + "\n\n".join(search_rules))

    if "send_email" in available_tool_names:
        tool_trigger_sections.append('''**E-MAIL (Tool aufrufen, NUR wenn Betreff UND Inhalt vorhanden):**
- "Sende eine E-Mail" → send_email
- "Schicke eine Mail" → send_email
- "Verfasse eine E-Mail" → send_email
- "Schreibe eine E-Mail" → send_email
- "Sende eine Nachricht" → send_email
- "E-Mail versenden" → send_email
- "send an email" / "send email" → send_email
- "Schicke eine Nachfolge-E-Mail" → send_email

WICHTIG: Nur aufrufen wenn BEIDE Pflichtfelder vorhanden:
  ✓ subject (Betreff - MUSS explizit genannt werden)
  ✓ body (Inhalt - MUSS erkennbarer Nachrichtentext vorhanden sein)
  ✗ NUR Betreff ohne Inhalt → insufficient_data
  ✗ NUR vager Auftrag ohne Betreff → insufficient_data''')

    tool_trigger_text = "\n\n".join(tool_trigger_sections) if tool_trigger_sections else "Keine Tool-spezifischen Trigger definiert."

    # Build completeness rules section dynamically
    completeness_rules = []
    if "klips2_register" in available_tool_names:
        completeness_rules.append("  - klips2_register: Vorname UND Nachname UND Email UND Geburtsdatum UND Geschlecht UND Staatsangehörigkeit")
    if "klips2_apply_study" in available_tool_names:
        completeness_rules.append("  - klips2_apply_study: username UND password UND semester UND degree_type UND study_program UND study_form (Erststudium/Zweitstudium) UND gender UND birth_place UND nationality UND hzb_date UND hzb_type UND hzb_grade UND hzb_place")
        completeness_rules.append("  - Wenn study_form='Zweitstudium': ZUSÄTZLICH prev_uni UND prev_program UND prev_semesters erforderlich")
    if "send_email" in available_tool_names:
        completeness_rules.append("  - send_email: subject UND body (beide Felder müssen im Text vorhanden sein)")
    completeness_text = "\n".join(completeness_rules) if completeness_rules else "  (Keine tool-spezifischen Regeln)"

    # JSON example only if both tools are available
    if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
        json_example = '\nBeispiel: "Suche X und hole dann Y" → {{"action": "tool", "tool_names": ["duckduckgo_search", "klips2_get_course_details"], "reason": "Multi-Tool: Suche + KLIPS"}}'
    else:
        json_example = ""

    return f"""Du bist ein KI-Assistent für KLIPS 2.0 der Universität zu Köln.

Analysiere die Nutzeranfrage und entscheide:
1. Welches Tool benötigt wird (oder keins)
2. Ob die wichtigsten Pflichtfelder vorhanden sind

VERFÜGBARE TOOLS mit Pflichtfeldern:
{tools_str}

ENTSCHEIDUNGSLOGIK:

## 1. TOOL-TRIGGER: Wann welches Tool aufrufen?

{tool_trigger_text}

**KEINE TOOLS (respond):**
- Begrüßungen: "Hallo!", "Wie geht's?", "Guten Tag", "Hi"
- System-Fragen: "Was kannst du?", "Welche Funktionen hast du?", "Hilfe"
- Einfache Berechnungen: "Was ist 2+2?", "Rechne 10 * 5"
- Übersetzungen: "Übersetze X nach Y", "Was heißt X auf Englisch?"
- Allgemeine Wissensfragen ohne Uni-Bezug: "Was ist ein Bachelor?" (generisch, nicht Uni-spezifisch)
- Small Talk: "Wie ist das Wetter?", "Erzähl einen Witz"


## 2. PFLICHTFELD-PRÜFUNG (STRENG!)

PRÜFREGEL: Gehe Pflichtfeld für Pflichtfeld durch und notiere:
  ✓ "vorname: [Wert aus Text]"
  ✓ "nachname: [Wert aus Text]"  
  ✓ "email: [Wert aus Text]"
  ... etc.

Wenn Tool identifiziert:
- Prüfe JEDES EINZELNE Pflichtfeld für das gewählte Tool
- Ist das Feld EXPLIZIT im Text genannt? (Nicht raten/ableiten!)
- Sind die Werte konkret und vollständig?

**KRITISCHE REGELN:**

NAMES/IDENTITÄT (STRENGSTE PRÜFUNG!):
  ✗ "Login: kim@uni-koeln.de" → KEINE NAMEN! → insufficient_data (fehlen: vorname, nachname)
  ✗ "Divers, 01.01.2000, Berlin" → KEINE NAMEN! → insufficient_data (fehlen: vorname, nachname)
  ✗ "Name: Thomas Klein" → UNKLAR ob Vor-/Nachname → insufficient_data (fehlt Trennung)
  ✓ "Ich heiße Peter Bauer" → OK: "Peter" = vorname, "Bauer" = nachname
  ✓ "Vorname: Lisa, Nachname: Müller" → OK: Explizit getrennt
  
  REGEL: Vorname UND Nachname müssen BEIDE EXPLIZIT identifizierbar sein!

KLIPS-LOGIN (username/password):
  ✗ "Bewerbung Informatik Bachelor" → KEINE Zugangsdaten! → insufficient_data (fehlen: username, password)
  ✗ "Erststudium, 1. Semester" → KEINE Zugangsdaten! → insufficient_data (fehlen: username, password)
  ✓ "Login: max@uni-koeln.de / pass123" → OK: username + password vorhanden

PERSÖNLICHE DATEN (gender, birth_place, nationality):
  ✗ "Bewerbung Informatik Bachelor" → NICHTS über Person! → insufficient_data (fehlen: gender, birth_place, nationality)
  ✓ "männlich, geboren 15.03.1999 in Köln" → OK: gender + birth_place vorhanden
  ✓ "Staatsangehörigkeit: deutsch" → OK: nationality vorhanden

HZB-DATEN (hzb_date, hzb_type, hzb_grade, hzb_place):
  ✗ "Abitur 2,3 vom 01.06.2018" → hzb_place fehlt! → insufficient_data (fehlt: hzb_place)
  ✓ "Abitur 2,3 vom 01.06.2018, Gymnasium Bonn, Bonn" → OK: alle HZB-Pflichtfelder vorhanden
  
  HINWEIS: hzb_name (Zeugnis-Bezeichnung) und hzb_school (Schulname) sind OPTIONAL mit Standardwerten.

EMAIL (nur für klips2_register - die Registrierungs-E-Mail-Adresse des Nutzers):
  - MUSS @ enthalten: "max@test.de" ✓
  - Fake-Emails ABLEHNEN: "noemail@nodomain.com", "keine-email@test.de" ✗
  - Phrase "E-Mail: wird nachgereicht" → insufficient_data
  HINWEIS: Diese Regel gilt NUR für den klips2_register-Parameter 'email', NICHT für send_email!

DATUM:
  - "Geburtsdatum: 15.03.1999" ✓
  - "Geboren 1999" → insufficient_data (nur Jahr)
  - "Geburtsdatum: TBA" / "noch unklar" → insufficient_data

VOLLSTÄNDIGKEIT:
{completeness_text}
  - Fehlt EIN EINZIGES Pflichtfeld → action='insufficient_data'
  - Platzhalter wie "TBD", "N/A", "wird ergänzt" → insufficient_data

**WENN Pflichtfelder fehlen:** action='insufficient_data' mit missing_fields
**WENN ALLE Pflichtfelder vorhanden:** action='tool'

WICHTIG: Lieber EINMAL ZU VIEL nachfragen als mit unvollständigen Daten Tool aufrufen!

## 3. FORMAT-TOLERANZ (WICHTIG):

✓ ACCEPT verschiedene Formate:
  - Datum: "15.03.1995", "1995-03-15", "March 15, 1995" (alle gültig)
  - Geschlecht: "m", "w", "d", "männlich", "male", "female", "divers" (alle gültig)
  - Email: Jede Email mit @ ist gültig (auch nicht-deutsche Domains)
  - Namen: Auch englische/internationale Namen akzeptieren
  - Sprache: Deutsch UND Englisch akzeptieren

✗ REJECT nur offensichtliche Probleme:
  - Email OHNE @: "email max.mustermann"
  - Fake-Emails: "keine-echte-email@example.com", "noemail@nodomain.com"
  - Partielles Datum: "1995" (nur Jahr), "15.03" (ohne Jahr)
  - Ungültiges Datum: "32.13.2020", "99.99.9999"
  - Fehlende Stadt bei Adresse: "Hauptstraße 1, PLZ 12345" (Stadt fehlt)
  - Vage Suche: "irgendwelche Kurse", "könnte ich Infos zu..."

## 4. SPEZIALFALL: Multi-Step-Konversationen (KRITISCH!)

**WICHTIG: Wenn "Previous conversation:" vorhanden ist:**

SCHRITT 1 - DATEN SAMMELN:
  - Lies ALLE vorherigen User-Nachrichten komplett durch
  - Sammle JEDES erwähnte Datenfeld (auch aus mehreren Nachrichten!)
  - Notiere dir: "In vorherigen Nachrichten habe ich: [Liste]"
  
SCHRITT 2 - AKTUELLE NACHRICHT:
  - Lies die aktuelle User-Nachricht
  - Notiere: "In aktueller Nachricht habe ich zusätzlich: [Liste]"
  
SCHRITT 3 - KOMBINIERE:
  - Vereinige ALLE Daten (vorherige + aktuelle)
  - Prüfe: Sind JETZT alle Pflichtfelder vorhanden?
  - JA → action='tool' | NEIN → action='insufficient_data'

TYPISCHE MULTI-STEP-MUSTER:
  ✓ "Zugangsdaten nachliefern": User gibt initial Studiengang/Daten, später Username/Password → DANN tool aufrufen!
  ✓ "Fehlende HZB": User gibt initial Persönliches, später Abitur-Daten → DANN tool aufrufen!
  ✓ "Korrekturen": User sagt "sorry, ich meinte X statt Y" → Nutze korrigierten Wert und tool aufrufen!
  
  ✗ "Abbruch": User sagt "doch nicht" / "abbrechen" → action='respond'
  ✗ "Immer noch unvollständig": Auch nach Nachfrage fehlen Pflichtfelder → action='insufficient_data'

Antworte im JSON-Format:

**EIN TOOL:**
{{"action": "tool", "tool_names": ["<name1>"], "reason": "Ein Tool identifiziert"}}

**MEHRERE TOOLS (Multi-Tool bei "und dann", "und schicke", etc.):**
{{"action": "tool", "tool_names": ["<name1>", "<name2>"], "reason": "Mehrere Tools identifiziert"}}
{json_example}

**FEHLENDE DATEN:**
{{"action": "insufficient_data", "tool_names": ["<name>"], "reason": "Pflichtfelder fehlen", "missing_fields": ["feld1", "feld2"]}}

**KEINE TOOLS:**
{{"action": "respond", "reason": "Nur Frage/Information, keine Aktion gewünscht"}}"""


def get_extraction_prompt(tool_name: str, schema: Type[BaseModel]) -> str:
    """Prompt für die Argument-Extraktion eines bestimmten Tools."""
    # Hole Feld-Beschreibungen aus dem Schema
    fields = []
    for name, field in schema.model_fields.items():
        required = field.is_required()
        desc = field.description or ""
        req_str = "PFLICHT" if required else "optional"
        fields.append(f'  "{name}": "<{desc}>" // {req_str}')

    fields_str = ",\n".join(fields)

    # Tool-spezifische Normalisierungshinweise
    tool_hints = ""
    if tool_name == "klips2_apply_study":
        tool_hints = """
HZB-NORMALISIERUNG:
  * "Abitur" → hzb_type="Allgemeine Hochschulreife", hzb_name="Abitur"
  * "A-Levels" → hzb_type="Allgemeine Hochschulreife", hzb_name="A-Levels"
  * "Fachhochschulreife" / "FHR" → hzb_type="Fachhochschulreife"
  * "Fachgebundene Hochschulreife" → hzb_type="Fachgebundene Hochschulreife"
  * "High School Diploma" → hzb_type="Ausländische Hochschulzugangsberechtigung"

SEMESTER-NORMALISIERUNG:
  * "WS 2024/25" / "WS24/25" / "Wintersemester 2024" → "Wintersemester 2024/25"
  * "SS 2025" / "SoSe 2025" / "Sommersemester 25" → "Sommersemester 2025"

HZB-ORT: "Gymnasium Köln" → hzb_school="Gymnasium Köln", hzb_place="Köln" (Stadt aus Schulname ableiten wenn kein separater Ort genannt)
"""

    return f"""Extrahiere die Parameter für {tool_name} aus dem Nutzertext.

WICHTIGE REGELN:
- Extrahiere NUR Daten die im Text stehen (aktuell ODER in "Previous conversation:")
- Bei "Previous conversation:": Lies ALLE vorherigen Nachrichten und sammle Daten
- Bei Korrekturen ("sorry, ich meinte X statt Y"): Nutze korrigierte Werte
- NIEMALS Daten erfinden oder raten
- Nutze EXAKT diese Feldnamen (keine Variationen!)
- Preserve all characters exactly as they appear in the user message, including umlauts: ä ö ü Ä Ö Ü ß
- Normalisiere Formate flexibel:
  * Datum: "15.03.1995", "1995-03-15", "March 15, 1995" → "15.03.1995"
  * Geschlecht: "m"→"männlich", "w"→"weiblich", "d"→"divers", "male"→"männlich", etc.
  * Email: lowercase, beliebige Domains OK (auch .edu, .org, etc.)
  * Namen: Capitalize first letter, auch internationale Namen
{tool_hints}
FORMAT-TOLERANZ:
- Akzeptiere verschiedene Datumsformate (DD.MM.YYYY, YYYY-MM-DD, Month DD, YYYY)
- Akzeptiere Abkürzungen (m/w/d, DE/USA, etc.)
- Akzeptiere englische Texte
- Konvertiere automatisch zu erwarteten Formaten

Ausgabeformat (JSON):
{{
{fields_str}
}}

Lasse optionale Felder weg wenn nicht vorhanden.
PFLICHT-Felder sollten vorhanden sein (wurden bereits validiert)."""
