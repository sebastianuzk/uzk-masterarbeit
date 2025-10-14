# Camunda Platform 7 Integration

Enterprise-grade BPMN 2.0 process engine integration with automatic Docker startup and BPMN deployment.

## 🚀 **Key Features**

✅ **Automatic Docker Startup**
- Docker containers start automatically with Streamlit app
- Intelligent container detection and management
- Clean custom Docker image without demo processes

✅ **Auto-Deployment of BPMN Files**
- All `.bpmn` files in `bpmn_processes/` are automatically deployed at startup
- No manual deployment required
- Startup script handles deployment via REST API

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
- Auto-deployed process overview
- Task assignment and completion
- Statistics and real-time monitoring
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
3. 📋 BPMN files are auto-deployed
4. ✅ Camunda is ready to use!

### 3. Access Camunda Web Apps

Once auto-started, access Camunda at:
- **Cockpit**: http://localhost:8080/camunda/app/cockpit/
- **Tasklist**: http://localhost:8080/camunda/app/tasklist/
- **Admin**: http://localhost:8080/camunda/app/admin/
- **REST API**: http://localhost:8080/engine-rest/

**Default Login:** demo / demo

### 4. BPMN Auto-Deployment

**Automatic Process Deployment:**
- Place BPMN files in `src/camunda_integration/bpmn_processes/`
- Files are automatically deployed when Docker container starts
- No manual deployment needed!

**Current Auto-Deployed Processes:**
- `bewerbung_process.bpmn` - Universitäts-Bewerbungsprozess

## 🏗️ **Architecture**

```
src/camunda_integration/
├── client/
│   ├── camunda_client.py          # REST API client with pycamunda
│   └── __init__.py
├── docker/
│   ├── Dockerfile.clean           # Custom Camunda image without demos
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

**Custom Docker Image (`docker/Dockerfile.clean`)**
- Based on camunda/camunda-bpm-platform:7.21.0
- Removes all demo processes and applications
- Includes auto-deployment startup script
- BPMN files copied to container and deployed automatically

## 📋 **BPMN Development Guide**

### Auto-Deployment Directory

Place BPMN files in `src/camunda_integration/bpmn_processes/` for automatic deployment.

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

The project uses a custom Docker image (`Dockerfile.clean`) that:
- Removes all Camunda demo processes
- Includes auto-deployment script
- Copies BPMN files from `bpmn_processes/` directory
- Deploys processes automatically on startup

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
2. **📋 Auto-Deployed Processes** - View automatically deployed BPMN files
3. **🚀 Process Starting** - Start process instances
4. **✅ Task Management** - View and complete tasks
5. **📊 Statistics** - Monitor engine performance

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
docker logs camunda-platform-clean

# View auto-deployment logs
docker logs camunda-platform-clean | grep "Deploying"
```

**Auto-deployment not working:**
```bash
# Check BPMN files are in correct directory
ls src/camunda_integration/bpmn_processes/

# Verify files are copied to container
docker exec camunda-platform-clean ls /tmp/bpmn-deploy/

# Check deployment logs
docker logs camunda-platform-clean --tail 20
```

**Memory issues:**
```bash
# Increase Java heap in docker-compose.yml
JAVA_OPTS=-Xmx2048m -XX:MaxMetaspaceSize=1024m

# Monitor container resources
docker stats camunda-platform-clean
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
| **Auto-Deployment** | Manual | Automatic |

Choose based on your needs:
- **Development/Prototyping**: Custom engine
- **Production/Enterprise**: Camunda Platform 7 (recommended)

## 🚀 **Getting Started Summary**

1. **Start Streamlit**: `.\Masterarbeit\Scripts\python.exe -m streamlit run src/ui/streamlit_app.py`
2. **Everything auto-starts**: Docker → Camunda → BPMN deployment
3. **Access Camunda**: http://localhost:8080/camunda/app/cockpit/
4. **Add BPMN files**: Place in `src/camunda_integration/bpmn_processes/`
5. **Restart container**: Files are auto-deployed

**That's it! The system is fully automated and ready for enterprise use!** 🎉