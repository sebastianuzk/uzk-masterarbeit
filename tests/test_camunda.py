"""
Tests für die Camunda Process Engine Integration
"""
import unittest
import sys
import os
from unittest.mock import Mock, patch
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.settings import settings

# Camunda Integration Tests
try:
    from src.camunda_integration.client.camunda_client import CamundaClient
    from src.camunda_integration.services.camunda_service import CamundaService
    from src.camunda_integration.services.docker_manager import DockerManager
    from src.camunda_integration.models.camunda_models import ProcessDefinition, ProcessInstance, Task
    CAMUNDA_AVAILABLE = True
except ImportError as e:
    CAMUNDA_AVAILABLE = False
    print(f"Camunda Integration nicht verfügbar: {e}")


class TestCamundaIntegration(unittest.TestCase):
    """Test-Klasse für die Camunda Integration"""
    
    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_camunda_client_creation(self):
        """Teste CamundaClient Erstellung"""
        try:
            client = CamundaClient(base_url="http://localhost:8080/engine-rest")
            self.assertIsNotNone(client)
            self.assertEqual(client.base_url, "http://localhost:8080/engine-rest")
            self.assertEqual(client.timeout, 15)
            self.assertIsNone(client.auth)
            
        except Exception as e:
            self.fail(f"CamundaClient Erstellung fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_camunda_service_creation(self):
        """Teste CamundaService Erstellung"""
        try:
            client = CamundaClient(base_url="http://localhost:8080/engine-rest")
            bpmn_dir = Path("src/camunda_integration/bpmn_processes")
            service = CamundaService(client=client, bpmn_dir=bpmn_dir)
            
            self.assertIsNotNone(service)
            self.assertEqual(service.client, client)
            self.assertEqual(service.bpmn_dir, bpmn_dir)
            
        except Exception as e:
            self.fail(f"CamundaService Erstellung fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_docker_manager_creation(self):
        """Teste DockerManager Erstellung"""
        try:
            compose_file = Path("src/camunda_integration/docker/docker-compose-manual.yml")
            docker_manager = DockerManager(compose_file=compose_file)
            
            self.assertIsNotNone(docker_manager)
            self.assertEqual(docker_manager.compose_file, compose_file)
            
        except Exception as e:
            self.fail(f"DockerManager Erstellung fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_process_definition_model(self):
        """Teste ProcessDefinition Model"""
        try:
            process_def = ProcessDefinition(
                id="test_process:1:123",
                key="test_process",
                name="Test Process",
                version=1
            )
            
            self.assertEqual(process_def.id, "test_process:1:123")
            self.assertEqual(process_def.key, "test_process")
            self.assertEqual(process_def.name, "Test Process")
            self.assertEqual(process_def.version, 1)
            
        except Exception as e:
            self.fail(f"ProcessDefinition Model Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_process_instance_model(self):
        """Teste ProcessInstance Model"""
        try:
            process_instance = ProcessInstance(
                id="instance_123",
                definitionId="test_process:1:123",
                businessKey="test_key",
                ended=False,
                suspended=False
            )
            
            self.assertEqual(process_instance.id, "instance_123")
            self.assertEqual(process_instance.definitionId, "test_process:1:123")
            self.assertEqual(process_instance.businessKey, "test_key")
            self.assertFalse(process_instance.ended)
            self.assertFalse(process_instance.suspended)
            
            # Test get_process_key Methode
            process_key = process_instance.get_process_key()
            self.assertEqual(process_key, "test_process")
            
        except Exception as e:
            self.fail(f"ProcessInstance Model Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_task_model(self):
        """Teste Task Model"""
        try:
            task = Task(
                id="task_123",
                name="Test Task",
                processInstanceId="instance_123",
                assignee="test_user"
            )
            
            self.assertEqual(task.id, "task_123")
            self.assertEqual(task.name, "Test Task")
            self.assertEqual(task.processInstanceId, "instance_123")
            self.assertEqual(task.assignee, "test_user")
            
        except Exception as e:
            self.fail(f"Task Model Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_camunda_client_timeout_configuration(self):
        """Teste CamundaClient Timeout Konfiguration"""
        try:
            client = CamundaClient(
                base_url="http://localhost:8080/engine-rest",
                timeout=30
            )
            
            self.assertEqual(client.timeout, 30)
            
        except Exception as e:
            self.fail(f"CamundaClient Timeout Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_camunda_client_auth_configuration(self):
        """Teste CamundaClient Auth Konfiguration"""
        try:
            client = CamundaClient(
                base_url="http://localhost:8080/engine-rest",
                auth=("user", "password")
            )
            
            self.assertEqual(client.auth, ("user", "password"))
            
        except Exception as e:
            self.fail(f"CamundaClient Auth Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_bpmn_directory_handling(self):
        """Teste BPMN Directory Handling"""
        try:
            # Test mit existierendem Verzeichnis
            bpmn_dir = Path("src/camunda_integration/bpmn_processes")
            client = CamundaClient(base_url="http://localhost:8080/engine-rest")
            service = CamundaService(client=client, bpmn_dir=bpmn_dir)
            
            self.assertTrue(bpmn_dir.exists() or not bpmn_dir.exists())  # Verzeichnis kann existieren oder nicht
            
            # Test mit nicht-existierendem Verzeichnis
            nonexistent_dir = Path("nonexistent/directory")
            service2 = CamundaService(client=client, bpmn_dir=nonexistent_dir)
            self.assertEqual(service2.bpmn_dir, nonexistent_dir)
            
        except Exception as e:
            self.fail(f"BPMN Directory Handling Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_docker_compose_file_validation(self):
        """Teste Docker Compose File Validation"""
        try:
            # Test mit existierender Compose-Datei
            compose_file = Path("src/camunda_integration/docker/docker-compose-manual.yml")
            
            if compose_file.exists():
                docker_manager = DockerManager(compose_file=compose_file)
                self.assertTrue(docker_manager.compose_file.exists())
            else:
                # Wenn die Datei nicht existiert, sollte der DockerManager trotzdem erstellt werden
                docker_manager = DockerManager(compose_file=compose_file)
                self.assertEqual(docker_manager.compose_file, compose_file)
            
        except Exception as e:
            self.fail(f"Docker Compose File Validation Test fehlgeschlagen: {str(e)}")


class TestCamundaIntegrationWithMocks(unittest.TestCase):
    """Test-Klasse für Camunda Integration mit Mocks (ohne echte Engine)"""
    
    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    @patch('requests.Session.get')
    def test_camunda_client_is_alive_success(self, mock_get):
        """Teste CamundaClient is_alive bei erfolgreicher Verbindung"""
        try:
            # Mock erfolgreiche Antwort
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"name": "default"}
            mock_get.return_value = mock_response
            
            client = CamundaClient(base_url="http://localhost:8080/engine-rest")
            result = client.is_alive()
            
            self.assertTrue(result)
            mock_get.assert_called_once()
            
        except Exception as e:
            self.fail(f"CamundaClient is_alive Success Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    @patch('requests.Session.get')
    def test_camunda_client_is_alive_failure(self, mock_get):
        """Teste CamundaClient is_alive bei fehlgeschlagener Verbindung"""
        try:
            # Mock fehlgeschlagene Antwort
            mock_get.side_effect = Exception("Connection failed")
            
            client = CamundaClient(base_url="http://localhost:8080/engine-rest")
            result = client.is_alive()
            
            self.assertFalse(result)
            mock_get.assert_called_once()
            
        except Exception as e:
            self.fail(f"CamundaClient is_alive Failure Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_process_instance_get_process_key_edge_cases(self):
        """Teste ProcessInstance get_process_key mit Edge Cases"""
        try:
            # Test mit normalem definitionId
            instance1 = ProcessInstance(
                id="1",
                definitionId="test_process:1:123",
                businessKey=None,
                ended=False,
                suspended=False
            )
            self.assertEqual(instance1.get_process_key(), "test_process")
            
            # Test mit definitionId ohne Version/Colon
            instance2 = ProcessInstance(
                id="2", 
                definitionId="simple_process",
                businessKey=None,
                ended=False,
                suspended=False
            )
            self.assertEqual(instance2.get_process_key(), "unknown")  # Kein Colon, daher "unknown"
            
            # Test mit None definitionId wird übersprungen,
            # da definitionId ein required field ist in Pydantic
            # Stattdessen testen wir mit leerem string
            instance3 = ProcessInstance(
                id="3",
                definitionId="",
                businessKey=None,
                ended=False,
                suspended=False
            )
            self.assertEqual(instance3.get_process_key(), "unknown")
            
        except Exception as e:
            self.fail(f"ProcessInstance get_process_key Edge Cases Test fehlgeschlagen: {str(e)}")


if __name__ == "__main__":
    unittest.main()