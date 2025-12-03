# KLIPS2 Integration

Der Chatbot verfügt über eine tiefe Integration in das Campus-Management-System **KLIPS2** der Universität zu Köln. Dies ermöglicht es dem Agenten, komplexe administrative Aufgaben im Auftrag des Benutzers durchzuführen.

## 🔐 Voraussetzungen

Für die meisten KLIPS-Funktionen (außer der Registrierung eines Basis-Accounts) sind gültige Zugangsdaten erforderlich.

Diese können entweder:
1. In der `.env` Datei konfiguriert werden (für Entwicklungszwecke):
   ```bash
   KLIPS_USERNAME=s_mustermann
   KLIPS_PASSWORD=geheim
   ```
2. Oder vom Agenten während des Gesprächs abgefragt werden (empfohlen für den produktiven Einsatz).

## 🛠️ Verfügbare Tools

### 1. Studienbewerbung (`klips2_apply_study`)
Automatisierter Assistent für den Bewerbungsprozess. Der Agent navigiert durch den komplexen Bewerbungs-Wizard.

**Funktionen:**
- Auswahl von Semester, Abschlussart und Studiengang
- Automatische Erkennung dynamischer Felder (z.B. Einstiegssemester, Studienform)
- Ausfüllen von Personendaten und Adressen (falls nicht vorausgefüllt)
- Unterstützung für Hochschulzugangsberechtigung (HZB) und Vorbildung

**Parameter:**
- `semester`: z.B. "Wintersemester 2024/25"
- `degree_type`: z.B. "Bachelor"
- `study_program`: z.B. "Rechtswissenschaften"
- `entry_semester`: Fachsemester (Standard: 1)
- `study_form`: z.B. "Zweitstudium"
- *Optionale Felder für HZB, Adresse, etc.*

### 2. Account-Registrierung (`klips2_register`)
Erstellt einen Basis-Account für Studieninteressierte ohne bestehenden Uni-Account.

**Ablauf:**
- Navigiert zur öffentlichen Registrierungsseite
- Füllt das Formular mit den bereitgestellten Daten aus
- Bestätigt die Eingaben

### 3. Adressänderung (`klips2_change_address`)
Aktualisiert die im Profil hinterlegten Adressdaten.

**Unterstützte Felder:**
- Straße & Hausnummer
- Postleitzahl & Ort
- Land
- Telefonnummer

### 4. Kurs-Details (`klips2_get_course_details`)
Ruft detaillierte Informationen zu einer spezifischen Lehrveranstaltung ab.

**Parameter:**
- `course_id`: Die eindeutige LV-Nummer (z.B. "14335.0001")

### 5. Account-Aktivierung (`klips2_activate_account`)
Aktiviert einen neu erstellten Account mittels des per E-Mail erhaltenen Aktivierungscodes.

### 6. Passwort-Änderung (`klips2_change_password`)
Ermöglicht das Ändern des KLIPS2-Passworts.

## ⚙️ Technische Umsetzung

Die Integration basiert auf **Playwright** für die Browser-Automatisierung.

- **Session Management**: Die `KLIPSBrowserSession` Klasse verwaltet Login-Cookies und Browser-Kontexte effizient.
- **Resilienz**: Die Tools implementieren "Fuzzy Matching" für Dropdowns, um auch bei leichten Abweichungen in der Bezeichnung (z.B. "Wintersemester 2024" vs "Wintersemester 2024/25") robust zu funktionieren.
- **Sicherheit**: Passwörter werden nicht geloggt und nur zur Laufzeit im Speicher gehalten.
