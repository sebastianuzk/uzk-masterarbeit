"""
Process Engine Startup Script
Automatisierte Initialisierung und Deployment der Camunda Platform 8 Umgebung
"""

import os
import sys
import time
import requests
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

# Füge src zum Python Path hinzu
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from config.settings import Settings
from src.process_engine.process_client import ProcessEngineClient
from src.process_engine.bpmn_generator import BPMNGenerator
from src.process_engine.workflow_manager import WorkflowManager


class ProcessEngineSetup:
    """Setup und Management für Process Engine"""
    
    def __init__(self):
        self.settings = Settings()
        self.docker_compose_file = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
        self.workflows_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "workflows")
        self.max_wait_time = 300  # 5 Minuten
        
    def check_docker_available(self) -> bool:
        """Prüft ob Docker verfügbar ist"""
        try:
            result = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                print(f"✅ Docker verfügbar: {result.stdout.strip()}")
                return True
            else:
                print("❌ Docker nicht verfügbar")
                return False
        except Exception as e:
            print(f"❌ Docker Prüfung fehlgeschlagen: {e}")
            return False
    
    def start_camunda_platform(self) -> bool:
        """Startet Camunda Platform 8 via Docker Compose"""
        if not os.path.exists(self.docker_compose_file):
            print(f"❌ Docker Compose Datei nicht gefunden: {self.docker_compose_file}")
            return False
        
        print("🚀 Starte Camunda Platform 8...")
        
        try:
            # Docker Compose up im richtigen Verzeichnis ausführen
            original_dir = os.getcwd()
            os.chdir(os.path.dirname(self.docker_compose_file))
            
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            os.chdir(original_dir)  # Zurück zum ursprünglichen Verzeichnis
            
            if result.returncode == 0:
                print("✅ Camunda Platform 8 Container gestartet")
                return True
            else:
                print(f"❌ Container Start fehlgeschlagen: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Container Start Timeout")
            return False
        except Exception as e:
            print(f"❌ Container Start Fehler: {e}")
            return False
    
    def wait_for_services(self) -> bool:
        """Wartet bis alle Services verfügbar sind"""
        services = {
            "Elasticsearch": "http://localhost:9200/_cluster/health",
            "Zeebe": "http://localhost:9600/health", 
            "Operate": "http://localhost:8081/actuator/health",
            "Tasklist": "http://localhost:8082/actuator/health"
        }
        
        print("⏳ Warte auf Services...")
        start_time = time.time()
        
        while time.time() - start_time < self.max_wait_time:
            all_ready = True
            
            for service_name, health_url in services.items():
                try:
                    response = requests.get(health_url, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ {service_name} bereit")
                    else:
                        print(f"⏳ {service_name} noch nicht bereit (Status: {response.status_code})")
                        all_ready = False
                except requests.RequestException:
                    print(f"⏳ {service_name} noch nicht erreichbar")
                    all_ready = False
            
            if all_ready:
                print("🎉 Alle Services sind bereit!")
                return True
            
            time.sleep(10)
        
        print(f"❌ Services nicht bereit nach {self.max_wait_time} Sekunden")
        return False
    
    def generate_and_deploy_workflows(self) -> bool:
        """Generiert und deployt BPMN Workflows"""
        try:
            print("📄 Generiere BPMN Workflows...")
            
            # Erstelle Workflows-Verzeichnis
            os.makedirs(self.workflows_dir, exist_ok=True)
            
            # Generiere Workflows
            generator = BPMNGenerator()
            workflows = generator.generate_all_university_workflows(self.workflows_dir)
            
            print(f"✅ {len(workflows)} BPMN Workflows generiert")
            
            # Deploye Workflows
            if self.settings.ENABLE_PROCESS_ENGINE:
                print("🚀 Deploye Workflows...")
                
                process_client = ProcessEngineClient()
                deployed_count = 0
                
                for workflow_id, file_path in workflows.items():
                    deployment = process_client.deploy_workflow(file_path)
                    if deployment:
                        print(f"✅ Workflow deployed: {workflow_id}")
                        deployed_count += 1
                    else:
                        print(f"⚠️ Workflow deployment fehlgeschlagen: {workflow_id}")
                
                print(f"🎉 {deployed_count}/{len(workflows)} Workflows erfolgreich deployed")
                return deployed_count > 0
            else:
                print("⚠️ Process Engine deaktiviert - keine Deployments")
                return True
                
        except Exception as e:
            print(f"❌ Workflow Generation/Deployment fehlgeschlagen: {e}")
            return False
    
    def test_process_engine(self) -> bool:
        """Testet Process Engine Funktionalität"""
        try:
            print("🔧 Teste Process Engine...")
            
            process_client = ProcessEngineClient()
            
            # Health Check
            health = process_client.get_health_status()
            
            print("🏥 Health Status:")
            for component, status in health.items():
                if component != 'timestamp':
                    icon = "✅" if status else "❌"
                    print(f"   {icon} {component.capitalize()}: {'OK' if status else 'NICHT OK'}")
            
            # Test Workflow Start (falls möglich)
            if health.get('zeebe', False):
                print("🧪 Teste Workflow-Start...")
                
                test_variables = {
                    'student_id': '1234567',
                    'email': 'test@example.com',
                    'test_mode': True
                }
                
                try:
                    instance = process_client.start_process_instance(
                        'student-transcript-request',
                        test_variables
                    )
                    
                    if instance:
                        print(f"✅ Test-Workflow gestartet: {instance.process_instance_key}")
                        
                        # Workflow wieder abbrechen
                        process_client.cancel_process_instance(instance.process_instance_key)
                        print("✅ Test-Workflow erfolgreich abgebrochen")
                        return True
                    else:
                        print("⚠️ Test-Workflow konnte nicht gestartet werden")
                        return False
                        
                except Exception as e:
                    print(f"⚠️ Test-Workflow Fehler: {e}")
                    return False
            else:
                print("⚠️ Zeebe nicht verfügbar - kein Workflow-Test möglich")
                return False
                
        except Exception as e:
            print(f"❌ Process Engine Test fehlgeschlagen: {e}")
            return False
    
    def setup_environment_file(self) -> bool:
        """Erstellt .env Datei falls nicht vorhanden"""
        env_file = ".env"
        env_example = ".env.example"
        
        if not os.path.exists(env_file):
            if os.path.exists(env_example):
                print("📝 Kopiere .env.example zu .env...")
                
                try:
                    with open(env_example, 'r', encoding='utf-8') as src:
                        content = src.read()
                    
                    with open(env_file, 'w', encoding='utf-8') as dst:
                        dst.write(content)
                    
                    print("✅ .env Datei erstellt")
                    print("⚠️ WICHTIG: Bearbeiten Sie die .env Datei mit Ihren spezifischen Werten!")
                    return True
                    
                except Exception as e:
                    print(f"❌ .env Datei Erstellung fehlgeschlagen: {e}")
                    return False
            else:
                print("❌ .env.example nicht gefunden")
                return False
        else:
            print("✅ .env Datei bereits vorhanden")
            return True
    
    def install_dependencies(self) -> bool:
        """Installiert Python-Abhängigkeiten"""
        print("📦 Installiere Python-Abhängigkeiten...")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                print("✅ Abhängigkeiten erfolgreich installiert")
                return True
            else:
                print(f"❌ Abhängigkeiten Installation fehlgeschlagen: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Abhängigkeiten Installation Timeout")
            return False
        except Exception as e:
            print(f"❌ Abhängigkeiten Installation Fehler: {e}")
            return False
    
    def run_full_setup(self) -> bool:
        """Führt komplettes Setup aus"""
        print("🎯 Starte Process Engine Full Setup...")
        print("=" * 60)
        
        steps = [
            ("Environment Setup", self.setup_environment_file),
            ("Docker Check", self.check_docker_available),
            ("Dependencies Installation", self.install_dependencies),
            ("Camunda Platform Start", self.start_camunda_platform),
            ("Services Wait", self.wait_for_services),
            ("Workflows Generation/Deployment", self.generate_and_deploy_workflows),
            ("Process Engine Test", self.test_process_engine)
        ]
        
        for step_name, step_function in steps:
            print(f"\n🔄 {step_name}...")
            if not step_function():
                print(f"❌ Setup fehlgeschlagen bei: {step_name}")
                return False
            print(f"✅ {step_name} erfolgreich")
        
        print("\n" + "=" * 60)
        print("🎉 Process Engine Setup erfolgreich abgeschlossen!")
        print("\n📋 Nächste Schritte:")
        print("   1. Bearbeiten Sie die .env Datei mit Ihren Einstellungen")
        print("   2. Starten Sie den Chatbot: python main.py")
        print("   3. Testen Sie Process Engine Features in der Streamlit App")
        print("\n🌐 Verfügbare URLs:")
        print("   - Operate: http://localhost:8081")
        print("   - Tasklist: http://localhost:8082") 
        print("   - Elasticsearch: http://localhost:9200")
        print("   - Zeebe Monitoring: http://localhost:9600")
        
        return True
    
    def stop_camunda_platform(self) -> bool:
        """Stoppt Camunda Platform"""
        print("🛑 Stoppe Camunda Platform...")
        
        try:
            original_dir = os.getcwd()
            os.chdir(os.path.dirname(self.docker_compose_file))
            
            result = subprocess.run(
                ["docker-compose", "down"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            os.chdir(original_dir)  # Zurück zum ursprünglichen Verzeichnis
            
            if result.returncode == 0:
                print("✅ Camunda Platform gestoppt")
                return True
            else:
                print(f"❌ Stoppen fehlgeschlagen: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Stoppen Fehler: {e}")
            return False


def main():
    """Hauptfunktion für Setup Script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process Engine Setup")
    parser.add_argument(
        "action", 
        choices=["setup", "start", "stop", "test", "deploy"],
        help="Aktion auszuführen"
    )
    
    args = parser.parse_args()
    setup = ProcessEngineSetup()
    
    if args.action == "setup":
        success = setup.run_full_setup()
    elif args.action == "start":
        success = setup.start_camunda_platform() and setup.wait_for_services()
    elif args.action == "stop":
        success = setup.stop_camunda_platform()
    elif args.action == "test":
        success = setup.test_process_engine()
    elif args.action == "deploy":
        success = setup.generate_and_deploy_workflows()
    else:
        print(f"❌ Unbekannte Aktion: {args.action}")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()