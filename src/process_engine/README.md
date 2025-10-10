# CAMUNDA Process Engine Integration

Diese Implementierung bietet eine lokale CAMUNDA Process Engine für die Streamlit-App mit automatischen Bewerbungsprozessen.

## Features

### 🔄 Lokale Process Engine
- **Mock Zeebe Engine**: Läuft vollständig lokal ohne externe Abhängigkeiten
- **SQLite Persistence**: Alle Prozessinstanzen werden in einer lokalen Datenbank gespeichert
- **Automatischer Start**: Engine startet automatisch beim Laden der Streamlit-App
- **BPMN-Standard**: Kompatibel mit CAMUNDA BPMN 2.0

### 📋 Bewerbungsprozess
Der implementierte "Bewerbung" Prozess umfasst:

1. **Start Event**: 
   - Parameter: `student_name` (Name des Studierenden)
   - Parameter: `studiengang` (Bezeichnung des Studiengangs)

2. **User Task "Angaben prüfen"**:
   - Erfordert: `student_email` (E-Mail des Studenten)
   - Status: Wartet auf manuelle Bearbeitung

3. **End Event**: 
   - Prozess wird als COMPLETED markiert

## Architektur

```
src/process_engine/
├── __init__.py                 # Package Init
├── camunda_engine.py          # Haupt-Engine Implementation
└── streamlit_interface.py     # Streamlit UI Components

src/tools/
└── process_engine_tool.py     # LangChain Tools für Agent-Integration
```

### Hauptkomponenten

#### 1. MockZeebeEngine (`camunda_engine.py`)
- Lokale Implementation einer Zeebe-kompatiblen Engine
- SQLite-basierte Persistence
- BPMN-Prozess-Management
- Process Instance Lifecycle

#### 2. CamundaEngine (`camunda_engine.py`)
- Wrapper für Mock/Real Zeebe Engine
- Engine Management (Start/Stop)
- Prozess-Deployment
- Instance-Management

#### 3. Streamlit Interface (`streamlit_interface.py`)
- Web-Interface für Process Management
- Prozess-Übersicht und -Kontrolle
- Formulare für neue Prozesse
- Task-Bearbeitung

#### 4. LangChain Tools (`process_engine_tool.py`)
- `ProcessEngineStartTool`: Startet neue Bewerbungsprozesse
- `ProcessEngineCompleteTool`: Schließt Tasks ab
- `ProcessEngineStatusTool`: Zeigt Engine-Status
- `ProcessEngineInstanceTool`: Holt Instance-Details

## Verwendung

### 1. Über Streamlit Interface

**Process Engine Tab:**
- Engine-Status und -Kontrolle
- Neue Bewerbungsprozesse starten
- Aktive Prozesse verwalten
- Übersicht aller Prozesse mit Filteroptionen

**Beispiel neuer Prozess:**
1. Gehe zum "Process Engine" Tab
2. Fülle Formular aus:
   - Name: "Max Mustermann"
   - Studiengang: "Informatik Master"
3. Klicke "Bewerbungsprozess starten"
4. Notiere die Process Instance ID
5. Unter "Aktive Prozesse" E-Mail hinzufügen
6. Klicke "Angaben geprüft" zum Abschließen

### 2. Über Chatbot Agent

Der Agent kann Bewerbungsprozesse automatisch verwalten:

```
User: "Ich möchte mich für den Informatik Master bewerben. Mein Name ist Max Mustermann."
Agent: [Startet automatisch Bewerbungsprozess mit start_bewerbung_process]

User: "Meine E-Mail ist max.mustermann@uni-koeln.de"
Agent: [Schließt Angaben-Prüfung ab mit complete_angaben_pruefen]
```

**Verfügbare Agent-Commands:**
- `start_bewerbung_process(student_name, studiengang)`
- `complete_angaben_pruefen(instance_id, student_email)`
- `process_engine_status()` 
- `get_process_instance(instance_id)`

### 3. Programmatische Verwendung

