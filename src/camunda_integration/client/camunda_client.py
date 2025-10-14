"""
Camunda REST API Client

Python client for Camunda Platform 7 REST API using pycamunda library.
Provides high-level interface for common Camunda operations.
"""

import logging
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
import requests
from datetime import datetime

try:
    import pycamunda
    # Note: pycamunda 0.6.1 has different API structure than newer versions
    # We'll use direct HTTP calls with requests for better compatibility
    PYCAMUNDA_AVAILABLE = True
except ImportError:
    # Fallback für development ohne pycamunda
    pycamunda = None
    PYCAMUNDA_AVAILABLE = False

from ..models.camunda_models import (
    CamundaEngine, ProcessDefinition, ProcessInstance, Task, 
    DeploymentResult, HistoryProcessInstance
)


logger = logging.getLogger(__name__)


class CamundaConnectionError(Exception):
    """Raised when connection to Camunda fails"""
    pass


class CamundaAPIError(Exception):
    """Raised when Camunda API returns an error"""
    pass


class CamundaClient:
    """
    High-level client for Camunda Platform 7 REST API
    
    Provides convenient methods for:
    - Process deployment
    - Process instance management  
    - Task management
    - Engine monitoring
    """
    
    def __init__(self, base_url: str = "http://localhost:8080/engine-rest"):
        """
        Initialize Camunda client
        
        Args:
            base_url: Camunda REST API base URL
        """
        self.base_url = base_url.rstrip('/')
        self._session = requests.Session()
        self._session.timeout = 30
        
        # For now, we use direct HTTP requests for better compatibility
        # pycamunda 0.6.1 has different API structure than documented
        self.engine_client = None
        logger.info("Using direct HTTP client for Camunda REST API")
    
    def is_connected(self) -> bool:
        """
        Check if Camunda engine is reachable
        
        Returns:
            True if connected, False otherwise
        """
        try:
            response = self._session.get(f"{self.base_url}/engine", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
    
    def get_engine_info(self) -> CamundaEngine:
        """
        Get Camunda engine information
        
        Returns:
            Engine information
            
        Raises:
            CamundaConnectionError: If connection fails
            CamundaAPIError: If API returns error
        """
        try:
            response = self._session.get(f"{self.base_url}/engine")
            response.raise_for_status()
            
            engines = response.json()
            if not engines:
                raise CamundaAPIError("No engines found")
            
            engine_data = engines[0]  # Use first engine
            return CamundaEngine(
                name=engine_data.get("name", "default"),
                version=self._get_version()
            )
        except requests.RequestException as e:
            raise CamundaConnectionError(f"Failed to connect to Camunda: {e}")
        except Exception as e:
            raise CamundaAPIError(f"Failed to get engine info: {e}")
    
    def _get_version(self) -> str:
        """Get Camunda version from version endpoint"""
        try:
            response = self._session.get(f"{self.base_url}/version")
            if response.status_code == 200:
                return response.json().get("version", "unknown")
        except:
            pass
        return "unknown"
    
    def deploy_bpmn(self, file_path: Union[str, Path], deployment_name: Optional[str] = None) -> DeploymentResult:
        """
        Deploy BPMN file to Camunda
        
        Args:
            file_path: Path to BPMN file
            deployment_name: Optional deployment name
            
        Returns:
            Deployment result
            
        Raises:
            CamundaAPIError: If deployment fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise CamundaAPIError(f"BPMN file not found: {file_path}")
        
        if not deployment_name:
            deployment_name = f"Deployment_{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Use proper multipart form data for Camunda deployment
            with open(file_path, 'rb') as f:
                files = {
                    'data': (file_path.name, f.read(), 'application/xml')
                }
                data = {
                    'deployment-name': deployment_name,
                    'deployment-source': 'python-client'
                }
                
                response = self._session.post(
                    f"{self.base_url}/deployment/create",
                    files=files,
                    data=data
                )
                
                # Debug information
                if response.status_code != 200:
                    logger.error(f"Deployment failed with status {response.status_code}")
                    logger.error(f"Response: {response.text}")
                
                response.raise_for_status()
                
                result = response.json()
                return DeploymentResult(**result)
                    
        except Exception as e:
            raise CamundaAPIError(f"Deployment failed: {e}")
    
    def get_process_definitions(self) -> List[ProcessDefinition]:
        """
        Get all process definitions
        
        Returns:
            List of process definitions
        """
        try:
            response = self._session.get(f"{self.base_url}/process-definition")
            response.raise_for_status()
            
            definitions = response.json()
            return [ProcessDefinition(**def_data) for def_data in definitions]
        except Exception as e:
            logger.error(f"Failed to get process definitions: {e}")
            return []
    
    def start_process(self, process_key: str, variables: Optional[Dict[str, Any]] = None, 
                     business_key: Optional[str] = None) -> ProcessInstance:
        """
        Start process instance
        
        Args:
            process_key: Process definition key
            variables: Process variables
            business_key: Optional business key
            
        Returns:
            Created process instance
            
        Raises:
            CamundaAPIError: If start fails
        """
        try:
            # Convert variables to Camunda format
            camunda_variables = {}
            if variables:
                for key, value in variables.items():
                    camunda_variables[key] = {
                        "value": value,
                        "type": self._get_variable_type(value)
                    }
            
            request_data = {
                "variables": camunda_variables
            }
            if business_key:
                request_data["businessKey"] = business_key
            
            response = self._session.post(
                f"{self.base_url}/process-definition/key/{process_key}/start",
                json=request_data
            )
            response.raise_for_status()
            
            instance_data = response.json()
            return ProcessInstance(**instance_data)
            
        except Exception as e:
            raise CamundaAPIError(f"Failed to start process: {e}")
    
    def get_tasks(self, assignee: Optional[str] = None, 
                  process_instance_id: Optional[str] = None) -> List[Task]:
        """
        Get tasks
        
        Args:
            assignee: Filter by assignee
            process_instance_id: Filter by process instance
            
        Returns:
            List of tasks
        """
        try:
            params = {}
            if assignee:
                params["assignee"] = assignee
            if process_instance_id:
                params["processInstanceId"] = process_instance_id
            
            response = self._session.get(f"{self.base_url}/task", params=params)
            response.raise_for_status()
            
            tasks = response.json()
            return [Task(**task_data) for task_data in tasks]
            
        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return []
    
    def complete_task(self, task_id: str, variables: Optional[Dict[str, Any]] = None) -> None:
        """
        Complete a task
        
        Args:
            task_id: Task ID
            variables: Task variables
            
        Raises:
            CamundaAPIError: If completion fails
        """
        try:
            # Convert variables to Camunda format
            camunda_variables = {}
            if variables:
                for key, value in variables.items():
                    camunda_variables[key] = {
                        "value": value,
                        "type": self._get_variable_type(value)
                    }
            
            request_data = {
                "variables": camunda_variables
            }
            
            response = self._session.post(
                f"{self.base_url}/task/{task_id}/complete",
                json=request_data
            )
            response.raise_for_status()
            
        except Exception as e:
            raise CamundaAPIError(f"Failed to complete task: {e}")
    
    def get_process_instances(self) -> List[ProcessInstance]:
        """
        Get all process instances
        
        Returns:
            List of process instances
        """
        try:
            response = self._session.get(f"{self.base_url}/process-instance")
            response.raise_for_status()
            
            instances = response.json()
            return [ProcessInstance(**inst_data) for inst_data in instances]
            
        except Exception as e:
            logger.error(f"Failed to get process instances: {e}")
            return []
    
    def get_history_process_instances(self, finished: bool = True) -> List[HistoryProcessInstance]:
        """
        Get historical process instances
        
        Args:
            finished: Filter for finished instances
            
        Returns:
            List of historical process instances
        """
        try:
            params = {}
            if finished:
                params["finished"] = "true"
            
            response = self._session.get(f"{self.base_url}/history/process-instance", params=params)
            response.raise_for_status()
            
            instances = response.json()
            return [HistoryProcessInstance(**inst_data) for inst_data in instances]
            
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    def delete_deployment(self, deployment_id: str, cascade: bool = True) -> None:
        """
        Delete deployment
        
        Args:
            deployment_id: Deployment ID
            cascade: Delete process instances too
            
        Raises:
            CamundaAPIError: If deletion fails
        """
        try:
            params = {"cascade": "true" if cascade else "false"}
            response = self._session.delete(
                f"{self.base_url}/deployment/{deployment_id}",
                params=params
            )
            response.raise_for_status()
            
        except Exception as e:
            raise CamundaAPIError(f"Failed to delete deployment: {e}")
    
    def _get_variable_type(self, value: Any) -> str:
        """Map Python type to Camunda variable type"""
        if isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, int):
            return "Integer" 
        elif isinstance(value, float):
            return "Double"
        elif isinstance(value, str):
            return "String"
        elif isinstance(value, dict):
            return "Json"
        elif isinstance(value, list):
            return "Json"
        else:
            return "String"