"""
E-Mail-Tool Test-Modus für Entwicklung
Simuliert E-Mail-Versand ohne echte SMTP-Verbindung
"""
from src.tools.email_tool import EmailTool

class EmailToolTestMode(EmailTool):
    """Test-Version des E-Mail-Tools ohne echten Versand"""
    
    def _run(self, recipient: str, subject: str, body: str, sender_name: str = "Test-Bot") -> str:
        """Simuliert E-Mail-Versand"""
        from config.settings import DEFAULT_RECIPIENT
        
        print("📧 SIMULIERTER E-MAIL-VERSAND")
        print("="*40)
        print(f"Von: {sender_name}")
        print(f"An: {DEFAULT_RECIPIENT} (Standard-Adresse)")
        print(f"Betreff: {subject}")
        print(f"Inhalt: {body}")
        print("="*40)
        
        return f"✅ E-Mail simuliert gesendet an: {DEFAULT_RECIPIENT}"

def test_email_simulation():
    """Teste E-Mail-Tool im Simulationsmodus"""
    print("🧪 E-Mail-Tool Simulation")
    print("="*50)
    
    tool = EmailToolTestMode()
    result = tool._run(
        recipient="ignoriert@test.com",
        subject="Test-E-Mail vom Chatbot",
        body="Das ist eine Test-Nachricht für die Entwicklung."
    )
    
    print("\n📋 Ergebnis:", result)
    return result

if __name__ == "__main__":
    test_email_simulation()