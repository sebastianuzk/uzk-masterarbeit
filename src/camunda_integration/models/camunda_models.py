
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CamundaVariable(BaseModel):
    value: Any
    type: Optional[str] = None
    valueInfo: Optional[Dict[str, Any]] = None


class ProcessDefinition(BaseModel):
    id: str
    key: str
    name: Optional[str] = None
    version: Optional[int] = None
    deployment_id: Optional[str] = Field(None, alias="deploymentId")
    suspended: Optional[bool] = False
    category: Optional[str] = None
    description: Optional[str] = None
    resource: Optional[str] = None
    diagram_resource: Optional[str] = Field(None, alias="diagramResource")
    tenant_id: Optional[str] = Field(None, alias="tenantId")
    
    model_config = {"populate_by_name": True}


class ProcessInstance(BaseModel):
    id: str
    definitionId: str
    processDefinitionKey: Optional[str] = None
    businessKey: Optional[str] = None
    ended: Optional[bool] = None
    suspended: Optional[bool] = None
    tenantId: Optional[str] = None
    
    # Property für UI-Kompatibilität
    @property
    def definition_id(self) -> str:
        return self.definitionId
    
    # Extract process key from definitionId if processDefinitionKey is missing
    def get_process_key(self) -> str:
        if self.processDefinitionKey:
            return self.processDefinitionKey
        # Extract from definitionId (format: "processKey:version:id")
        if self.definitionId and ":" in self.definitionId:
            return self.definitionId.split(":")[0]
        return "unknown"


class Task(BaseModel):
    id: str
    name: Optional[str]
    processInstanceId: str
    processDefinitionId: Optional[str] = None
    taskDefinitionKey: Optional[str] = None
    assignee: Optional[str] = None
    created: Optional[str] = None  # ISO datetime string
    due: Optional[str] = None
    followUp: Optional[str] = None
    delegationState: Optional[str] = None
    description: Optional[str] = None
    executionId: Optional[str] = None
    owner: Optional[str] = None
    parentTaskId: Optional[str] = None
    priority: Optional[int] = None
    suspended: Optional[bool] = False
    tenantId: Optional[str] = None
    
    @property
    def created_datetime(self):
        """Convert created string to datetime object"""
        if self.created:
            from datetime import datetime
            try:
                # Handle different datetime formats
                if 'T' in self.created:
                    return datetime.fromisoformat(self.created.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(self.created)
            except:
                return None
        return None


class ToolResult(BaseModel):
    success: bool
    message: str
    process_instance_id: Optional[str] = None
    next_tasks: List[Task] = Field(default_factory=list)
    process_status: Optional[str] = None
    need_input: bool = False
    missing: Optional[List[Dict[str, Any]]] = None
    details: Optional[Dict[str, Any]] = None
