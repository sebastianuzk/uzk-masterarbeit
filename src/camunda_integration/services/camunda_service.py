
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.camunda_integration.client.camunda_client import CamundaClient
from src.camunda_integration.models.camunda_models import ToolResult
from src.camunda_integration.services.form_validator import load_required_fields_from_bpmn, validate_start_variables


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
        defs = self.client.get_process_definitions()
        # enrich with required fields from BPMN where filename matches key (common convention)
        key_to_fields: Dict[str, List[Dict[str, Any]]] = {}
        for p in self.bpmn_dir.glob("**/*.bpmn"):
            fields = load_required_fields_from_bpmn(p)
            if not fields:
                continue
            key_to_fields[p.stem] = fields
        result = []
        for d in defs:
            req = key_to_fields.get(d.key) or key_to_fields.get((d.name or "").strip().replace(" ", "_")) or []
            result.append({
                "id": d.id,
                "key": d.key,
                "name": d.name,
                "version": d.version,
                "required_fields": req,
            })
        return {"success": True, "processes": result}

    def start_process(self, process_key: str, variables: Dict[str, Any], business_key: Optional[str] = None) -> ToolResult:
        # validate against BPMN, if file exists
        bpmn_path = self._find_bpmn_for_key(process_key)
        if bpmn_path:
            ok, msg, missing = validate_start_variables(bpmn_path, variables or {})
            if not ok:
                return ToolResult(
                    success=False,
                    message=f"Validation failed: {msg}",
                    need_input=True,
                    missing=missing,
                )
        # start
        pi = self.client.start_process_by_key(process_key, variables, business_key)
        tasks = self.client.get_tasks_for_instance(pi.id)
        return ToolResult(
            success=True,
            message=f"Started process {process_key} -> instance {pi.id}",
            process_instance_id=pi.id,
            next_tasks=tasks,
            process_status="running" if tasks else "completed",
        )

    def start_process_instance(self, process_key: str, variables: Dict[str, Any], business_key: Optional[str] = None):
        """Start a process instance - UI compatible version"""
        return self.client.start_process_by_key(process_key, variables, business_key)

    def complete_task(self, task_id: str, variables: Optional[Dict[str, Any]] = None):
        """Complete a task - UI compatible version"""
        return self.client.complete_task(task_id, variables or {})

    def get_process_status(self, process_instance_id: str) -> ToolResult:
        tasks = self.client.get_tasks_for_instance(process_instance_id)
        status = "running" if tasks else "completed"
        return ToolResult(
            success=True,
            message=f"Instance {process_instance_id} status: {status}",
            process_instance_id=process_instance_id,
            next_tasks=tasks,
            process_status=status,
        )

    def complete_next_task(self, process_instance_id: str, variables: Optional[Dict[str, Any]] = None) -> ToolResult:
        tasks = self.client.get_tasks_for_instance(process_instance_id)
        if not tasks:
            return ToolResult(success=False, message="No open user tasks", process_instance_id=process_instance_id)
        task = tasks[0]
        # (Optional) fetch task form variables and ensure provided variables satisfy required ones
        try:
            form_vars = self.client.get_task_form_variables(task.id)
            missing = []
            if form_vars:
                provided = variables or {}
                for k, spec in form_vars.items():
                    if spec.get("readable", True) and spec.get("required", False):
                        if k not in provided or provided.get(k) in (None, ""):
                            missing.append({"id": k, "label": spec.get("label", k), "reason": "required"})
                if missing:
                    return ToolResult(success=False, message="Missing variables for task", need_input=True, missing=missing, process_instance_id=process_instance_id)
        except Exception:
            # If form retrieval fails, proceed best-effort
            pass
        self.client.complete_task(task.id, variables)
        # refresh
        remaining = self.client.get_tasks_for_instance(process_instance_id)
        status = "running" if remaining else "completed"
        return ToolResult(
            success=True,
            message=f"Completed task {task.name or task.id}",
            process_instance_id=process_instance_id,
            next_tasks=remaining,
            process_status=status,
        )

    def get_process_definitions(self) -> List:
        """Get all process definitions as objects"""
        try:
            return self.client.get_process_definitions()
        except Exception as e:
            return []

    def get_engine_status(self) -> Dict[str, Any]:
        """Get engine status information"""
        try:
            is_running = self.client.is_alive()
            if is_running:
                processes = self.client.get_process_definitions()
                instances = self.client.get_process_instances()
                tasks = self.get_tasks()
                return {
                    "running": True,
                    "engine_info": {
                        "name": "Camunda Platform 7",
                        "version": "7.21.0"
                    },
                    "process_definitions": len(processes),
                    "active_instances": len(instances),
                    "open_tasks": len(tasks)
                }
            else:
                return {
                    "running": False,
                    "error": "Engine not reachable"
                }
        except Exception as e:
            return {
                "running": False,
                "error": str(e)
            }

    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get all active tasks"""
        try:
            # Get all process instances
            instances = self.client.get_process_instances()
            all_tasks = []
            
            for instance in instances:
                tasks = self.client.get_tasks_for_instance(instance.id)
                for task in tasks:
                    all_tasks.append({
                        "id": task.id,
                        "name": task.name,
                        "processInstanceId": task.processInstanceId,
                        "taskDefinitionKey": task.taskDefinitionKey,
                        "assignee": task.assignee
                    })
            
            return all_tasks
        except Exception as e:
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        try:
            processes = self.client.get_process_definitions()
            instances = self.client.get_process_instances()
            
            # Count instances by process key
            by_process = {}
            for instance in instances:
                key = instance.get_process_key()  # Use the new method
                if key not in by_process:
                    by_process[key] = {"active": 0, "completed": 0}
                by_process[key]["active"] += 1
            
            # Get all tasks
            all_tasks = self.get_tasks()
            
            return {
                "process_definitions": len(processes),
                "active_instances": len(instances),
                "completed_instances": 0,  # TODO: Implement completed instances tracking
                "open_tasks": len(all_tasks),
                "by_process": by_process,
                "engine_running": self.client.is_alive()
            }
        except Exception as e:
            return {
                "process_definitions": 0,
                "active_instances": 0, 
                "completed_instances": 0,
                "open_tasks": 0,
                "by_process": {},
                "engine_running": False,
                "error": str(e)
            }

    def get_active_processes(self):
        """Get active process instances"""
        try:
            return self.client.get_process_instances()
        except Exception as e:
            return []

    def get_process_history(self):
        """Get process history (completed instances)"""
        try:
            # Get historical process instances
            url = f"{self.client.base_url}/history/process-instance"
            params = {
                "finished": "true",
                "sortBy": "startTime",
                "sortOrder": "desc",
                "maxResults": 10
            }
            response = self.client._session.get(url, params=params, timeout=self.client.timeout)
            response.raise_for_status()
            
            history_data = response.json()
            from src.camunda_integration.models.camunda_models import ProcessInstance
            from datetime import datetime
            
            history_instances = []
            for item in history_data:
                # Convert to ProcessInstance-like object for consistency
                instance = ProcessInstance(
                    id=item.get("id"),
                    definitionId=item.get("processDefinitionId", ""),
                    processDefinitionKey=item.get("processDefinitionKey"),
                    businessKey=item.get("businessKey")
                )
                # Add history-specific fields
                instance.start_time = datetime.fromisoformat(item.get("startTime", "").replace("Z", "+00:00")) if item.get("startTime") else None
                instance.end_time = datetime.fromisoformat(item.get("endTime", "").replace("Z", "+00:00")) if item.get("endTime") else None
                instance.duration_in_millis = item.get("durationInMillis")
                instance.state = item.get("state", "COMPLETED")
                
                history_instances.append(instance)
            
            return history_instances
        except Exception as e:
            return []

    def _find_bpmn_for_key(self, key: str) -> Optional[Path]:
        # heuristic: filename stem equals key
        for p in self.bpmn_dir.glob("**/*.bpmn"):
            if p.stem == key:
                return p
        return None
