#!/bin/bash

# Cleanup Script for Feature Branch Deployments
set -e

BRANCH_NAME=${1:-$(git branch --show-current)}
SANITIZED_BRANCH=$(echo "$BRANCH_NAME" | sed 's/\//-/g' | tr '[:upper:]' '[:lower:]')

echo "🧹 Cleaning up Feature Branch Deployment: $BRANCH_NAME"
echo "================================================"

CONTAINER_NAME="wiso-chatbot-$SANITIZED_BRANCH"
COMPOSE_FILE="docker-compose.${SANITIZED_BRANCH}.yml"

# Prüfe ob Deployment existiert
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "⚠️  No deployment found for branch: $BRANCH_NAME"
    echo "Looking for: $COMPOSE_FILE"
    exit 0
fi

# Stoppe und entferne Container
echo "⏹️  Stopping containers..."
docker-compose -f "$COMPOSE_FILE" down -v

# Entferne Images (optional)
read -p "Remove Docker images for this branch? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing images..."
    docker images | grep "$SANITIZED_BRANCH" | awk '{print $3}' | xargs -r docker rmi -f
fi

# Entferne Compose-File
echo "🗑️  Removing compose file..."
rm -f "$COMPOSE_FILE"

echo "✅ Cleanup complete for branch: $BRANCH_NAME"
