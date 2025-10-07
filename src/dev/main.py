"""
Leichtgewichtige Entwicklungsumgebung für E-Mail-Tool Experimente
Ausführbar mit VS Code "Run Python File" Button
"""
import os
import sys

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.tools.email_tool import create_email_tool
from config.settings import settings


def test_email_tool():
    """Teste das E-Mail-Tool direkt"""
    print("🧪 E-Mail-Tool Experimentierumgebung")
    print("=" * 50)
    
    # Erstelle E-Mail-Tool
    email_tool = create_email_tool()
    
    # Zeige Tool-Informationen
    print(f"📧 Tool-Name: {email_tool.name}")
    print(f"📝 Beschreibung: {email_tool.description}")
    print()
    
    # Automatische E-Mail-Eingabe (IMMER an Standard-E-Mail)
    print("📮 E-Mail senden (IMMER an Standard-E-Mail):")
    print("-" * 30)
    print(f"🎯 Empfänger: {settings.DEFAULT_RECIPIENT} (FEST EINGESTELLT)")
    
    try:
        # Nur Betreff und Nachricht abfragen - Empfänger ist automatisch
        subject = input("📝 Betreff: ").strip()
        if not subject:
            subject = "Test E-Mail vom Chatbot"
        
        body = input("💬 Nachricht: ").strip()
        if not body:
            body = "Dies ist eine Test-E-Mail vom autonomen Chatbot-Agenten."
        
        print("\n🚀 Sende E-Mail...")
        print("-" * 30)
        
        # E-Mail senden - recipient wird automatisch durch DEFAULT_RECIPIENT ersetzt
        result = email_tool._run(
            recipient="dummy@example.com",  # Wird automatisch überschrieben
            subject=subject,
            body=body,
            sender_name="Chatbot Agent"
        )
        
        print(f"📋 Ergebnis: {result}")
        
    except KeyboardInterrupt:
        print("\n❌ Abgebrochen durch Benutzer")
    except Exception as e:
        print(f"❌ Fehler: {str(e)}")
    
    print("\n✅ Experiment beendet")


def show_email_config_help():
    """Zeige Hilfe zur E-Mail-Konfiguration"""
    print("\n📋 E-Mail-Konfiguration (settings.py):")
    print("=" * 40)
    print("""
Bearbeiten Sie die Datei config/settings.py und setzen Sie:

# E-Mail Konfiguration
SMTP_SERVER = "smtp.gmail.com"  # Für Gmail
SMTP_PORT = 587
SMTP_USERNAME = "ihre-email@gmail.com"
SMTP_PASSWORD = "ihr-app-passwort"

# Standard-E-Mail für ALLE ausgehenden E-Mails
DEFAULT_RECIPIENT = "ihre-standard-email@example.com"

# Für Outlook verwenden Sie:
# SMTP_SERVER = "smtp-mail.outlook.com"

WICHTIG: 
- Für Gmail verwenden Sie App-Passwörter (nicht Ihr normales Passwort)
- Aktivieren Sie 2FA und erstellen Sie ein App-Passwort in den Google-Kontoeinstellungen
- DEFAULT_RECIPIENT: ALLE E-Mails gehen an diese Adresse!
- Die Anmeldedaten sind bereits in Ihrer settings.py konfiguriert
""")


if __name__ == "__main__":
    print("🤖 Autonomer Chatbot - E-Mail-Tool Entwicklung")
    print("=" * 60)
    
    # Überprüfe E-Mail-Konfiguration aus Settings
    print(f"📧 Konfiguration aus settings.py:")
    print(f"   SMTP_SERVER: {settings.SMTP_SERVER if settings.SMTP_SERVER else '❌ NICHT GESETZT'}")
    print(f"   SMTP_PORT: {settings.SMTP_PORT if settings.SMTP_PORT else '❌ NICHT GESETZT'}")
    print(f"   SMTP_USERNAME: {settings.SMTP_USERNAME if settings.SMTP_USERNAME else '❌ NICHT GESETZT'}")
    print(f"   SMTP_PASSWORD: {'✅ GESETZT' if settings.SMTP_PASSWORD else '❌ NICHT GESETZT'}")
    print(f"   DEFAULT_RECIPIENT: {settings.DEFAULT_RECIPIENT if settings.DEFAULT_RECIPIENT else '❌ NICHT GESETZT'}")
    print(f"\n⚠️  WICHTIG: ALLE E-Mails werden an {settings.DEFAULT_RECIPIENT} gesendet!")
    
    if not all([settings.SMTP_SERVER, settings.SMTP_USERNAME, settings.SMTP_PASSWORD, settings.DEFAULT_RECIPIENT]):
        print("\n⚠️  E-Mail-Konfiguration in settings.py unvollständig!")
        show_email_config_help()
        
        choice = input("\nTrotzdem fortfahren? (j/n): ").lower()
        if choice != 'j':
            print("👋 Auf Wiedersehen!")
            sys.exit(0)
    else:
        print(f"\n✅ E-Mail-Konfiguration vollständig:")
        print(f"   📧 Server: {settings.SMTP_SERVER}")
        print(f"   👤 Benutzer: {settings.SMTP_USERNAME}")
        print(f"   🔐 Passwort: {'*' * len(settings.SMTP_PASSWORD)}")
        print(f"   📬 Standard-Empfänger: {settings.DEFAULT_RECIPIENT}")
        print(f"   🎯 ALLE E-MAILS GEHEN AN: {settings.DEFAULT_RECIPIENT}")
    
    print()
    
    # Führe E-Mail-Test aus
    test_email_tool()