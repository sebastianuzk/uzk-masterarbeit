# Camunda Platform 7 Integration

Enterprise-grade BPMN 2.0 process engine integration with automatic Docker startup and BPMN deployment.

## 🚀 **Key Features**

✅ **Automatic Docker Startup**
- Docker containers start automatically with Streamlit app
- Intelligent container detection and management
- Clean custom Docker image without demo processes

✅ **Manual Deployment Control**
- No automatic BPMN deployment for security
- Manual "Deploy All BPMN Files" button in Streamlit UI
- User-controlled process deployment decisions
- "Delete All Deployments" functionality for cleanup

✅ **Docker-based Camunda Platform 7**
- Ready-to-use docker-compose setup with custom clean image
- H2 in-memory database (development)
- PostgreSQL option (production)
- Health checks and automatic startup

✅ **Python REST API Client**
- pycamunda-based client with HTTP fallback
- Full BPMN lifecycle management
- Process instance control and task management
- Error handling and retry logic

✅ **Streamlit Management UI**
- Engine status monitoring
- Process statistics and real-time monitoring
- Task assignment and completion interface
- Manual deployment controls
- Direct links to Camunda web apps

## 🏁 **Quick Start**

### 1. Prerequisites

**Docker Required:**
```bash
# Install Docker Desktop
# https://www.docker.com/products/docker-desktop
```

### 2. Start Everything Automatically

**Just start the Streamlit app - everything else happens automatically:**
```bash
cd d:\Uni-Köln\Masterarbeit\Software\uzk-masterarbeit
.\Masterarbeit\Scripts\python.exe -m streamlit run src/ui/streamlit_app.py
```

**What happens automatically:**
1. 🚀 Streamlit app starts
2. 🐳 Docker container automatically starts
3. ✅ Camunda is ready to use!
4. 📋 BPMN files can be deployed manually via UI

### 3. Access Camunda Web Apps

Once auto-started, access Camunda at:
- **Cockpit**: http://localhost:8080/camunda/app/cockpit/
- **Tasklist**: http://localhost:8080/camunda/app/tasklist/
- **Admin**: http://localhost:8080/camunda/app/admin/
- **REST API**: http://localhost:8080/engine-rest/

**Default Login:** demo / demo

### 4. BPMN Manual Deployment

**Manual Process Deployment for Security:**
- Place BPMN files in `src/camunda_integration/bpmn_processes/`
- Use "Deploy All BPMN Files" button in Streamlit UI
- No automatic deployment for security reasons
- Manual control over when processes are deployed

**Current Available Processes:**
- `bewerbung_process.bpmn` - Universitäts-Bewerbungsprozess

**Deployment Management:**
- "Deploy All BPMN Files" button - Deploy all files from bpmn_processes/ directory
- "Delete All Deployments" button - Remove all deployed processes for cleanup

## 🏗️ **Architecture**

```
src/camunda_integration/
├── client/
│   ├── camunda_client.py          # REST API client with pycamunda
│   └── __init__.py
├── docker/
│   ├── Dockerfile                # Custom Camunda image without demos
│   ├── docker-compose.yml         # Auto-start container setup
│   └── startup-deploy.sh          # Auto-deployment script (in container)
├── models/
│   ├── camunda_models.py          # Pydantic data models
│   └── __init__.py
├── services/
│   ├── camunda_service.py         # High-level service layer
│   ├── docker_manager.py          # Docker container management
│   └── __init__.py
├── bpmn_processes/
│   ├── bewerbung_process.bpmn     # Auto-deployed BPMN files
│   └── README.md                  # BPMN development guide
└── README.md                      # This file
```

### Key Components

**Auto-Start Integration (`ui/streamlit_app.py`)**
- Automatic Docker container detection and startup
- Progress monitoring with health checks
- API availability verification
- Manual deployment controls in UI

**CamundaClient (`client/camunda_client.py`)**
- Low-level REST API wrapper
- pycamunda integration with HTTP fallback
- Connection management and error handling

**CamundaService (`services/camunda_service.py`)**
- High-level business logic
- Process statistics and monitoring
- Compatible interface with custom BPMN engine

**DockerManager (`services/docker_manager.py`)**
- Docker container lifecycle management
- Health monitoring and log access
- Cross-platform docker-compose handling

**Custom Docker Image (`docker/Dockerfile`)**
- Based on camunda/camunda-bpm-platform:7.21.0
- Removes all demo processes and applications
- Clean startup without auto-deployment
- Manual deployment control via Streamlit UI

## 📋 **BPMN Development Guide**

### Auto-Deployment Directory

Place BPMN files in `src/camunda_integration/bpmn_processes/` for manual deployment via Streamlit UI.

### BPMN Requirements for Camunda Platform 7

**1. Mandatory History TTL:**
```xml
<bpmn:process id="process_id" name="Process Name" 
              isExecutable="true" 
              camunda:historyTimeToLive="30">
```

**2. Namespace Declaration:**
```xml
<bpmn:definitions xmlns:camunda="http://camunda.org/schema/1.0/bpmn">
```

**3. User Tasks:**
```xml
<bpmn:userTask id="task_id" name="Task Name" camunda:assignee="username">
```

**4. Service Tasks:**
```xml
<bpmn:serviceTask id="service_id" name="Service Name" camunda:class="com.example.ServiceClass">
```

