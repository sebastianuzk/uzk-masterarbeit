
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from camunda_client import CamundaClient
from camunda_models import ToolResult
from form_validator import load_required_fields_from_bpmn, validate_start_variables


@dataclass
class CamundaService:
    client: CamundaClient
    bpmn_dir: Path

    def wait_for_engine(self, attempts: int = 30, sleep_seconds: float = 1.0) -> bool:
        import time
        for _ in range(attempts):
            if self.client.is_alive():
                return True
            time.sleep(sleep_seconds)
        return False

    def deploy_all(self) -> Dict[str, Any]:
        return self.client.deploy_directory(self.bpmn_dir)

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

    def start_process(self, process_key: str, variables: Dict[str, Any]) -> ToolResult:
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
        pi = self.client.start_process_by_key(process_key, variables)
        tasks = self.client.get_tasks_for_instance(pi.id)
        return ToolResult(
            success=True,
            message=f"Started process {process_key} -> instance {pi.id}",
            process_instance_id=pi.id,
            next_tasks=tasks,
            process_status="running" if tasks else "completed",
        )

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

    def _find_bpmn_for_key(self, key: str) -> Optional[Path]:
        # heuristic: filename stem equals key
        for p in self.bpmn_dir.glob("**/*.bpmn"):
            if p.stem == key:
                return p
        return None
