#!/usr/bin/env python3
"""
Benachrichtigungs-System für Evaluation-Abschluss

Nutzt ntfy.sh für Push-Notifications aufs Handy
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


def send_ntfy_notification(message: str, topic: str = None, title: str = "Evaluation fertig!"):
    """
    Sendet Push-Notification über ntfy.sh
    
    Setup:
    1. Installiere ntfy App auf deinem Handy (Android/iOS)
    2. Öffne die App und abonniere ein Topic (z.B. "sebastian_thesis_eval")
    3. Setze NTFY_TOPIC in .env oder nutze den topic-Parameter
    
    Args:
        message: Nachrichteninhalt
        topic: ntfy.sh Topic (Standard: aus NTFY_TOPIC env var)
        title: Titel der Notification
    
    Returns:
        bool: True wenn erfolgreich
    """
    if not topic:
        topic = os.getenv("NTFY_TOPIC", "")
    
    if not topic:
        print("Kein ntfy Topic konfiguriert!")
        print("   Setze NTFY_TOPIC in .env oder übergebe topic-Parameter")
        print("   Beispiel: NTFY_TOPIC=sebastian_thesis_eval")
        return False
    
    url = f"https://ntfy.sh/{topic}"
    
    try:
        response = requests.post(
            url,
            json={
                "topic": topic,
                "message": message,
                "title": title,
                "priority": 4,
                "tags": ["white_check_mark"]
            }
        )
        
        if response.status_code == 200:
            print(f"ntfy Notification gesendet an Topic: {topic}")
            return True
        else:
            print(f"ntfy Fehler: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"ntfy Fehler: {e}")
        return False


def notify_evaluation_complete(
    model: str,
    agents: list[str],
    duration: str,
    results_path: str
):
    """
    Sendet Benachrichtigung über abgeschlossene Evaluation
    
    Args:
        model: Name des evaluierten Modells
        agents: Liste der evaluierten Agenten
        duration: Dauer der Evaluation
        results_path: Pfad zu den Ergebnissen
    """
    agents_str = ", ".join(agents)
    
    message = (
        f"Evaluation abgeschlossen!\n\n"
        f"🤖 Modell: {model}\n"
        f"🔧 Agents: {agents_str}\n"
        f"⏱️ Dauer: {duration}\n"
        f"📁 Ergebnisse: {results_path}"
    )
    
    if not send_ntfy_notification(message):
        print("\n⚠️ ntfy nicht konfiguriert!")
        print("   1. Installiere ntfy App auf deinem Handy")
        print("   2. Abonniere ein Topic (z.B. 'thesis_eval_sebastian')")
        print("   3. Setze in .env: NTFY_TOPIC=thesis_eval_sebastian")


def test_notification():
    """Testet die ntfy Notification"""
    print("Teste ntfy Notification...\n")
    send_ntfy_notification("Test-Nachricht von notify.py")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Notification System")
    parser.add_argument("--test", action="store_true", help="Teste Notification")
    
    args = parser.parse_args()
    
    if args.test:
        test_notification()
    else:
        # Beispiel-Notification
        notify_evaluation_complete(
            model="llama3.1:8b",
            agents=["single", "multi"],
            duration="1h 45m",
            results_path="data/eval/final/llama3.1-8b/20260109_110242"
        )
