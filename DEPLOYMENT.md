# CI/CD Deployment Guide

## 🚀 Deployment Setup

Diese Anleitung erklärt, wie Sie den WiSo Chatbot mit automatischem Deployment für **main** und **alle Feature-Branches** deployen können.

## 📋 Deployment-Strategie

### **Automatische Deployments für:**
1. ✅ **main Branch** → Production (Port 8501)
2. ✅ **Alle feat/* Branches** → Eigene Feature-Umgebung (dynamische Ports)

Jeder Feature-Branch erhält automatisch:
- Eigenen Docker-Container
- Eigenen Port (8500-8600 Range)
- Eigene Datenbank
- Eigene Ollama-Instanz
- Automatisches Cleanup bei Branch-Löschung

## 📋 Voraussetzungen

- Docker und Docker Compose installiert
- Git Repository auf GitHub
- (Optional) Server mit Docker für Production/Staging

## 🔧 Setup

### 1. Scripts ausführbar machen

```bash
chmod +x deploy-prod.sh deploy-feature.sh cleanup-feature.sh list-deployments.sh
```

### 2. Environment Files erstellen

```bash
cp .env.production.example .env.production
```

Bearbeiten Sie die Datei mit Ihren spezifischen Einstellungen.

## 🌐 Deployment-Strategien

### **Production Deployment (main Branch)**

```bash
# Mit Deployment Script
./deploy-prod.sh

# Oder manuell
docker-compose -f docker-compose.prod.yml up -d

# Zugriff auf: http://localhost:8501
```

### **Feature Branch Deployment (automatisch)**

Jeder `feat/*` Branch kann individuell deployed werden:

```bash
# Aktuellen Branch deployen
./deploy-feature.sh

# Spezifischen Branch deployen
./deploy-feature.sh feat/deploy_mas-64

# Branch wird automatisch:
# - Eigener Container: wiso-chatbot-feat-deploy-mas-64
# - Eigener Port: z.B. 8523 (automatisch berechnet)
# - Eigene Datenbank und Ollama-Instanz
```

### **Lokales Development**

```bash
# Standard Docker Compose
docker-compose up -d

# Zugriff auf: http://localhost:8501
```

## 📊 Deployment-Übersicht

### Alle aktiven Deployments anzeigen:

```bash
./list-deployments.sh
```

Ausgabe:
```
📋 Active Feature Branch Deployments
================================================

Branch: feat-deploy-mas-64
  Status: 🟢 Running
  Container: wiso-chatbot-feat-deploy-mas-64
  URL: http://localhost:8523
  Compose: docker-compose.feat-deploy-mas-64.yml

Branch: feat-webscraping-mas-55
  Status: 🟢 Running
  Container: wiso-chatbot-feat-webscraping-mas-55
  URL: http://localhost:8534
  Compose: docker-compose.feat-webscraping-mas-55.yml
```

### Feature Branch Cleanup:

```bash
# Cleanup für spezifischen Branch
./cleanup-feature.sh feat/deploy_mas-64

# Cleanup für aktuellen Branch
./cleanup-feature.sh
```

## 🔄 GitHub Actions Workflow

Die CI/CD Pipeline wird automatisch ausgelöst bei:

- **Push zu main** → Build + Deploy zu Production
- **Push zu feat/** → Build + Deploy zu eigener Feature-Umgebung
- **Branch-Löschung** → Automatisches Cleanup der Feature-Umgebung
- **Pull Requests** → Tests ausführen

### Workflow-Schritte:

1. **Test** - Python Tests ausführen
2. **Build** - Docker Image bauen und zu GHCR pushen
3. **Deploy Main** - Production Deployment (nur main)
4. **Deploy Feature** - Feature-Branch Deployment (alle feat/*)
5. **Cleanup** - Entfernt Deployment bei Branch-Löschung

### Automatische Features:

- ✅ Eindeutige Ports für jeden Feature-Branch
- ✅ PR-Kommentare mit Deployment-URLs
- ✅ Automatisches Cleanup bei Merge/Delete
- ✅ Parallele Deployments möglich
- ✅ Isolierte Umgebungen pro Branch

## 🐳 Docker Images

Images werden automatisch zu GitHub Container Registry gepusht:

```
ghcr.io/sebastianuzk/uzk-masterarbeit/chatbot:main
ghcr.io/sebastianuzk/uzk-masterarbeit/chatbot:feat-deploy_mas-64
```

## 📦 Manuelle Docker Commands

### Image bauen:
```bash
docker build -t wiso-chatbot .
```

### Container starten:
```bash
docker run -p 8501:8501 wiso-chatbot
```

### Logs anzeigen:
```bash
docker-compose logs -f chatbot
```

### Container stoppen:
```bash
docker-compose down
```

## 🔍 Monitoring

### Health Check:
```bash
curl http://localhost:8501/_stcore/health
```

### Logs anzeigen:
```bash
# Production
docker-compose -f docker-compose.prod.yml logs -f

# Staging
docker-compose -f docker-compose.staging.yml logs -f
```

## 🌍 Cloud Deployment Optionen

### **Option 1: DigitalOcean App Platform**
1. Verbinden Sie Ihr GitHub Repository
2. App Platform erkennt automatisch das Dockerfile
3. Konfigurieren Sie Environment Variables
4. Deployment erfolgt automatisch bei Git Push

### **Option 2: AWS ECS / Azure Container Instances**
1. Pushen Sie Images zu GHCR oder ECR
2. Erstellen Sie Task Definition / Container Group
3. Konfigurieren Sie Load Balancer
4. Automatisches Deployment via GitHub Actions

### **Option 3: Kubernetes**
1. Erstellen Sie Kubernetes Manifests (siehe k8s/ Ordner)
2. Deploy mit `kubectl apply -f k8s/`
3. Nutzen Sie ArgoCD für GitOps

### **Option 4: Railway / Render**
1. Verbinden Sie GitHub Repository
2. Platform erkennt automatisch Dockerfile
3. Automatisches Deployment bei Push

## 🔐 Secrets Management

Für GitHub Actions benötigen Sie folgende Secrets:

- `DOCKER_USERNAME` - Docker Registry Username
- `DOCKER_PASSWORD` - Docker Registry Password
- (Optional) `DEPLOY_SSH_KEY` - SSH Key für Server-Deployment

Secrets hinzufügen unter: **Settings → Secrets and variables → Actions**

## 🎯 Branch-Strategie

```
main (production - Port 8501)
  ├── feat/deploy_mas-64 (Port 8523)
  ├── feat/webscraping_mas-55 (Port 8534)
  ├── feat/new-feature (Port 8512)
  └── feat/another-feature (Port 8547)
```

**Vorteile:**
- ✅ Jeder Feature-Branch hat eigene Test-Umgebung
- ✅ Paralleles Testen mehrerer Features
- ✅ Kein Konflikt zwischen Branches
- ✅ Einfaches Teilen von Test-URLs mit Team
- ✅ Automatisches Cleanup spart Ressourcen

## 📊 Port-Zuweisung

Ports werden automatisch basierend auf dem Branch-Namen berechnet:
- **main**: 8501 (fest)
- **feat/***: 8500-8600 (dynamisch per MD5-Hash)

Beispiele:
```bash
feat/deploy_mas-64     → Port 8523
feat/webscraping_mas-55 → Port 8534
feat/new-ui            → Port 8512
```

## 📊 Umgebungen

| Environment | Branch Pattern | Port | URL | Auto-Deploy |
|-------------|---------------|------|-----|-------------|
| Production | main | 8501 | http://your-domain.com | ✅ |
| Feature 1 | feat/deploy_mas-64 | 8523 | http://feat-deploy-mas-64.domain.com | ✅ |
| Feature 2 | feat/webscraping_mas-55 | 8534 | http://feat-webscraping-mas-55.domain.com | ✅ |
| Feature N | feat/* | 8500-8600 | http://feat-*.domain.com | ✅ |
| Development | local | 8501 | http://localhost:8501 | ❌ |

**Hinweis:** Jeder Feature-Branch erhält automatisch eine eigene Umgebung!

## ⚙️ Ollama Model Management

Models werden automatisch beim ersten Start heruntergeladen:

```bash
# Im Container
docker exec ollama-prod ollama pull llama3.2:3b

# Liste alle Models
docker exec ollama-prod ollama list
```

## 🛠️ Troubleshooting

### Feature-Branch Container startet nicht:
```bash
# Logs anzeigen
docker logs wiso-chatbot-feat-your-branch

# Oder mit compose
docker-compose -f docker-compose.feat-your-branch.yml logs -f
```

### Port bereits belegt:
```bash
# Zeige alle aktiven Deployments
./list-deployments.sh

# Stoppe konfliktierendes Deployment
./cleanup-feature.sh feat/old-branch
```

### Ollama Verbindungsfehler:
```bash
# Prüfen Sie ob Ollama läuft
docker ps | grep ollama-feat-your-branch

# Neu starten
docker restart ollama-feat-your-branch
```

### Branch-spezifische Daten löschen:
```bash
# Cleanup mit Volume-Löschung
docker-compose -f docker-compose.feat-your-branch.yml down -v
```

### Alle Feature-Deployments auf einmal stoppen:
```bash
# Finde und stoppe alle feature containers
docker ps --filter "label=deployment=feature" --format "{{.Names}}" | xargs -r docker stop
```

### Speicherprobleme:
```bash
# Cleanup nicht verwendeter Resources
docker system prune -a
docker volume prune

# Nur alte Feature-Branch Volumes
docker volume ls | grep feat- | awk '{print $2}' | xargs -r docker volume rm
```

## 📝 Nächste Schritte

### 1. ✅ Lokales Testing
```bash
# Feature-Branch deployen
./deploy-feature.sh

# Testen unter http://localhost:<port>
# Port wird im Output angezeigt
```

### 2. ✅ Push zu GitHub
```bash
git add .
git commit -m "Add feature"
git push origin feat/your-feature
```

### 3. ✅ Automatisches Deployment
- GitHub Actions baut und deployt automatisch
- PR erhält Kommentar mit Deployment-URL
- Team kann Feature live testen

### 4. ✅ Nach Merge/Delete
- Automatisches Cleanup
- Resources werden freigegeben
- Kein manueller Aufwand

## 🚀 Quick Start

```bash
# 1. Clone Repository
git clone https://github.com/sebastianuzk/uzk-masterarbeit.git
cd uzk-masterarbeit

# 2. Checkout Feature-Branch
git checkout -b feat/my-new-feature

# 3. Mache Änderungen und deploy lokal
./deploy-feature.sh

# 4. Teste unter http://localhost:<port>

# 5. Push zu GitHub für automatisches Deployment
git push origin feat/my-new-feature

# 6. Cleanup nach Fertigstellung
./cleanup-feature.sh feat/my-new-feature
```

## 💡 Best Practices

1. **Branch-Naming**: Verwende `feat/` Prefix für automatisches Deployment
2. **Testing**: Teste lokal mit `./deploy-feature.sh` vor dem Push
3. **Cleanup**: Lösche alte Feature-Branches regelmäßig
4. **Resources**: Überwache mit `./list-deployments.sh`
5. **Logs**: Bei Problemen immer zuerst Logs prüfen

## 📞 Support

Bei Fragen oder Problemen:
- Prüfen Sie GitHub Actions Logs
- Schauen Sie in Docker Logs
- Öffnen Sie ein Issue im Repository
