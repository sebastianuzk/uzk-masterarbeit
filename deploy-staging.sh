#!/bin/bash

# Deployment script for staging
set -e

echo "🚀 Deploying to Staging..."

# Load environment variables
if [ -f .env.staging ]; then
    export $(cat .env.staging | xargs)
fi

# Pull latest changes
git pull origin feat/deploy_mas-64

# Build and deploy with Docker Compose
docker-compose -f docker-compose.staging.yml down
docker-compose -f docker-compose.staging.yml build --no-cache
docker-compose -f docker-compose.staging.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
if docker-compose -f docker-compose.staging.yml ps | grep -q "Up"; then
    echo "✅ Staging deployment successful!"
    echo "🌐 Chatbot available at: http://localhost:8502"
else
    echo "❌ Deployment failed!"
    docker-compose -f docker-compose.staging.yml logs
    exit 1
fi

# Pull Ollama model if not exists
docker exec ollama-staging ollama pull llama3.2:3b || true

echo "✅ Deployment complete!"
