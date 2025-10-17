# LangSmith-Tracing Setup 🔍

## Übersicht

LangSmith-Tracing ermöglicht es, alle Agent-Interaktionen, Tool-Calls und LLM-Kommunikationen automatisch zu verfolgen und zu analysieren.

## Setup

### 1. LangSmith Account erstellen
1. Gehe zu [LangSmith](https://smith.langchain.com/)
2. Erstelle einen Account oder melde dich an
3. Erstelle ein neues Projekt oder verwende ein vorhandenes

### 2. API-Key erhalten
1. Gehe zu Settings > API Keys
2. Erstelle einen neuen API-Key
3. Kopiere den API-Key

### 3. Konfiguration

#### Option A: .env-Datei (Empfohlen)
Füge folgende Zeilen zu deiner `.env`-Datei hinzu:

```bash
# LangSmith Tracing
LANGSMITH_API_KEY=your_actual_api_key_here
LANGSMITH_PROJECT=uzk-masterarbeit
LANGSMITH_TRACING=true
```

#### Option B: Umgebungsvariablen
```bash
export LANGSMITH_API_KEY="your_actual_api_key_here"
export LANGSMITH_PROJECT="your_actual_project_here"  
export LANGSMITH_TRACING="true"
```

## Verwendung

### Tracing aktivieren
```bash
# In .env setzen:
LANGSMITH_TRACING=true
```

### Tracing deaktivieren
```bash
# In .env setzen:
LANGSMITH_TRACING=false
```

## Was wird getrackt?

### 🤖 **Automatisch erfasst:**
- **Agent-Runs**: Komplette Reasoning-Zyklen
- **Tool-Calls**: Alle Tool-Aufrufe mit Ein-/Ausgaben
- **LLM-Interactions**: Ollama-Kommunikation
- **Performance-Metriken**: Latenz aller Komponenten
- **Fehler**: Automatische Fehlererfassung

### 📊 **Session-Tracking:**
- **Session-IDs**: Zusammenhängende Gespräche
- **User-Messages**: Eingaben (gekürzt für Privacy)
- **Tool-Usage**: Welche Tools verwendet werden

## LangSmith Dashboard

Nach der Aktivierung findest du in deinem LangSmith Dashboard:

### 📈 **Analytics**
- Tool-Usage-Statistiken
- Performance-Trends
- Fehlerrate-Monitoring

### 🔍 **Traces** 
- Detaillierte Execution-Traces
- Tool-Call-Hierarchien
- Timing-Informationen

### 🐛 **Debugging**
- Fehlgeschlagene Tool-Calls
- LLM-Reasoning-Prozesse
- Input/Output-Inspection

## Streamlit-Integration

Das Streamlit-Interface zeigt den LangSmith-Status automatisch an:

- ✅ **Aktiv**: LangSmith-Tracing läuft
- ❌ **Inaktiv**: Kein Tracing
- **Session-ID**: Eindeutige Session-Kennung (gekürzt)

## Privacy & Sicherheit

### 🔒 **Gesendete Daten:**
- User-Messages (erste 100 Zeichen)
- Tool-Calls und Responses
- Agent-Reasoning
- Performance-Metriken

### 🚫 **NICHT gesendet:**
- Vollständige sensitive Nachrichten
- API-Keys anderer Services
- Lokale Dateipfade

### 🛡️ **Sicherheitsmaßnahmen:**
- API-Key wird sicher übertragen
- Daten werden in LangSmith verschlüsselt gespeichert
- Nur autorisierte Team-Mitglieder haben Zugang

## Troubleshooting

### Problem: "LangSmith-Tracing nicht aktiv"
```bash
# Prüfe .env-Konfiguration:
cat .env | grep LANGSMITH

# Stelle sicher, dass alle Variablen gesetzt sind:
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=...
LANGSMITH_TRACING=true
```

### Problem: "API-Key ungültig"
1. Prüfe API-Key in LangSmith Dashboard
2. Erstelle neuen API-Key falls nötig
3. Aktualisiere .env-Datei

### Problem: "Traces erscheinen nicht"
1. Warte 1-2 Minuten (kann etwas dauern)
2. Aktualisiere LangSmith Dashboard
3. Prüfe Projekt-Name in LangSmith

## Kosten

LangSmith bietet:
- **Free Tier**: Begrenzte Traces pro Monat
- **Pro Tier**: Unbegrenzte Traces + erweiterte Features

Siehe [LangSmith Pricing](https://www.langchain.com/pricing) für Details.

## Beispiel-Workflow

1. **Setup**: API-Key in .env konfigurieren
2. **Aktivieren**: `LANGSMITH_TRACING=true` setzen
3. **Testen**: Agent-Chat starten
4. **Monitoring**: LangSmith Dashboard öffnen
5. **Analysieren**: Traces und Performance prüfen

## Deaktivierung

Um LangSmith komplett zu deaktivieren:

```bash
# In .env:
LANGSMITH_TRACING=false

# Oder Zeile auskommentieren:
# LANGSMITH_TRACING=true
```

Der Agent funktioniert normal weiter, sendet aber keine Daten an LangSmith.