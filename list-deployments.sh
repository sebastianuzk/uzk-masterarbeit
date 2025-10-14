#!/bin/bash

# List all deployed Feature Branches
echo "📋 Active Feature Branch Deployments"
echo "================================================"
echo ""

# Finde alle feature-compose files
COMPOSE_FILES=$(ls docker-compose.feat-*.yml 2>/dev/null)

if [ -z "$COMPOSE_FILES" ]; then
    echo "No feature branch deployments found."
    exit 0
fi

echo "Found deployments:"
echo ""

for file in $COMPOSE_FILES; do
    SANITIZED_BRANCH=$(echo "$file" | sed 's/docker-compose\.\(.*\)\.yml/\1/')
    CONTAINER_NAME="wiso-chatbot-$SANITIZED_BRANCH"
    
    # Prüfe ob Container läuft
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        STATUS="🟢 Running"
        PORT=$(docker port "$CONTAINER_NAME" 2>/dev/null | grep 8501 | cut -d: -f2)
        URL="http://localhost:${PORT}"
    else
        STATUS="🔴 Stopped"
        URL="N/A"
    fi
    
    echo "Branch: $SANITIZED_BRANCH"
    echo "  Status: $STATUS"
    echo "  Container: $CONTAINER_NAME"
    if [ "$URL" != "N/A" ]; then
        echo "  URL: $URL"
    fi
    echo "  Compose: $file"
    echo ""
done

echo "================================================"
echo "Commands:"
echo "  View logs: docker logs -f <container-name>"
echo "  Stop: docker-compose -f <compose-file> down"
echo "  Cleanup: ./cleanup-feature.sh <branch-name>"
