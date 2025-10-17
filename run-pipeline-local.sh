#!/bin/bash

# Lokale CI/CD Pipeline Ausführung mit 'act'
# Simuliert GitHub Actions lokal

set -e

echo "🔄 Local CI/CD Pipeline Execution"
echo "================================================"
echo ""

# Prüfe ob 'act' installiert ist
if ! command -v act &> /dev/null; then
    echo "❌ 'act' is not installed!"
    echo ""
    echo "Install with:"
    echo "  # Ubuntu/Debian:"
    echo "  curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
    echo ""
    echo "  # macOS:"
    echo "  brew install act"
    echo ""
    echo "  # Or download from: https://github.com/nektos/act/releases"
    echo ""
    exit 1
fi

# Prüfe ob Docker läuft (act benötigt Docker)
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running!"
    echo "act requires Docker to run GitHub Actions locally."
    echo ""
    echo "Alternatives without Docker:"
    echo "  1. Use ./deploy-local.sh for local Streamlit deployment"
    echo "  2. Push to GitHub to trigger real CI/CD pipeline"
    echo ""
    exit 1
fi

# Zeige verfügbare Workflows
echo "📋 Available Workflows:"
echo ""
act -l
echo ""

# Frage welche Action ausgeführt werden soll
echo "Select workflow to run:"
echo "  1) Run all tests"
echo "  2) Build Docker image"
echo "  3) Deploy feature branch"
echo "  4) Full pipeline (test + build + deploy)"
echo "  5) Custom workflow"
echo ""

read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo "Running tests..."
        act -j test
        ;;
    2)
        echo "Building Docker image..."
        act -j build
        ;;
    3)
        echo "Deploying feature branch..."
        BRANCH=$(git branch --show-current)
        echo "Current branch: $BRANCH"
        act -j deploy-feature --env GITHUB_REF=refs/heads/$BRANCH
        ;;
    4)
        echo "Running full pipeline..."
        act push
        ;;
    5)
        echo "Enter workflow name:"
        read -p "Workflow: " workflow
        act -j $workflow
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Local pipeline execution completed!"
