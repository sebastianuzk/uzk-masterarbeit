"""
E-Mail-Tool für autonomen Chatbot-Agenten
"""
import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from config.settings import settings

class EmailInput(BaseModel):
    """Input für das E-Mail-Tool"""
    subject: str = Field(description="Betreff der E-Mail")
    body: str = Field(description="Inhalt der E-Mail")


class EmailTool(BaseTool):
    """Tool zum Versenden von E-Mails über SMTP"""
    
    name: str = "send_email"
    description: str = """Nutze dieses Tool, falls du eine Anfrage nicht beantworten kannst, oder der Benutzer explizit danach fragt. Nutze es nicht bei Smalltalk!
    Das Tool sendet eine E-Mail an die vorkonfigurierte Standard-E-Mail-Adresse.
    
    🎯 Verwendet automatisch die konfigurierten Umgebungsvariablen:
    🎯 Empfänger: DEFAULT_RECIPIENT aus .env
    🎯 Absender: SMTP_USERNAME aus .env

    Verwendung:
    - subject: Betreff der E-Mail
    - body: Inhalt der E-Mail
    
    Beispiel: send_email(subject="Test", body="Nachricht")
    ➜ Geht automatisch an die konfigurierte Standard-E-Mail-Adresse!
    """
    args_schema: type = EmailInput
    
    def _run(self, subject: str, body: str) -> str:
        """Sende E-Mail über SMTP - Verwendet konfigurierte Umgebungsvariablen"""
        try:
            # Standard-E-Mail aus Konfiguration verwenden
            actual_recipient = settings.DEFAULT_RECIPIENT if settings and settings.DEFAULT_RECIPIENT else None
            
            if not actual_recipient:
                return "❌ Keine Standard-E-Mail-Adresse konfiguriert (DEFAULT_RECIPIENT in .env)."
            
            # Validiere Standard-E-Mail-Adresse
            if not self._is_valid_email(actual_recipient):
                return f"❌ Ungültige Standard-E-Mail-Adresse: {actual_recipient}"
            
            # Lade E-Mail-Konfiguration aus Settings
            smtp_config = self._get_smtp_config()
            if not smtp_config:
                return "❌ E-Mail-Konfiguration unvollständig. Prüfen Sie Ihre .env Datei."
            
            # Erweitere den E-Mail-Body um Systeminfo
            enhanced_body = f"""[AUTOMATISCHE E-MAIL VOM CHATBOT-SYSTEM]
Empfänger: {actual_recipient}
Gesendet von: Autonomer Chatbot

---

{body}

---
Diese E-Mail wurde automatisch vom Chatbot-System gesendet."""
            
            # Erstelle E-Mail-Nachricht
            message = self._create_email_message(
                recipient=actual_recipient,
                subject=f"[CHATBOT] {subject}",
                body=enhanced_body,
                smtp_config=smtp_config
            )
            
            # Sende E-Mail
            success = self._send_email(message, smtp_config)
            
            if success:
                return f"✅ E-Mail erfolgreich gesendet an: {actual_recipient}"
            else:
                return f"❌ Fehler beim Senden der E-Mail an {actual_recipient}"
                
        except Exception as e:
            return f"❌ Unerwarteter Fehler beim E-Mail-Versand: {str(e)}"
    
    def _is_valid_email(self, email: str) -> bool:
        """Validiere E-Mail-Adresse mit Regex"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _get_smtp_config(self) -> Optional[Dict[str, Any]]:
        """Lade SMTP-Konfiguration aus Settings"""
        # Verwende Settings statt Umgebungsvariablen
        smtp_server = settings.SMTP_SERVER if settings else os.getenv("SMTP_SERVER")
        smtp_port = settings.SMTP_PORT if settings else os.getenv("SMTP_PORT")
        smtp_username = settings.SMTP_USERNAME if settings else os.getenv("SMTP_USERNAME")
        smtp_password = settings.SMTP_PASSWORD if settings else os.getenv("SMTP_PASSWORD")
        
        # Validiere erforderliche Konfiguration
        if not all([smtp_server, smtp_port, smtp_username, smtp_password]):
            return None
        
        return {
            "server": smtp_server,
            "port": int(smtp_port),
            "username": smtp_username,
            "password": smtp_password
        }
    
    def _create_email_message(
        self, 
        recipient: str, 
        subject: str, 
        body: str, 
        smtp_config: Dict[str, Any]
    ) -> MIMEMultipart:
        """Erstelle E-Mail-Nachricht"""
        message = MIMEMultipart("alternative")
        
        # Setze Header
        sender_email = smtp_config["username"]
        message["From"] = f"Autonomer Chatbot <{sender_email}>"
        message["To"] = recipient
        message["Subject"] = subject
        
        # Erstelle Text- und HTML-Version
        text_body = body
        # Ersetze Zeilenumbrüche für HTML außerhalb des f-strings
        body_html = body.replace('\n', '<br>')
        html_body = f"""
        <html>
          <body>
            {body_html}
          </body>
        </html>
        """
        
        # Füge beide Versionen hinzu
        text_part = MIMEText(text_body, "plain", "utf-8")
        html_part = MIMEText(html_body, "html", "utf-8")
        
        message.attach(text_part)
        message.attach(html_part)
        
        return message
    
    def _send_email(self, message: MIMEMultipart, smtp_config: Dict[str, Any]) -> bool:
        """Sende E-Mail über SMTP-Server"""
        try:
            # Verbinde mit SMTP-Server
            with smtplib.SMTP(smtp_config["server"], smtp_config["port"]) as server:
                server.starttls()  # Aktiviere TLS-Verschlüsselung
                server.login(smtp_config["username"], smtp_config["password"])
                
                # Sende E-Mail
                server.send_message(message)
                return True
                
        except smtplib.SMTPAuthenticationError:
            print("❌ SMTP-Authentifizierung fehlgeschlagen.")
            print("💡 Für Gmail: Verwenden Sie ein App-Passwort statt Ihres normalen Passworts!")
            print("   1. Aktivieren Sie 2-Faktor-Authentifizierung in Ihrem Google-Konto")
            print("   2. Gehen Sie zu Sicherheit > 2-Faktor-Authentifizierung > App-Passwörter")
            print("   3. Erstellen Sie ein neues App-Passwort für 'Mail'")
            print("   4. Verwenden Sie dieses App-Passwort in settings.py")
            return False
        except smtplib.SMTPRecipientsRefused:
            print("❌ Empfänger-E-Mail-Adresse wurde abgelehnt.")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP-Fehler: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Allgemeiner Fehler beim E-Mail-Versand: {str(e)}")
            return False


def create_email_tool() -> EmailTool:
    """Factory-Funktion für das E-Mail-Tool"""
    return EmailTool()