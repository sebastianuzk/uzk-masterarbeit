# Camunda Platform 7 Integration

Enterprise-grade BPMN 2.0 process engine integration for the chatbot agent.

## Features

✅ **Docker-based Camunda Platform 7**
- Ready-to-use docker-compose setup
- H2 in-memory database (development)
- PostgreSQL option (production)
- Health checks and automatic startup

✅ **Python REST API Client**
- pycamunda-based client with fallback
- Full BPMN lifecycle management
- Process instance control
- Task management
- Error handling and retry logic

✅ **Streamlit Management UI**
- Engine control (start/stop/restart)
- Process deployment and management
- Task assignment and completion
- Statistics and monitoring
- Direct links to Camunda web apps

✅ **Automated BPMN Deployment**
- Auto-deploy from `deployed_processes/` directory
- Manual file upload support
- Version management
- Deployment cleanup

## Quick Start

### 1. Prerequisites

**Docker Required:**
```bash
# Install Docker Desktop
# https://www.docker.com/products/docker-desktop
```

**Java (optional - included in Docker):**
- Java 8+ for local Camunda installation
- Not needed when using Docker

### 2. Start Camunda

**Via Streamlit UI:**
1. Open Streamlit app: `http://localhost:8501`
2. Go to "🏗️ Camunda Engine" tab
3. Click "🚀 Start Camunda"
4. Wait for engine to be ready (~2 minutes)

**Via Command Line:**
```bash
cd src/camunda_integration/docker
docker-compose up -d
```

### 3. Access Camunda Web Apps

Once started, access Camunda at:
- **Cockpit**: http://localhost:8080/camunda/app/cockpit/
- **Tasklist**: http://localhost:8080/camunda/app/tasklist/
- **Admin**: http://localhost:8080/camunda/app/admin/
- **REST API**: http://localhost:8080/engine-rest/

**Default Login:** demo / demo

### 4. Deploy BPMN Processes

**Automatic Deployment:**
- Place BPMN files in `src/process_automation/deployed_processes/`
- Click "🔄 Auto-Deploy" in Streamlit UI
- Files are automatically deployed to Camunda

**Manual Deployment:**
- Upload BPMN files via Streamlit UI
- Or use Camunda Cockpit web interface

## Architecture

```
src/camunda_integration/
├── client/
│   ├── camunda_client.py          # REST API client
│   └── __init__.py
├── docker/
│   ├── docker-compose.yml         # Camunda container setup
│   └── README.md                  # Docker documentation
├── models/
│   ├── camunda_models.py          # Pydantic data models
│   └── __init__.py
├── services/
│   ├── camunda_service.py         # High-level service layer
│   ├── docker_manager.py          # Docker container management
│   └── __init__.py
└── __init__.py
```

### Key Components

**CamundaClient (`client/camunda_client.py`)**
- Low-level REST API wrapper
- pycamunda integration with HTTP fallback
- Connection management and error handling
- BPMN deployment, process control, task management

**CamundaService (`services/camunda_service.py`)**
- High-level business logic
- Automatic directory deployment
- Process statistics and monitoring
- Compatible interface with custom BPMN engine

**DockerManager (`services/docker_manager.py`)**
- Docker container lifecycle management
- Health monitoring and log access
- Cross-platform docker-compose handling

**Camunda Interface (`ui/camunda_interface.py`)**
- Streamlit UI components
- Engine control panel
- Process and task management
- Real-time statistics dashboard

## Usage Examples

### Python API

```python
from src.camunda_integration.services.camunda_service import CamundaService

# Initialize service
camunda = CamundaService(auto_deploy_dir="src/process_automation/deployed_processes")

# Check engine status
if camunda.is_engine_running():
    print("Camunda is ready!")

# Deploy BPMN files
deployments = camunda.deploy_from_directory()
print(f"Deployed {len(deployments)} processes")

# Start a process
instance = camunda.start_process("bewerbung_process", {
    "applicant_name": "John Doe",
    "position": "Software Engineer"
})

# Get open tasks
tasks = camunda.get_tasks()
for task in tasks:
    print(f"Task: {task.name} - Assignee: {task.assignee}")

# Complete a task
camunda.complete_task(tasks[0].id, {"approved": True})

# Get statistics
stats = camunda.get_statistics()
print(f"Active instances: {stats['active_instances']}")
```

