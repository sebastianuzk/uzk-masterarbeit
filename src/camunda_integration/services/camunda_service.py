
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.camunda_integration.client.camunda_client import CamundaClient
from src.camunda_integration.models.camunda_models import ToolResult


@dataclass
class CamundaService:
    client: CamundaClient
    bpmn_dir: Path

    def is_engine_running(self) -> bool:
        """Check if Camunda engine is running and accessible"""
        return self.client.is_alive()

    def wait_for_engine(self, attempts: int = 30, sleep_seconds: float = 1.0) -> bool:
        import time
        for _ in range(attempts):
            if self.client.is_alive():
                return True
            time.sleep(sleep_seconds)
        return False

    def deploy_all(self) -> Dict[str, Any]:
        """Deploy all BPMN files from the configured directory"""
        try:
            result = self.client.deploy_directory(self.bpmn_dir)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def discover_processes(self) -> Dict[str, Any]:
        """Get all deployed process definitions from Camunda with form variables"""
        try:
            defs = self.client.get_process_definitions()
            result = []
            
            for d in defs:
                # Get form variables directly from Camunda API
                try:
                    form_vars = self.client.get_start_form_variables(d.id)
                    required_fields = []
                    
                    # Convert Camunda form variables to our format
                    for var_name, var_spec in form_vars.items():
                        required_fields.append({
                            "id": var_name,
                            "label": var_spec.get("label", var_name),
                            "type": var_spec.get("type", "string").lower(),
                            "required": var_spec.get("required", False),
                            "value": var_spec.get("value")
                        })
                        
                except Exception:
                    # If form variables can't be retrieved, continue without them
                    required_fields = []
                
                result.append({
                    "id": d.id,
                    "key": d.key,
                    "name": d.name,
                    "version": d.version,
                    "required_fields": required_fields,
                })
                
            return {"success": True, "processes": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_process(self, process_key: str, variables: Dict[str, Any], business_key: Optional[str] = None) -> ToolResult:
        """Start a process using Camunda-first approach with intelligent error handling"""
        try:
            # Let Camunda handle validation and start the process
            pi = self.client.start_process_by_key(process_key, variables, business_key)
            tasks = self.client.get_tasks_for_instance(pi.id)
            
            return ToolResult(
                success=True,
                message=f"Started process {process_key} -> instance {pi.id}",
                process_instance_id=pi.id,
                next_tasks=tasks,
                process_status="running" if tasks else "completed",
            )
            
        except Exception as e:
            # Transform Camunda errors into user-friendly format
            return self._handle_camunda_error(e, process_key)

    def start_process_instance(self, process_key: str, variables: Dict[str, Any], business_key: Optional[str] = None):
        """Start a process instance - UI compatible version"""
        return self.client.start_process_by_key(process_key, variables, business_key)

    def complete_task(self, task_id: str, variables: Optional[Dict[str, Any]] = None):
        """Complete a task - UI compatible version"""
        return self.client.complete_task(task_id, variables or {})

    def get_process_status(self, process_instance_id: str) -> ToolResult:
        tasks = self.client.get_tasks_for_instance(process_instance_id)
        
        # Enhance tasks with form variables
        enhanced_tasks = []
        for task in tasks:
            # Get form variables for each task
            try:
                form_vars = self.client.get_task_form_variables(task.id)
                # Add form variables to task (extend Task model or use dict)
                task_dict = task.model_dump()
                task_dict["form_variables"] = form_vars
                enhanced_tasks.append(task_dict)
            except Exception:
                # If form variables can't be retrieved, use task as-is
                enhanced_tasks.append(task.model_dump())
        
        status = "running" if tasks else "completed"
        return ToolResult(
            success=True,
            message=f"Instance {process_instance_id} status: {status}",
            process_instance_id=process_instance_id,
            next_tasks=enhanced_tasks,  # Now includes form variables
            process_status=status,
        )

    def complete_next_task(self, process_instance_id: str, variables: Optional[Dict[str, Any]] = None) -> ToolResult:
        """Complete the next task using Camunda-first approach"""
        try:
            tasks = self.client.get_tasks_for_instance(process_instance_id)
            if not tasks:
                return ToolResult(
                    success=False, 
                    message="No open user tasks", 
                    process_instance_id=process_instance_id
                )
            
            task = tasks[0]
            
            # Let Camunda handle task completion and validation
            self.client.complete_task(task.id, variables or {})
            
            # Get updated status
            remaining = self.client.get_tasks_for_instance(process_instance_id)
            status = "running" if remaining else "completed"
            
            return ToolResult(
                success=True,
                message=f"Completed task {task.name or task.id}",
                process_instance_id=process_instance_id,
                next_tasks=remaining,
                process_status=status,
            )
            
        except Exception as e:
            return self._handle_camunda_error(e, f"task completion for instance {process_instance_id}")

    def _handle_camunda_error(self, error: Exception, process_key: str) -> ToolResult:
        """Transform Camunda API errors into user-friendly ToolResult"""
        import requests
        
        if isinstance(error, requests.HTTPError):
            if error.response.status_code == 400:
                try:
                    error_details = error.response.json()
                    message = error_details.get("message", "Process start failed")
                    
                    # Try to extract missing field information
                    if "variable" in message.lower() or "required" in message.lower():
                        return ToolResult(
                            success=False,
                            message=f"Validation failed: {message}",
                            need_input=True,
                            missing=[{"reason": "validation_error", "details": message}]
                        )
                        
                except Exception:
                    pass
                    
                return ToolResult(
                    success=False, 
                    message=f"Invalid request for process {process_key}: {str(error)}"
                )
                
            elif error.response.status_code == 404:
                return ToolResult(
                    success=False,
                    message=f"Process '{process_key}' not found. Make sure it's deployed."
                )
                
        return ToolResult(
            success=False,
            message=f"Failed to start process {process_key}: {str(error)}"
        )
