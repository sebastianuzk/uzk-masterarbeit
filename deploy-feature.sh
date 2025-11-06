#!/bin/bash

# Universal Feature Branch Deployment Script
set -e

# Konfiguration
BRANCH_NAME=${1:-$(git branch --show-current)}
SANITIZED_BRANCH=$(echo "$BRANCH_NAME" | sed 's/\//-/g' | tr '[:upper:]' '[:lower:]')
BASE_PORT=8500

echo "🚀 Deploying Feature Branch: $BRANCH_NAME"
echo "================================================"

# Generiere eindeutigen Port basierend auf Branch-Name
PORT_OFFSET=$(echo -n "$SANITIZED_BRANCH" | md5sum | cut -c1-4)
PORT=$((BASE_PORT + 0x$PORT_OFFSET % 100))

# Container-Name
CONTAINER_NAME="wiso-chatbot-$SANITIZED_BRANCH"
OLLAMA_CONTAINER="ollama-$SANITIZED_BRANCH"
NETWORK_NAME="chatbot-${SANITIZED_BRANCH}-network"

echo "Configuration:"
echo "  Branch: $BRANCH_NAME"
echo "  Sanitized: $SANITIZED_BRANCH"
echo "  Container: $CONTAINER_NAME"
echo "  Port: $PORT"
echo "  Network: $NETWORK_NAME"
echo ""

# Erstelle docker-compose file dynamisch
cat > "docker-compose.${SANITIZED_BRANCH}.yml" <<EOF
version: '3.8'

services:
  chatbot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ${CONTAINER_NAME}
    ports:
      - "${PORT}:8501"
    environment:
      - PYTHONPATH=/app
      - ENVIRONMENT=feature
      - BRANCH_NAME=${BRANCH_NAME}
      - OLLAMA_BASE_URL=http://${OLLAMA_CONTAINER}:11434
    volumes:
      - ${SANITIZED_BRANCH}-data:/app/data
      - ./config:/app/config
    restart: unless-stopped
    networks:
      - ${NETWORK_NAME}
    depends_on:
      - ollama
    labels:
      - "branch=${BRANCH_NAME}"
      - "deployment=feature"

  ollama:
    image: ollama/ollama:latest
    container_name: ${OLLAMA_CONTAINER}
    volumes:
      - ${SANITIZED_BRANCH}-ollama-data:/root/.ollama
    restart: unless-stopped
    networks:
      - ${NETWORK_NAME}
    labels:
      - "branch=${BRANCH_NAME}"

volumes:
  ${SANITIZED_BRANCH}-data:
  ${SANITIZED_BRANCH}-ollama-data:

networks:
  ${NETWORK_NAME}:
    driver: bridge
EOF

echo "✓ Docker Compose file created: docker-compose.${SANITIZED_BRANCH}.yml"

# Stoppe existierende Container für diesen Branch
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "⏹️  Stopping existing deployment..."
    docker-compose -f "docker-compose.${SANITIZED_BRANCH}.yml" down
fi

# Build und Deploy
echo "🔨 Building and deploying..."
docker-compose -f "docker-compose.${SANITIZED_BRANCH}.yml" build --no-cache
docker-compose -f "docker-compose.${SANITIZED_BRANCH}.yml" up -d

# Warte auf Health Check
echo "⏳ Waiting for services to start..."
sleep 15

# Prüfe Status
if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "✅ Deployment successful!"
    echo ""
    echo "================================================"
    echo "🌐 Chatbot available at: http://localhost:${PORT}"
    echo "📦 Container: ${CONTAINER_NAME}"
    echo "🔍 View logs: docker logs -f ${CONTAINER_NAME}"
    echo "🛑 Stop: docker-compose -f docker-compose.${SANITIZED_BRANCH}.yml down"
    echo "================================================"
    
    # Pull Ollama model
    echo ""
    echo "📥 Pulling Ollama model (this may take a while)..."
    docker exec ${OLLAMA_CONTAINER} ollama pull llama3.2:3b || echo "⚠️  Model pull failed, will retry on first use"
else
    echo "❌ Deployment failed!"
    docker-compose -f "docker-compose.${SANITIZED_BRANCH}.yml" logs
    exit 1
fi