### Streamlit Integration

The Camunda engine is fully integrated into the Streamlit UI with tabs for:

1. **🎛️ Engine Control** - Start/stop Docker container
2. **📋 Process Management** - Deploy and start processes
3. **✅ Task Management** - View and complete tasks
4. **📊 Statistics** - Monitor engine performance

## Configuration

### Environment Variables

```bash
# Camunda REST API URL (default: http://localhost:8080/engine-rest)
CAMUNDA_BASE_URL=http://localhost:8080/engine-rest

# Auto-deployment directory (default: src/process_automation/deployed_processes)
CAMUNDA_AUTO_DEPLOY_DIR=src/process_automation/deployed_processes
```

### Docker Configuration

Edit `src/camunda_integration/docker/docker-compose.yml`:

**Database Options:**
- H2 in-memory (default) - Fast, data lost on restart
- PostgreSQL - Persistent data, production ready

**Memory Settings:**
```yaml
environment:
  - JAVA_OPTS=-Xmx1024m -XX:MaxMetaspaceSize=512m  # Increase for production
```

**Port Configuration:**
```yaml
ports:
  - "8080:8080"  # Change if port 8080 is occupied
```

## Integration with Chatbot

The Camunda integration is designed to work alongside the existing custom BPMN engine. Both engines can run simultaneously, allowing for:

- **Development**: Use custom engine for rapid prototyping
- **Production**: Use Camunda for enterprise features
- **Migration**: Gradual transition from custom to Camunda
- **Comparison**: A/B testing of different engines

### Future Chatbot Integration

Planned LangChain tools for chatbot integration:

```python
# Future implementation
from src.camunda_integration.tools import (
    CamundaTaskListTool,
    CamundaCompleteTaskTool, 
    CamundaStartProcessTool
)

# Add to agent tools
agent_tools = [
    CamundaTaskListTool(),
    CamundaCompleteTaskTool(),
    CamundaStartProcessTool(),
    # ... existing tools
]
```

## Troubleshooting

### Common Issues

**Docker not starting:**
```bash
# Check Docker Desktop is running
docker version

# Check port availability
netstat -an | findstr :8080

# View container logs
docker-compose logs camunda
```

**Engine not responding:**
```bash
# Test API connectivity
curl http://localhost:8080/engine-rest/engine

# Check container health
docker-compose ps
```

**Memory issues:**
```bash
# Increase Java heap in docker-compose.yml
JAVA_OPTS=-Xmx2048m -XX:MaxMetaspaceSize=1024m

# Monitor container resources
docker stats camunda-platform
```

**Import errors:**
```bash
# Ensure dependencies are installed in venv
.\Masterarbeit\Scripts\pip.exe install -r requirements.txt

# Test imports
.\Masterarbeit\Scripts\python.exe -c "from src.camunda_integration import get_camunda_service; print('OK')"
```

## Production Considerations

### Security
- Change default admin credentials (demo/demo)
- Enable HTTPS in production
- Configure proper authentication (LDAP/SSO)
- Restrict network access to Camunda ports

### Performance
- Use PostgreSQL instead of H2
- Increase Java heap size based on load
- Configure proper connection pooling
- Monitor JVM metrics

### Backup
- Regular PostgreSQL backups
- Export BPMN definitions
- Backup process data and history

### Monitoring
- Use Camunda enterprise monitoring tools
- Integrate with application logging
- Set up health check alerts
- Monitor Java GC and memory usage

## Comparison: Custom Engine vs Camunda

| Feature | Custom Engine | Camunda Platform 7 |
|---------|---------------|-------------------|
| **Setup** | Built-in | Docker required |
| **Performance** | Lightweight | Enterprise-grade |
| **Features** | Basic BPMN 2.0 | Full BPMN 2.0 + extensions |
| **UI** | Streamlit only | Cockpit + Tasklist + Admin |
| **Persistence** | SQLite | H2/PostgreSQL/Oracle |
| **Clustering** | No | Yes |
| **Monitoring** | Basic | Advanced |
| **Support** | Community | Commercial available |
| **Learning Curve** | Low | Medium |
| **Production Ready** | Development | Enterprise |

Choose based on your needs:
- **Development/Prototyping**: Custom engine
- **Production/Enterprise**: Camunda Platform 7