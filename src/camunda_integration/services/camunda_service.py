
import xml.etree.ElementTree as ET
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

    def _get_task_descriptions(self, process_key: str) -> Dict[str, Dict[str, Any]]:
        """Extract task descriptions and documentation from BPMN file"""
        try:
            # Find BPMN file for this process
            bpmn_file = None
            for file in self.bpmn_dir.glob("*.bpmn"):
                tree = ET.parse(file)
                root = tree.getroot()
                
                # Find the process element with matching id
                process_elem = root.find(f".//*[@id='{process_key}']")
                if process_elem is not None:
                    bpmn_file = file
                    break
            
            if not bpmn_file:
                return {}
            
            # Parse the BPMN file
            tree = ET.parse(bpmn_file)
            root = tree.getroot()
            
            # Define namespaces
            namespaces = {
                'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
                'camunda': 'http://camunda.org/schema/1.0/bpmn'
            }
            
            descriptions = {}
            
            # Extract all tasks with their documentation and properties
            task_types = ['userTask', 'serviceTask', 'scriptTask', 'sendTask', 'receiveTask', 'manualTask', 'businessRuleTask']
            
            for task_type in task_types:
                tasks = root.findall(f".//bpmn:{task_type}", namespaces)
                
                for task in tasks:
                    task_id = task.get('id')
                    task_name = task.get('name', task_id)
                    
                    task_info = {
                        'id': task_id,
                        'name': task_name,
                        'type': task_type,
                        'documentation': None,
                        'description': None,
                        'instructions': None,
                        'category': None,
                        'form_fields': {}
                    }
                    
                    # Extract documentation
                    doc_elem = task.find('bpmn:documentation', namespaces)
                    if doc_elem is not None and doc_elem.text:
                        task_info['documentation'] = doc_elem.text.strip()
                    
                    # Extract Camunda properties
                    ext_elements = task.find('bpmn:extensionElements', namespaces)
                    if ext_elements is not None:
                        properties = ext_elements.find('camunda:properties', namespaces)
                        if properties is not None:
                            for prop in properties.findall('camunda:property', namespaces):
                                prop_name = prop.get('name')
                                prop_value = prop.get('value')
                                if prop_name in ['description', 'instructions', 'category']:
                                    task_info[prop_name] = prop_value
                        
                        # Extract form field descriptions
                        form_data = ext_elements.find('camunda:formData', namespaces)
                        if form_data is not None:
                            for field in form_data.findall('camunda:formField', namespaces):
                                field_id = field.get('id')
                                field_label = field.get('label', field_id)
                                field_type = field.get('type', 'string')
                                
                                field_info = {
                                    'id': field_id,
                                    'label': field_label,
                                    'type': field_type,
                                    'description': None,
                                    'helptext': None,
                                    'placeholder': None
                                }
                                
                                # Extract field properties
                                field_props = field.find('camunda:properties', namespaces)
                                if field_props is not None:
                                    for prop in field_props.findall('camunda:property', namespaces):
                                        prop_name = prop.get('id', prop.get('name'))
                                        prop_value = prop.get('value')
                                        if prop_name in ['description', 'helptext', 'placeholder']:
                                            field_info[prop_name] = prop_value
                                
                                task_info['form_fields'][field_id] = field_info
                    
                    descriptions[task_id] = task_info
            
            return descriptions
            
        except Exception as e:
            print(f"Error extracting task descriptions: {e}")
            return {}

    def get_task_info_with_descriptions(self, process_key: str) -> Dict[str, Any]:
        """Get detailed task information including descriptions for a process"""
        try:
            # Get basic process definition
            process_def = self.client.get_definition_by_key(process_key)
            if not process_def:
                return {"success": False, "error": f"Process '{process_key}' not found"}
            
            # Get task descriptions from BPMN
            task_descriptions = self._get_task_descriptions(process_key)
            
            # Get current tasks if process is running
            current_tasks = []
            try:
                # Get all instances of this process
                instances = self.client.get_history_process_instances(process_key)
                for instance in instances:
                    if instance.get('state') == 'ACTIVE':  # Running instances
                        tasks = self.client.get_tasks_for_instance(instance['id'])
                        current_tasks.extend(tasks)
            except Exception:
                pass  # Ignore if no running instances
            
            result = {
                "success": True,
                "process": {
                    "key": process_key,
                    "name": process_def.name,
                    "version": process_def.version,
                    "definition_id": process_def.id
                },
                "task_descriptions": task_descriptions,
                "current_tasks": current_tasks
            }
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_required_fields(self, definition_id: str) -> List[Dict[str, Any]]:
        """Get required fields for a process definition from Camunda API"""
        try:
            # Use standard Camunda API first
            form_vars = self.client.get_start_form_variables(definition_id)
            
            # If API returns results but without required info, use XML extraction
            if form_vars:
                # Check if any field has required information
                has_required_info = any(
                    field_spec.get("required") is not None 
                    for field_spec in form_vars.values()
                )
                
                if has_required_info:
                    # Use API results
                    required_fields = []
                    for var_name, var_spec in form_vars.items():
                        required_fields.append({
                            "id": var_name,
                            "label": var_spec.get("label", var_name),
                            "type": var_spec.get("type", "string").lower(),
                            "required": var_spec.get("required", False)
                        })
                    return required_fields
            
            # AUSNAHME: Für embedded forms nutze XML-Extraktion
            # (API liefert Fields ohne required-Information)
            xml_response = self.client._session.get(
                f"{self.client.base_url}/process-definition/{definition_id}/xml",
                timeout=self.client.timeout
            )
            if xml_response.status_code == 200:
                xml_data = xml_response.json().get("bpmn20Xml", "")
                required_fields = self._extract_embedded_form_fields(xml_data)
                if required_fields:
                    return required_fields
            
            # Fallback: Nutze API-Results ohne required-Info
            if form_vars:
                required_fields = []
                for var_name, var_spec in form_vars.items():
                    required_fields.append({
                        "id": var_name,
                        "label": var_spec.get("label", var_name),
                        "type": var_spec.get("type", "string").lower(),
                        "required": False  # Default für unbekannte Fields
                    })
                return required_fields
            
            return []
            
        except Exception:
            return []

    def _extract_embedded_form_fields(self, xml_data: str) -> List[Dict[str, Any]]:
        """AUSNAHME: Extrahiere embedded form fields aus BPMN XML (nur für Camunda 7 embedded forms)"""
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_data)
            namespaces = {
                'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
                'camunda': 'http://camunda.org/schema/1.0/bpmn'
            }
            
            form_fields = []
            
            # Find start events with embedded form data
            start_events = root.findall('.//bpmn:startEvent', namespaces)
            for start_event in start_events:
                form_data = start_event.find('.//camunda:formData', namespaces)
                if form_data is not None:
                    for field in form_data.findall('camunda:formField', namespaces):
                        field_id = field.get('id')
                        field_type = field.get('type', 'string')
                        field_label = field.get('label', field_id)
                        
                        # Check if field is required
                        required = False
                        validation = field.find('camunda:validation', namespaces)
                        if validation is not None:
                            for constraint in validation.findall('camunda:constraint', namespaces):
                                if constraint.get('name') == 'required':
                                    required = True
                                    break
                        
                        form_fields.append({
                            "id": field_id,
                            "label": field_label,
                            "type": field_type.lower(),
                            "required": required
                        })
            
            return form_fields
            
        except Exception:
            return []

    def discover_processes(self) -> Dict[str, Any]:
        """Get all deployed process definitions from Camunda with required fields"""
        try:
            defs = self.client.get_process_definitions()
            result = []
            
            for d in defs:
                # Use the validator method to get required fields
                required_fields = self._get_required_fields(d.id)
                
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
        """Start a process with validation for required fields"""
        try:
            # Get process definition
            process_def = self.client.get_definition_by_key(process_key)
            if not process_def:
                return ToolResult(
                    success=False,
                    message=f"Process '{process_key}' not found. Make sure it's deployed."
                )
            
            # Get required fields (includes embedded form extraction as exception)
            required_fields = self._get_required_fields(process_def.id)
            
            # Validate required fields if any are defined
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field.get("required", False):
                        field_id = field["id"]
                        if field_id not in variables or not variables[field_id] or str(variables[field_id]).strip() == "":
                            missing_fields.append({
                                "id": field_id,
                                "label": field.get("label", field_id),
                                "type": field.get("type", "string"),
                                "required": True,
                                "reason": "missing_required_field"
                            })
                
                if missing_fields:
                    return ToolResult(
                        success=False,
                        message=f"Validation failed: {len(missing_fields)} required fields missing",
                        need_input=True,
                        missing=missing_fields
                    )
            
            # Start the process
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
            return self._handle_camunda_error(e, process_key)

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
            return self.client.get_history_process_instances()
        except Exception as e:
            return []

    def _find_bpmn_for_key(self, key: str) -> Optional[Path]:
        # heuristic: filename stem equals key
        for p in self.bpmn_dir.glob("**/*.bpmn"):
            if p.stem == key:
                return p
        return None

    def _handle_camunda_error(self, error: Exception, process_key: str) -> ToolResult:
        """Transform Camunda API errors into user-friendly ToolResult"""
        import requests
        
        if isinstance(error, requests.HTTPError):
            if error.response.status_code == 400:
                try:
                    error_details = error.response.json()
                    message = error_details.get("message", "Process start failed")
                    
                    return ToolResult(
                        success=False,
                        message=f"Bad request for process {process_key}: {message}",
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
