# 🚀 CI/CD Setup - Quick Reference

## Deployment-Übersicht

✅ **Main Branch** → Production (Port 8501)  
✅ **Alle feat/* Branches** → Eigene Feature-Umgebung (Ports 8500-8600)

## 📦 Dateien

```
.github/workflows/deploy.yml    # GitHub Actions Workflow
Dockerfile                      # Container Definition
docker-compose.yml              # Standard Compose
docker-compose.prod.yml         # Production Setup
deploy-prod.sh                  # Production Deployment
deploy-feature.sh              # Feature Branch Deployment
cleanup-feature.sh             # Cleanup Script
list-deployments.sh            # Liste aktiver Deployments
.env.production.example        # Environment Beispiel
DEPLOYMENT.md                  # Vollständige Dokumentation
```

## 🎯 Schnellstart

### Lokales Feature-Branch Deployment:
```bash
./deploy-feature.sh
# oder für spezifischen Branch
./deploy-feature.sh feat/my-feature
```

### Production Deployment:
```bash
./deploy-prod.sh
```

### Deployments anzeigen:
```bash
./list-deployments.sh
```

### Cleanup:
```bash
./cleanup-feature.sh feat/my-feature
```

## 🔄 Automatisches Deployment

1. **Code pushen:**
   ```bash
   git push origin feat/my-feature
   ```

2. **GitHub Actions:**
   - Baut Docker Image
   - Deployed zu Feature-Umgebung
   - Kommentiert in PR mit URL

3. **Nach Merge/Delete:**
   - Automatisches Cleanup
   - Resources freigegeben

## 📊 Wichtige Befehle

```bash
# Logs anzeigen
docker logs -f wiso-chatbot-feat-my-feature

# Container stoppen
docker stop wiso-chatbot-feat-my-feature

# Alle Feature-Deployments
docker ps --filter "label=deployment=feature"

# Cleanup alter Volumes
docker volume prune
```

## 📚 Weitere Informationen

Siehe [DEPLOYMENT.md](DEPLOYMENT.md) für detaillierte Dokumentation.
