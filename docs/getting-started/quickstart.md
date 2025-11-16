# Quick Start

## Chatbot starten

```bash
streamlit run src/ui/streamlit_app.py
```

Öffnet automatisch http://localhost:8501

## Erste Fragen

Probiere diese Beispiele:

- "Welche Master-Programme gibt es?"
- "Wie bewerbe ich mich?"
- "Wo finde ich IT-Support?"
- "Registriere mich für KLIPS2"

## CLI-Modus

```bash
python src/dev/main.py
```

## Mit Docker

```bash
# Starten
docker-compose up -d

# Logs
docker-compose logs -f

# Stoppen
docker-compose down
```

## Daten aktualisieren

```bash
# WiSo-Website neu scrapen
python src/scraper/pipelines/scraper_main.py
```

## Tests ausführen

```bash
make test
# oder
pytest tests/
```
