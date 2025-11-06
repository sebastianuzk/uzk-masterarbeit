#!/bin/bash

# Stoppt lokale Streamlit-Deployments

BRANCH_NAME=${1:-$(git branch --show-current)}
SANITIZED_BRANCH=$(echo "$BRANCH_NAME" | sed 's/\//-/g' | tr '[:upper:]' '[:lower:]')

echo "🛑 Stopping Local Deployment: $BRANCH_NAME"
echo "================================================"

# Finde Streamlit-Prozesse für diesen Branch
if [ -n "$1" ]; then
    # Spezifischer Branch
    PIDS=$(pgrep -f "streamlit run.*${SANITIZED_BRANCH}" || true)
else
    # Alle Streamlit-Prozesse
    PIDS=$(pgrep -f "streamlit run" || true)
fi

if [ -z "$PIDS" ]; then
    echo "No running deployments found for: $BRANCH_NAME"
    exit 0
fi

echo "Stopping processes: $PIDS"
for pid in $PIDS; do
    PORT=$(lsof -Pan -p $pid -iTCP -sTCP:LISTEN 2>/dev/null | grep LISTEN | awk '{print $9}' | cut -d: -f2 | head -1)
    echo "  Stopping PID $pid (Port: $PORT)"
    kill $pid 2>/dev/null || true
done

sleep 2

# Prüfe ob gestoppt
REMAINING=$(pgrep -f "streamlit run" || true)
if [ -z "$REMAINING" ]; then
    echo "✅ All deployments stopped"
else
    echo "⚠️  Some processes still running: $REMAINING"
    echo "Use 'kill -9' if needed"
fi

# Optional: Cleanup logs
if [ -f "logs/streamlit-${SANITIZED_BRANCH}.log" ]; then
    read -p "Delete log file? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm "logs/streamlit-${SANITIZED_BRANCH}.log"
        echo "✅ Log file deleted"
    fi
fi