### Example: bewerbung_process.bpmn

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:camunda="http://camunda.org/schema/1.0/bpmn">
  <bpmn:process id="bewerbung_process" 
                name="Universitäts-Bewerbungsprozess"
                isExecutable="true"
                camunda:historyTimeToLive="30">
    <!-- Process definition here -->
  </bpmn:process>
</bpmn:definitions>
```

## 🐳 **Docker Configuration**

### Custom Clean Image

The project uses a custom Docker image (`Dockerfile`) that:
- Removes all Camunda demo processes
- Provides clean startup environment
- Enables manual deployment control via UI
- No automatic BPMN deployment for security

### Database Options

**Current Setup (H2 In-Memory):**
- Fast startup, perfect for development
- Data is lost when container restarts
- No additional setup required

**PostgreSQL Setup (Production):**
```yaml
# Uncomment in docker-compose.yml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: camunda
    POSTGRES_USER: camunda
    POSTGRES_PASSWORD: camunda
```

### Health Check

Container includes automatic health monitoring:
- Camunda REST API availability
- 60 seconds startup grace period
- Automatic restart on failure

## 💻 **Usage Examples**

### Python API

```python
from src.camunda_integration.services.camunda_service import CamundaService

# Initialize service (auto-deploy directory is set automatically)
camunda = CamundaService()

# Check engine status
if camunda.is_engine_running():
    print("Camunda is ready!")

# Get auto-deployed processes
processes = camunda.get_process_definitions()
for proc in processes:
    print(f"Process: {proc.key} - {proc.name}")

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
if tasks:
    camunda.complete_task(tasks[0].id, {"approved": True})

# Get statistics
stats = camunda.get_statistics()
print(f"Active instances: {stats['active_instances']}")
```

### Streamlit Integration

The Camunda engine is fully integrated into the Streamlit UI:

1. **🐳 Docker Status** - Auto-start status and container health
2. **� Statistics** - Real-time monitoring of process instances and tasks  
3. **� Process Management** - Manual deployment and deletion controls
4. **✅ Task Management** - View and complete user tasks
5. **� Process Starting** - Start process instances with parameters

## ⚙️ **Configuration**

### Environment Variables

```bash
# Camunda REST API URL (default: http://localhost:8080/engine-rest)
CAMUNDA_BASE_URL=http://localhost:8080/engine-rest

# Auto-deployment directory (default: src/camunda_integration/bpmn_processes)
CAMUNDA_AUTO_DEPLOY_DIR=src/camunda_integration/bpmn_processes
```

### Docker Memory Settings

Edit `docker-compose.yml` for production:
```yaml
environment:
  - JAVA_OPTS=-Xmx1024m -XX:MaxMetaspaceSize=512m  # Increase for production
```

## 🔧 **Troubleshooting**

### Common Issues

**Docker not starting automatically:**
```bash
# Check Docker Desktop is running
docker version

# Manual start if needed
cd src/camunda_integration/docker
docker-compose up -d
```

**Engine not responding:**
```bash
# Test API connectivity
curl http://localhost:8080/engine-rest/engine

# Check container logs
docker logs camunda-platform

# Check deployment status in Streamlit UI
# Use "Deploy All BPMN Files" button if needed
```

**Manual deployment not working:**
```bash
# Check BPMN files are in correct directory
ls src/camunda_integration/bpmn_processes/

# Use Streamlit UI "Deploy All BPMN Files" button
# Check deployment status in Process Management tab

# Check container logs for deployment errors
docker logs camunda-platform --tail 20
```

**Memory issues:**
```bash
# Increase Java heap in docker-compose.yml
JAVA_OPTS=-Xmx2048m -XX:MaxMetaspaceSize=1024m

# Monitor container resources
docker stats camunda-platform
```

## 🏭 **Production Considerations**

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

## 🆚 **Comparison: Custom Engine vs Camunda**

| Feature | Custom Engine | Camunda Platform 7 |
|---------|---------------|-------------------|
| **Setup** | Built-in | Docker auto-start |
| **Performance** | Lightweight | Enterprise-grade |
| **Features** | Basic BPMN 2.0 | Full BPMN 2.0 + extensions |
| **UI** | Streamlit only | Cockpit + Tasklist + Admin |
| **Persistence** | SQLite | H2/PostgreSQL/Oracle |
| **Clustering** | No | Yes |
| **Monitoring** | Basic | Advanced |
| **Support** | Community | Commercial available |
| **Learning Curve** | Low | Medium |
| **Production Ready** | Development | Enterprise |
| **Deployment** | Manual | Manual (Security) |

Choose based on your needs:
- **Development/Prototyping**: Custom engine
- **Production/Enterprise**: Camunda Platform 7 (recommended)

## 🚀 **Getting Started Summary**

1. **Start Streamlit**: `.\Masterarbeit\Scripts\python.exe -m streamlit run src/ui/streamlit_app.py`
2. **Everything auto-starts**: Docker → Camunda → Ready for use
3. **Access Camunda**: http://localhost:8080/camunda/app/cockpit/
4. **Add BPMN files**: Place in `src/camunda_integration/bpmn_processes/`
5. **Deploy manually**: Use "Deploy All BPMN Files" button in UI

**That's it! The system is fully automated and ready for enterprise use with manual deployment control!** 🎉