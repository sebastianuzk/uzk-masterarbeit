"""
Camunda Service Layer

High-level service for Camunda operations with automatic deployment,
process management, and task handling. Provides similar interface to
the custom BPMN engine for easy migration.
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import os
import time
from datetime import datetime

from ..client.camunda_client import CamundaClient, CamundaConnectionError, CamundaAPIError
from ..models.camunda_models import (
    ProcessDefinition, ProcessInstance, Task, DeploymentResult,
    HistoryProcessInstance
)


logger = logging.getLogger(__name__)


class CamundaService:
    """
    High-level service for Camunda Platform 7 operations
    
    Provides:
    - Automatic BPMN deployment from directory
    - Process instance management
    - Task management
    - Engine status monitoring
    - Similar interface to custom BPMN engine
    """
    
    def __init__(self, base_url: str = "http://localhost:8080/engine-rest",
                 auto_deploy_dir: Optional[str] = None):
        """
        Initialize Camunda service
        
        Args:
            base_url: Camunda REST API URL
            auto_deploy_dir: Directory to auto-deploy BPMN files from
        """
        self.client = CamundaClient(base_url)
        self.auto_deploy_dir = auto_deploy_dir
        self._deployed_files: Dict[str, str] = {}  # file_path -> deployment_id
        
    def is_engine_running(self) -> bool:
        """
        Check if Camunda engine is running and accessible
        
        Returns:
            True if engine is running, False otherwise
        """
        return self.client.is_connected()
    
    def wait_for_engine(self, timeout: int = 60) -> bool:
        """
        Wait for Camunda engine to be ready
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            True if engine becomes ready, False on timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_engine_running():
                logger.info("Camunda engine is ready")
                return True
            logger.info("Waiting for Camunda engine...")
            time.sleep(2)
        
        logger.error(f"Camunda engine not ready after {timeout} seconds")
        return False
    
    def get_engine_status(self) -> Dict[str, Any]:
        """
        Get comprehensive engine status
        
        Returns:
            Engine status dictionary
        """
        try:
            if not self.is_engine_running():
                return {
                    "running": False,
                    "error": "Engine not reachable",
                    "engine_info": None,
                    "process_definitions": 0,
                    "active_instances": 0,
                    "open_tasks": 0
                }
            
            engine_info = self.client.get_engine_info()
            process_definitions = self.client.get_process_definitions()
            process_instances = self.client.get_process_instances()
            tasks = self.client.get_tasks()
            
            return {
                "running": True,
                "engine_info": {
                    "name": engine_info.name,
                    "version": engine_info.version
                },
                "process_definitions": len(process_definitions),
                "active_instances": len(process_instances),
                "open_tasks": len(tasks),
                "auto_deploy_dir": self.auto_deploy_dir,
                "deployed_files": len(self._deployed_files)
            }
            
        except Exception as e:
            logger.error(f"Failed to get engine status: {e}")
            return {
                "running": False,
                "error": str(e),
                "engine_info": None,
                "process_definitions": 0,
                "active_instances": 0,
                "open_tasks": 0
            }
    
    def deploy_from_directory(self, directory: Optional[str] = None) -> List[DeploymentResult]:
        """
        Deploy all BPMN files from directory
        
        Args:
            directory: Directory path (uses auto_deploy_dir if None)
            
        Returns:
            List of deployment results
            
        Raises:
            CamundaAPIError: If deployment fails
        """
        if not directory:
            directory = self.auto_deploy_dir
        
        if not directory:
            raise CamundaAPIError("No deployment directory specified")
        
        directory_path = Path(directory)
        if not directory_path.exists():
            raise CamundaAPIError(f"Directory not found: {directory}")
        
        results = []
        bpmn_files = list(directory_path.glob("*.bpmn"))
        
        if not bpmn_files:
            logger.warning(f"No BPMN files found in {directory}")
            return results
        
        for bpmn_file in bpmn_files:
            try:
                logger.info(f"Deploying {bpmn_file.name}...")
                result = self.client.deploy_bpmn(bpmn_file)
                self._deployed_files[str(bpmn_file)] = result.id
                results.append(result)
                logger.info(f"Successfully deployed {bpmn_file.name} (ID: {result.id})")
                
            except Exception as e:
                logger.error(f"Failed to deploy {bpmn_file.name}: {e}")
                # Continue with other files
        
        return results
    
    def deploy_file(self, file_path: str, deployment_name: Optional[str] = None) -> DeploymentResult:
        """
        Deploy single BPMN file
        
        Args:
            file_path: Path to BPMN file
            deployment_name: Optional deployment name
            
        Returns:
            Deployment result
        """
        result = self.client.deploy_bpmn(file_path, deployment_name)
        self._deployed_files[file_path] = result.id
        return result
    
    def get_process_definitions(self) -> List[ProcessDefinition]:
        """
        Get all deployed process definitions
        
        Returns:
            List of process definitions
        """
        return self.client.get_process_definitions()
    
    def start_process(self, process_key: str, variables: Optional[Dict[str, Any]] = None,
                     business_key: Optional[str] = None) -> ProcessInstance:
        """
        Start a process instance
        
        Args:
            process_key: Process definition key
            variables: Process variables
            business_key: Business key for the instance
            
        Returns:
            Created process instance
        """
        return self.client.start_process(process_key, variables, business_key)
    
    def get_active_processes(self) -> List[ProcessInstance]:
        """
        Get all active process instances
        
        Returns:
            List of active process instances
        """
        return self.client.get_process_instances()
    
    def get_process_history(self) -> List[HistoryProcessInstance]:
        """
        Get process execution history
        
        Returns:
            List of historical process instances
        """
        return self.client.get_history_process_instances()
    
    def get_tasks(self, assignee: Optional[str] = None,
                  process_instance_id: Optional[str] = None) -> List[Task]:
        """
        Get tasks (optionally filtered)
        
        Args:
            assignee: Filter by assignee
            process_instance_id: Filter by process instance
            
        Returns:
            List of tasks
        """
        return self.client.get_tasks(assignee, process_instance_id)
    
    def get_user_tasks(self, user_id: str) -> List[Task]:
        """
        Get tasks assigned to specific user
        
        Args:
            user_id: User ID
            
        Returns:
            List of user's tasks
        """
        return self.get_tasks(assignee=user_id)
    
    def complete_task(self, task_id: str, variables: Optional[Dict[str, Any]] = None) -> None:
        """
        Complete a task
        
        Args:
            task_id: Task ID
            variables: Task completion variables
        """
        self.client.complete_task(task_id, variables)
    
    def get_task_details(self, task_id: str) -> Optional[Task]:
        """
        Get details for a specific task
        
        Args:
            task_id: Task ID
            
        Returns:
            Task details or None if not found
        """
        all_tasks = self.get_tasks()
        for task in all_tasks:
            if task.id == task_id:
                return task
        return None
    
    def cleanup_deployments(self, keep_latest: int = 5) -> List[str]:
        """
        Cleanup old deployments, keeping only the latest versions
        
        Args:
            keep_latest: Number of latest deployments to keep per process
            
        Returns:
            List of deleted deployment IDs
        """
        try:
            process_definitions = self.get_process_definitions()
            
            # Group by process key
            by_key: Dict[str, List[ProcessDefinition]] = {}
            for pd in process_definitions:
                if pd.key not in by_key:
                    by_key[pd.key] = []
                by_key[pd.key].append(pd)
            
            deleted_ids = []
            
            for key, definitions in by_key.items():
                # Sort by version descending (newest first)
                definitions.sort(key=lambda x: x.version, reverse=True)
                
                # Keep only the latest versions
                to_delete = definitions[keep_latest:]
                
                for pd in to_delete:
                    try:
                        self.client.delete_deployment(pd.deployment_id, cascade=True)
                        deleted_ids.append(pd.deployment_id)
                        logger.info(f"Deleted old deployment {pd.deployment_id} for {key} v{pd.version}")
                    except Exception as e:
                        logger.error(f"Failed to delete deployment {pd.deployment_id}: {e}")
            
            return deleted_ids
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return []
    
    def auto_deploy_and_start(self) -> Tuple[List[DeploymentResult], List[ProcessInstance]]:
        """
        Convenience method: Deploy BPMN files and start default processes
        
        Returns:
            Tuple of (deployment_results, started_instances)
        """
        # Deploy all BPMN files
        deployments = []
        if self.auto_deploy_dir:
            deployments = self.deploy_from_directory()
        
        # Auto-start processes if configured (optional)
        instances = []
        # This could be extended to auto-start certain processes
        
        return deployments, instances
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive Camunda statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            process_definitions = self.get_process_definitions()
            active_instances = self.get_active_processes()
            history = self.get_process_history()
            tasks = self.get_tasks()
            
            # Group by process key
            by_key: Dict[str, Dict[str, int]] = {}
            for instance in active_instances:
                key = instance.definition_id.split(':')[0]  # Extract key from ID
                if key not in by_key:
                    by_key[key] = {"active": 0, "completed": 0}
                by_key[key]["active"] += 1
            
            for hist in history:
                key = hist.process_definition_key
                if key not in by_key:
                    by_key[key] = {"active": 0, "completed": 0}
                by_key[key]["completed"] += 1
            
            return {
                "process_definitions": len(process_definitions),
                "active_instances": len(active_instances),
                "completed_instances": len(history),
                "open_tasks": len(tasks),
                "by_process": by_key,
                "engine_status": self.get_engine_status()
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "error": str(e),
                "process_definitions": 0,
                "active_instances": 0,
                "completed_instances": 0,
                "open_tasks": 0,
                "by_process": {},
                "engine_status": {"running": False}
            }