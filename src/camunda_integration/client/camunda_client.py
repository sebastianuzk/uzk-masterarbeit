
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from camunda_models import (
    ProcessDefinition,
    ProcessInstance,
    Task,
)


@dataclass
class CamundaClient:
    """
    Lightweight Camunda 7 REST client.
    base_url example: http://localhost:8080/engine-rest
    """
    base_url: str
    timeout: int = 15
    auth: Optional[Tuple[str, str]] = None  # (user, pass) if Basic Auth

    def __post_init__(self):
        self._session = requests.Session()
        if self.auth:
            self._session.auth = self.auth
        self._session.headers.update({"Accept": "application/json"})

    # --------- Helpers ---------
    def _make_camunda_var(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, bool):
            return {"value": value, "type": "Boolean"}
        if isinstance(value, int):
            t = "Integer" if -2_147_483_648 <= value <= 2_147_483_647 else "Long"
            return {"value": value, "type": t}
        if isinstance(value, float):
            return {"value": value, "type": "Double"}
        if isinstance(value, str):
            return {"value": value, "type": "String"}
        if isinstance(value, (dict, list)):
            return {
                "value": json.dumps(value),
                "type": "Object",
                "valueInfo": {"serializationDataFormat": "application/json"},
            }
        return {"value": str(value), "type": "String"}

    def _var_map(self, variables: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {k: self._make_camunda_var(v) for k, v in (variables or {}).items()}

    # --------- Engine status ---------
    def is_alive(self) -> bool:
        try:
            r = self._session.get(f"{self.base_url}/engine", timeout=self.timeout)
            return r.ok
        except Exception:
            return False

    # --------- Deploy ---------
    def deploy_directory(self, directory: Path, deployment_name: str = "python-deploy") -> Dict[str, Any]:
        directory = Path(directory)
        assert directory.is_dir(), f"Not a directory: {directory}"

        bpmn_files = list(directory.glob("**/*.bpmn"))
        if not bpmn_files:
            return {"success": False, "message": "No .bpmn files found"}

        files = []
        for p in bpmn_files:
            files.append(("data", (p.name, open(p, "rb"), "application/xml")))

        data = {
            "deployment-name": deployment_name,
            "deployment-source": "python-client",
            "enable-duplicate-filtering": "true",
            "deploy-changed-only": "true",
        }
        url = f"{self.base_url}/deployment/create"
        r = self._session.post(url, files=files, data=data, timeout=self.timeout)
        for _, (_, fh, _) in files:
            try:
                fh.close()
            except Exception:
                pass
        r.raise_for_status()
        return r.json()

    # --------- Definitions ---------
    def get_process_definitions(self) -> List[ProcessDefinition]:
        r = self._session.get(f"{self.base_url}/process-definition", timeout=self.timeout)
        r.raise_for_status()
        return [ProcessDefinition(**x) for x in r.json()]

    def get_definition_by_key(self, key: str) -> Optional[ProcessDefinition]:
        r = self._session.get(f"{self.base_url}/process-definition/key/{key}", timeout=self.timeout)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return ProcessDefinition(**r.json())

    # --------- Forms (C7) ---------
    def get_start_form_variables(self, definition_id: str) -> Dict[str, Any]:
        r = self._session.get(
            f"{self.base_url}/process-definition/{definition_id}/form-variables",
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def get_task_form_variables(self, task_id: str) -> Dict[str, Any]:
        r = self._session.get(
            f"{self.base_url}/task/{task_id}/form-variables",
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    # --------- Start / Tasks ---------
    def start_process_by_key(
        self,
        key: str,
        variables: Optional[Dict[str, Any]] = None,
        business_key: Optional[str] = None,
    ) -> ProcessInstance:
        payload: Dict[str, Any] = {"variables": self._var_map(variables)}
        if business_key:
            payload["businessKey"] = business_key
        r = self._session.post(
            f"{self.base_url}/process-definition/key/{key}/start",
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return ProcessInstance(**r.json())

    def get_tasks_for_instance(self, process_instance_id: str) -> List[Task]:
        r = self._session.get(
            f"{self.base_url}/task",
            params={"processInstanceId": process_instance_id},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return [Task(**x) for x in r.json()]

    def complete_task(self, task_id: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"variables": self._var_map(variables)} if variables else {}
        r = self._session.post(
            f"{self.base_url}/task/{task_id}/complete",
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json() if r.text else {}
