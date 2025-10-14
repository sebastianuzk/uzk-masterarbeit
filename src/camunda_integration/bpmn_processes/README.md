# Camunda BPMN Processes

This directory contains BPMN process definitions that are automatically deployed to Camunda Platform 7.

## Auto-Deployment

**All `.bpmn` files in this directory are automatically deployed to Camunda when:**
- The Streamlit app starts
- You click "🔄 Auto-Deploy from Directory" in the Camunda Engine tab
- The CamundaService.deploy_from_directory() method is called

## BPMN Requirements for Camunda Platform 7

### Mandatory Attributes

**1. History Time To Live (TTL)**
```xml
<bpmn:process id="process_id" name="Process Name" 
              isExecutable="true" 
              camunda:historyTimeToLive="30">
```
- **Required**: `camunda:historyTimeToLive` attribute
- **Value**: Number of days (e.g., "30")
- **Purpose**: History cleanup for performance

**2. Namespace Declaration**
```xml
<bpmn:definitions xmlns:camunda="http://camunda.org/schema/1.0/bpmn">
```

### User Tasks

**Assignment:**
```xml
<bpmn:userTask id="task_id" name="Task Name" camunda:assignee="username">
```

**Candidate Groups:**
```xml
<bpmn:userTask id="task_id" name="Task Name" camunda:candidateGroups="group1,group2">
```

### Service Tasks

**Java Class:**
```xml
<bpmn:serviceTask id="service_id" name="Service Name" camunda:class="com.example.ServiceClass">
```

**Expression:**
```xml
<bpmn:serviceTask id="service_id" name="Service Name" camunda:expression="${serviceBean.method()}">
```

### Gateway Conditions

**Exclusive Gateway:**
```xml
<bpmn:sequenceFlow id="flow_id" sourceRef="gateway" targetRef="target">
  <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">
    ${variable == true}
  </bpmn:conditionExpression>
</bpmn:sequenceFlow>
```

## Current Processes

### 1. bewerbung_process.bpmn
- **Name**: Universitäts-Bewerbungsprozess
- **ID**: bewerbung_process
- **Description**: University application approval process
- **Elements**: 7 activities (Start, User Tasks, Service Task, Gateway, End Events)

**Process Flow:**
1. **Start**: Bewerbung eingegangen
2. **User Task**: Angaben prüfen (Assignee: sachbearbeiter)
3. **Gateway**: Bewerbung gültig? (Decision based on `bewerbung_gueltig`)
4. **Service Task**: Bewerbung akzeptieren (Class: AcceptApplicationService)
5. **User Task**: Ablehnung begründen (Alternative path)
6. **End Events**: Bewerbung akzeptiert/abgelehnt

**Variables:**
- `bewerbung_gueltig` (Boolean): Determines approval/rejection path
- `applicant_name` (String): Name of applicant
- `position` (String): Applied position

## Adding New Processes

### 1. Create BPMN File
Create new `.bpmn` file in this directory with:
- Unique process ID
- `camunda:historyTimeToLive` attribute
- Proper Camunda namespace

### 2. Design Process
Use tools like:
- **Camunda Modeler** (Recommended): https://camunda.com/download/modeler/
- **bpmn.io**: Online modeler
- **VS Code BPMN Extension**: For text editing

### 3. Deploy Process
**Automatic:** Place file in this directory and restart Streamlit or use Auto-Deploy button

**Manual:** Upload via Streamlit UI in Camunda Engine tab

### 4. Test Process
1. Go to Camunda Cockpit: http://localhost:8080/camunda/app/cockpit/
2. Start process instance
3. Check Tasklist: http://localhost:8080/camunda/app/tasklist/

## Best Practices

### 1. Naming Conventions
- **File**: `process_name.bpmn`
- **Process ID**: `process_name` (lowercase, underscore)
- **Process Name**: "Human Readable Name"
- **Element IDs**: `element_type_name` (e.g., `start_application`, `check_data`)

### 2. Documentation
- Add descriptions to process and activities
- Use meaningful names for variables
- Document business rules in annotations

### 3. Error Handling
- Add boundary events for error handling
- Use compensation events for rollback
- Implement timeout events for long-running tasks

### 4. Variables
- Use consistent variable names across processes
- Define variable types clearly
- Document expected variable values

## Troubleshooting

### Common Deployment Errors

**1. Missing TTL**
```
ENGINE-12018 History Time To Live (TTL) cannot be null
```
**Solution:** Add `camunda:historyTimeToLive="30"` to process element

**2. Invalid BPMN**
```
ENGINE-09005 Could not parse BPMN process
```
**Solution:** Validate BPMN with Camunda Modeler

**3. Missing Namespace**
```
Namespace prefix 'camunda' is not bound
```
**Solution:** Add `xmlns:camunda="http://camunda.org/schema/1.0/bpmn"` to definitions

### Validation Tools

**1. Camunda Modeler**
- Built-in validation
- Real-time error checking
- Deployment testing

**2. Online Validator**
- BPMN 2.0 specification compliance
- Camunda-specific validation

**3. Streamlit Deployment**
- Error messages in deployment log
- Detailed error descriptions

## Integration with Custom Engine

**Parallel Operation:**
- Custom BPMN engine: `src/process_automation/deployed_processes/`
- Camunda engine: `src/camunda_integration/bpmn_processes/`
- Both can run simultaneously

**Migration Path:**
1. Copy processes from custom engine directory
2. Add Camunda-specific attributes (TTL, assignments)
3. Test in Camunda
4. Gradually migrate logic to Camunda

**Differences:**
- Custom engine: Simplified BPMN 2.0
- Camunda: Full BPMN 2.0 + Camunda extensions
- Camunda: Enterprise features (clustering, monitoring, etc.)