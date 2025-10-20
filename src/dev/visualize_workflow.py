#!/usr/bin/env python3
"""
Einfache Workflow-Visualisierung für den Plan-and-Execute Agent
"""

import sys
from pathlib import Path

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.plan_and_execute_agent import app

# Workflow-Diagramm erstellen
png_data = app.get_graph(xray=True).draw_mermaid_png()

# PNG im dev-Ordner speichern
dev_folder = Path(__file__).parent
output_file = dev_folder / "workflow_diagram.png"

with open(output_file, "wb") as f:
    f.write(png_data)

print(f"✅ Workflow-Diagramm gespeichert: {output_file}")

# Optional: In Jupyter anzeigen falls verfügbar
try:
    from IPython.display import Image, display
    display(Image(png_data))
except ImportError:
    print(f"🖼️  Öffne die Datei: {output_file}")