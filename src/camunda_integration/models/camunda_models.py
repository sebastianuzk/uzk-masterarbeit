
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


class ProcessInstance(BaseModel):
    id: str
    definitionId: str
    businessKey: Optional[str] = None


class Task(BaseModel):
    id: str
    name: Optional[str]
    processInstanceId: str
    taskDefinitionKey: Optional[str] = None
    assignee: Optional[str] = None


class ToolResult(BaseModel):
    success: bool
    message: str
    process_instance_id: Optional[str] = None
    next_tasks: List[Task] = Field(default_factory=list)
    process_status: Optional[str] = None
    need_input: bool = False
    missing: Optional[List[Dict[str, Any]]] = None
    details: Optional[Dict[str, Any]] = None
