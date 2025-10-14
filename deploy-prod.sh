#!/bin/bash

# Deployment script for production
set -e

echo "🚀 Deploying to Production..."

# Load environment variables
if [ -f .env.production ]; then
    export $(cat .env.production | xargs)
fi

# Pull latest changes
git pull origin main

# Build and deploy with Docker Compose
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ Production deployment successful!"
    echo "🌐 Chatbot available at: http://localhost:8501"
else
    echo "❌ Deployment failed!"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi

# Pull Ollama model if not exists
docker exec ollama-prod ollama pull llama3.2:3b || true

echo "✅ Deployment complete!"
