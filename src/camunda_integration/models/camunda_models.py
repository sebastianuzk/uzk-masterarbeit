"""
Camunda Data Models

Pydantic models for Camunda Platform 7 API responses and requests.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field


class CamundaEngine(BaseModel):
    """Camunda Engine information"""
    name: str
    version: str


class ProcessDefinition(BaseModel):
    """BPMN Process Definition"""
    id: str
    key: str
    category: Optional[str] = None
    description: Optional[str] = None
    name: Optional[str] = None
    version: int
    resource: Optional[str] = None
    deployment_id: str = Field(alias="deploymentId")
    diagram: Optional[str] = None
    suspended: bool
    tenant_id: Optional[str] = Field(alias="tenantId", default=None)
    version_tag: Optional[str] = Field(alias="versionTag", default=None)


class ProcessInstance(BaseModel):
    """Running Process Instance"""
    id: str
    definition_id: str = Field(alias="definitionId")
    business_key: Optional[str] = Field(alias="businessKey", default=None)
    case_instance_id: Optional[str] = Field(alias="caseInstanceId", default=None)
    ended: bool
    suspended: bool
    tenant_id: Optional[str] = Field(alias="tenantId", default=None)


class Task(BaseModel):
    """User Task"""
    id: str
    name: Optional[str] = None
    assignee: Optional[str] = None
    created: datetime
    due: Optional[datetime] = None
    follow_up: Optional[datetime] = Field(alias="followUp", default=None)
    delegation_state: Optional[str] = Field(alias="delegationState", default=None)
    description: Optional[str] = None
    execution_id: str = Field(alias="executionId")
    owner: Optional[str] = None
    parent_task_id: Optional[str] = Field(alias="parentTaskId", default=None)
    priority: int
    process_definition_id: str = Field(alias="processDefinitionId")
    process_instance_id: str = Field(alias="processInstanceId")
    task_definition_key: str = Field(alias="taskDefinitionKey")
    case_execution_id: Optional[str] = Field(alias="caseExecutionId", default=None)
    case_instance_id: Optional[str] = Field(alias="caseInstanceId", default=None)
    case_definition_id: Optional[str] = Field(alias="caseDefinitionId", default=None)
    suspended: bool
    form_key: Optional[str] = Field(alias="formKey", default=None)
    tenant_id: Optional[str] = Field(alias="tenantId", default=None)


class Deployment(BaseModel):
    """BPMN Deployment"""
    id: str
    name: Optional[str] = None
    deployment_time: datetime = Field(alias="deploymentTime")
    source: Optional[str] = None
    tenant_id: Optional[str] = Field(alias="tenantId", default=None)


class Variable(BaseModel):
    """Process Variable"""
    value: Any
    type: str
    value_info: Dict[str, Any] = Field(alias="valueInfo", default_factory=dict)


class TaskForm(BaseModel):
    """Task Form Data"""
    key: str
    context_path: str = Field(alias="contextPath")


class CamundaError(BaseModel):
    """Camunda API Error Response"""
    type: str
    message: str


class StartProcessRequest(BaseModel):
    """Request to start a process instance"""
    variables: Dict[str, Variable] = Field(default_factory=dict)
    business_key: Optional[str] = Field(alias="businessKey", default=None)


class CompleteTaskRequest(BaseModel):
    """Request to complete a task"""
    variables: Dict[str, Variable] = Field(default_factory=dict)


class DeploymentResult(BaseModel):
    """Result of a deployment operation"""
    id: str
    name: Optional[str] = None
    deployment_time: datetime = Field(alias="deploymentTime")
    source: Optional[str] = None
    tenant_id: Optional[str] = Field(alias="tenantId", default=None)
    deployed_process_definitions: Optional[Dict[str, ProcessDefinition]] = Field(
        alias="deployedProcessDefinitions", default_factory=dict
    )
    deployed_case_definitions: Optional[Dict[str, Any]] = Field(
        alias="deployedCaseDefinitions", default_factory=dict
    )
    deployed_decision_definitions: Optional[Dict[str, Any]] = Field(
        alias="deployedDecisionDefinitions", default_factory=dict
    )
    deployed_decision_requirements_definitions: Optional[Dict[str, Any]] = Field(
        alias="deployedDecisionRequirementsDefinitions", default_factory=dict
    )


class HistoryProcessInstance(BaseModel):
    """Historical Process Instance"""
    id: str
    process_definition_id: str = Field(alias="processDefinitionId")
    process_definition_key: str = Field(alias="processDefinitionKey")
    process_definition_name: Optional[str] = Field(alias="processDefinitionName", default=None)
    process_definition_version: int = Field(alias="processDefinitionVersion")
    start_time: datetime = Field(alias="startTime")
    end_time: Optional[datetime] = Field(alias="endTime", default=None)
    duration_in_millis: Optional[int] = Field(alias="durationInMillis", default=None)
    start_user_id: Optional[str] = Field(alias="startUserId", default=None)
    start_activity_id: str = Field(alias="startActivityId")
    end_activity_id: Optional[str] = Field(alias="endActivityId", default=None)
    super_process_instance_id: Optional[str] = Field(alias="superProcessInstanceId", default=None)
    super_case_instance_id: Optional[str] = Field(alias="superCaseInstanceId", default=None)
    case_instance_id: Optional[str] = Field(alias="caseInstanceId", default=None)
    business_key: Optional[str] = Field(alias="businessKey", default=None)
    delete_reason: Optional[str] = Field(alias="deleteReason", default=None)
    tenant_id: Optional[str] = Field(alias="tenantId", default=None)
    state: str = "COMPLETED"  # ACTIVE, COMPLETED, EXTERNALLY_TERMINATED, INTERNALLY_TERMINATED