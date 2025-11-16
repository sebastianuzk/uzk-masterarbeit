# Docker Deployment

## Lokale Entwicklung

```bash
# Starten
docker-compose up -d

# Logs anzeigen
docker-compose logs -f chatbot

# Stoppen
docker-compose down
```

### Services

- **Chatbot**: Port 8501
- **Ollama**: Port 11434

## Production Deployment

```bash
# Production Compose
docker-compose -f docker-compose.prod.yml up -d

# Mit Script
./scripts/deployment/deploy-prod.sh
```

### Production Features

- Automatische Restarts
- Optimierte Resources
- Named Volumes
- Health Checks

## Volumes

```bash
# Daten-Backup
docker run --rm -v wiso-chatbot_data:/data \
  -v $(pwd):/backup ubuntu \
  tar czf /backup/backup.tar.gz /data
```

## Troubleshooting

```bash
# Container-Status
docker-compose ps

# Logs
docker-compose logs --tail=100 -f

# Rebuild
docker-compose build --no-cache

# Cleanup
docker-compose down -v
```
