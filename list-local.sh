#!/bin/bash

# Zeigt alle laufenden lokalen Streamlit-Instanzen

echo "📋 Active Local Streamlit Deployments"
echo "================================================"
echo ""

# Finde alle Streamlit-Prozesse
STREAMLIT_PIDS=$(pgrep -f "streamlit run" || true)

if [ -z "$STREAMLIT_PIDS" ]; then
    echo "No Streamlit instances running."
    exit 0
fi

echo "Running instances:"
echo ""

for pid in $STREAMLIT_PIDS; do
    # Hole Port und Command
    PORT=$(lsof -Pan -p $pid -iTCP -sTCP:LISTEN 2>/dev/null | grep LISTEN | awk '{print $9}' | cut -d: -f2 | head -1)
    CMD=$(ps -p $pid -o args= | head -1)
    
    if [ -n "$PORT" ]; then
        echo "PID: $pid"
        echo "  Port: $PORT"
        echo "  URL: http://localhost:$PORT"
        echo "  Command: $CMD"
        echo "  Stop: kill $pid"
        echo ""
    fi
done

echo "================================================"
echo ""
echo "Log files in: logs/"
ls -lh logs/*.log 2>/dev/null || echo "No log files found."
