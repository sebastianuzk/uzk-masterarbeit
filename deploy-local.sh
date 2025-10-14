#!/bin/bash

# Lokales Deployment ohne Docker
# Nutzt lokale Python-Umgebung und Streamlit

set -e

BRANCH_NAME=${1:-$(git branch --show-current)}
SANITIZED_BRANCH=$(echo "$BRANCH_NAME" | sed 's/\//-/g' | tr '[:upper:]' '[:lower:]')
BASE_PORT=8500

echo "🚀 Local Deployment (without Docker): $BRANCH_NAME"
echo "================================================"

# Berechne Port
PORT_OFFSET=$(echo -n "$SANITIZED_BRANCH" | md5sum | cut -c1-4)
PORT=$((BASE_PORT + 0x$PORT_OFFSET % 100))

echo "Configuration:"
echo "  Branch: $BRANCH_NAME"
echo "  Port: $PORT"
echo "  Environment: local"
echo ""

# Prüfe ob venv aktiviert ist
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Activating venv..."
    source venv/bin/activate 2>/dev/null || {
        echo "❌ venv not found. Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
    }
fi

# Installiere Dependencies (falls nötig)
echo "📦 Checking dependencies..."
pip install -q -r requirements.txt

# Setze Environment-Variablen
export PYTHONPATH=$(pwd)
export STREAMLIT_SERVER_PORT=$PORT
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export BRANCH_NAME=$BRANCH_NAME
export ENVIRONMENT=local-feature

# Erstelle Feature-spezifisches Data-Verzeichnis
FEATURE_DATA_DIR="data/local-${SANITIZED_BRANCH}"
mkdir -p "$FEATURE_DATA_DIR"
echo "📁 Feature data directory: $FEATURE_DATA_DIR"

# Prüfe ob Ollama läuft
echo "🔍 Checking Ollama..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Ollama is not running!"
    echo "Please start Ollama first:"
    echo "  ollama serve"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Stoppe andere Streamlit-Instanzen auf diesem Port
echo "🔍 Checking for existing processes on port $PORT..."
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⏹️  Stopping existing process on port $PORT..."
    kill $(lsof -t -i:$PORT) 2>/dev/null || true
    sleep 2
fi

# Starte Streamlit
echo ""
echo "🚀 Starting Streamlit on port $PORT..."
echo "================================================"
echo "  URL: http://localhost:$PORT"
echo "  Branch: $BRANCH_NAME"
echo "  Data: $FEATURE_DATA_DIR"
echo "  Press Ctrl+C to stop"
echo "================================================"
echo ""

# Starte im Hintergrund mit log file
LOG_FILE="logs/streamlit-${SANITIZED_BRANCH}.log"
mkdir -p logs

streamlit run src/ui/streamlit_app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    2>&1 | tee "$LOG_FILE"