```python
from src.process_engine.camunda_engine import start_engine

# Engine starten
engine = start_engine()

# Neuen Prozess starten
instance_id = engine.start_bewerbung_process("Max Mustermann", "Informatik Master")

# Task abschließen
engine.complete_angaben_pruefen(instance_id, "max.mustermann@uni-koeln.de")

# Status prüfen
status = engine.get_status()
print(f"Aktive Prozesse: {status['active_instances']}")
```

## Datenbank

Die Engine verwendet SQLite für Persistence:

### Tabellen

**process_instances:**
- `id`: Primary Key
- `process_key`: Prozess-Typ (z.B. "bewerbung")
- `status`: ACTIVE | COMPLETED
- `variables`: JSON mit Prozess-Variablen
- `current_task`: Aktueller Task oder NULL
- `created_at`, `updated_at`: Timestamps

**task_instances:**
- `id`: Primary Key
- `process_instance_id`: Foreign Key
- `task_name`: Name des Tasks
- `status`: COMPLETED
- `variables`: JSON mit Task-Variablen
- `created_at`, `completed_at`: Timestamps

### Datei-Location
- Standard: `process_instances.db` im Projektroot
- Konfigurierbar über MockZeebeEngine Parameter

## Erweiterung

### Neue Prozesse hinzufügen

1. **BPMN definieren** in `CamundaEngine._create_new_bpmn()`
2. **Deployment** in `CamundaEngine._start_mock_engine()`
3. **Business Logic** als neue Engine-Methoden
4. **Tools erstellen** in `process_engine_tool.py`
5. **UI erweitern** in `streamlit_interface.py`

### Echte Zeebe Engine

Für Produktivumgebung kann die echte Zeebe Engine verwendet werden:

1. Installiere `pyzeebe>=3.0.0`
2. Setze `use_mock=False` in `CamundaEngine`
3. Implementiere `_start_zeebe_engine()` Methode
4. Starte Zeebe Server extern

## Logging

Die Engine nutzt Python Logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

**Log-Events:**
- Engine Start/Stop
- Prozess-Deployment
- Instance-Lifecycle
- Task-Completion
- Fehler und Exceptions

## Konfiguration

### Engine-Settings
```python
# In camunda_engine.py anpassbar
MOCK_DB_PATH = "process_instances.db"
DEFAULT_PROCESS_KEY = "bewerbung"
```

### Streamlit-Integration
```python
# Automatischer Start in initialize_session_state()
start_engine()  # Startet Engine beim App-Start
```

## Monitoring

### Verfügbare Metriken
- Anzahl aktiver Prozesse
- Anzahl abgeschlossener Prozesse
- Engine-Status (Running/Stopped)
- Prozess-Details und Historie

### Streamlit Dashboard
- Echtzeit-Status in Sidebar
- Detaillierte Übersicht im Process Engine Tab
- Export-Funktionen für Berichte
- Filter- und Suchfunktionen

## Troubleshooting

### Häufige Probleme

**Engine startet nicht:**
- Prüfe Dateiberechtigungen für SQLite
- Kontrolliere Python-Dependencies
- Siehe Logs für Details

**Prozesse werden nicht gespeichert:**
- Prüfe SQLite-Datei Schreibrechte
- Kontrolliere Datenbankverbindung
- Prüfe JSON-Serialisierung der Variables

**Tools nicht verfügbar:**
- Kontrolliere Import-Pfade
- Prüfe Agent-Konfiguration
- Siehe Console-Output beim Start

### Debug-Modus

```python
import logging
logging.getLogger('src.process_engine').setLevel(logging.DEBUG)
```

## Sicherheit

### Lokale Entwicklung
- Keine externen Netzwerkverbindungen
- SQLite-Datei nur lokal zugänglich
- Keine Authentifizierung implementiert

### Produktive Nutzung
Für produktive Umgebungen sollten implementiert werden:
- Benutzer-Authentifizierung
- Autorisierung für Prozess-Actions
- Sichere Datenbankverbindung
- HTTPS für Streamlit
- Input-Validierung und Sanitization