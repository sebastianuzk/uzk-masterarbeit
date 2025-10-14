#!/usr/bin/env python3
"""
Standalone Camunda Docker Starter

Startet die Camunda Platform 7 Docker Container automatisch
ohne die Streamlit App zu starten.
"""

import sys
import os
import time
import requests
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from camunda_integration.services.docker_manager import DockerManager


def print_status(message: str, status: str = "INFO"):
    """Formatierte Status-Ausgabe"""
    colors = {
        "INFO": "\033[94m",    # Blau
        "SUCCESS": "\033[92m", # Grün
        "WARNING": "\033[93m", # Gelb
        "ERROR": "\033[91m",   # Rot
        "RESET": "\033[0m"     # Reset
    }
    
    color = colors.get(status, colors["INFO"])
    reset = colors["RESET"]
    
    timestamp = time.strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{reset}")


def check_api_availability(max_attempts: int = 30, delay: int = 2) -> bool:
    """
    Prüft ob die Camunda REST API verfügbar ist
    
    Args:
        max_attempts: Maximale Anzahl der Versuche
        delay: Wartezeit zwischen Versuchen in Sekunden
    
    Returns:
        True wenn API verfügbar, False sonst
    """
    print_status("Prüfe Camunda API-Verfügbarkeit...")
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get("http://localhost:8080/engine-rest/engine", timeout=5)
            if response.status_code == 200:
                print_status("✅ Camunda API ist verfügbar!", "SUCCESS")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if attempt < max_attempts:
            print_status(f"⏳ Versuch {attempt}/{max_attempts} - warte {delay} Sekunden...")
            time.sleep(delay)
    
    print_status("❌ Camunda API nicht erreichbar nach {max_attempts} Versuchen", "ERROR")
    return False


def check_auto_deployment() -> bool:
    """
    Prüft ob BPMN-Prozesse automatisch deployed wurden
    
    Returns:
        True wenn Prozesse deployed sind, False sonst
    """
    try:
        response = requests.get("http://localhost:8080/engine-rest/process-definition", timeout=5)
        if response.status_code == 200:
            processes = response.json()
            if processes:
                print_status(f"✅ {len(processes)} BPMN-Prozesse auto-deployed:", "SUCCESS")
                for process in processes:
                    print_status(f"  - {process.get('key', 'N/A')}: {process.get('name', 'N/A')}")
                return True
            else:
                print_status("⚠️ Keine BPMN-Prozesse deployed", "WARNING")
                return False
    except Exception as e:
        print_status(f"❌ Fehler beim Prüfen der Deployments: {str(e)}", "ERROR")
        return False


def main():
    """Hauptfunktion für Camunda Docker Start"""
    print_status("🚀 Camunda Docker Starter", "INFO")
    print_status("=" * 50, "INFO")
    
    try:
        # Docker Manager initialisieren
        docker_manager = DockerManager()
        
        # Docker-Verfügbarkeit prüfen
        print_status("Prüfe Docker-Installation...")
        if not docker_manager.is_docker_available():
            print_status("❌ Docker ist nicht verfügbar oder nicht gestartet", "ERROR")
            print_status("Bitte installieren und starten Sie Docker Desktop", "ERROR")
            sys.exit(1)
        
        if not docker_manager.is_compose_available():
            print_status("❌ Docker Compose ist nicht verfügbar", "ERROR")
            sys.exit(1)
        
        print_status("✅ Docker und Docker Compose verfügbar", "SUCCESS")
        
        # Container-Status prüfen
        print_status("Prüfe Container-Status...")
        status_result = docker_manager.get_status()
        
        if status_result.get("success") and "camunda-platform-clean" in status_result.get("output", ""):
            print_status("✅ Camunda Container läuft bereits", "SUCCESS")
            
            # API-Verfügbarkeit prüfen
            if check_api_availability(max_attempts=10, delay=1):
                check_auto_deployment()
                print_status("🎉 Camunda ist vollständig einsatzbereit!", "SUCCESS")
                print_status("", "INFO")
                print_status("🌐 Camunda Cockpit: http://localhost:8080/camunda", "INFO")
                print_status("🔧 REST API: http://localhost:8080/engine-rest", "INFO")
                return
            else:
                print_status("⏳ Container läuft, aber API noch nicht bereit", "WARNING")
        
        # Container starten
        print_status("🐳 Starte Camunda Docker Container...", "INFO")
        result = docker_manager.start_camunda(detached=True)
        
        if not result.get("success", False):
            error_msg = result.get("error", "Unbekannter Fehler")
            print_status(f"❌ Container-Start fehlgeschlagen: {error_msg}", "ERROR")
            sys.exit(1)
        
        print_status("✅ Container erfolgreich gestartet!", "SUCCESS")
        
        # Warte auf API-Verfügbarkeit
        if check_api_availability():
            # Prüfe Auto-Deployment
            print_status("Prüfe Auto-Deployment...")
            time.sleep(5)  # Kurz warten für Deployment
            check_auto_deployment()
            
            print_status("", "INFO")
            print_status("🎉 Camunda Platform 7 ist vollständig einsatzbereit!", "SUCCESS")
            print_status("", "INFO")
            print_status("📋 Verfügbare Interfaces:", "INFO")
            print_status("  🌐 Camunda Cockpit:    http://localhost:8080/camunda", "INFO")
            print_status("  🔧 REST API:           http://localhost:8080/engine-rest", "INFO")
            print_status("  📊 Process Definitions: http://localhost:8080/engine-rest/process-definition", "INFO")
            print_status("", "INFO")
            print_status("💡 Zum Stoppen: docker compose down (im docker/ Verzeichnis)", "INFO")
        else:
            print_status("❌ Container gestartet, aber API nicht verfügbar", "ERROR")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print_status("\n⏹️ Start abgebrochen", "WARNING")
        sys.exit(0)
    except Exception as e:
        print_status(f"❌ Unerwarteter Fehler: {str(e)}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()