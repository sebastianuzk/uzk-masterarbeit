# Camunda Platform 7 Docker Setup

## Quick Start

1. **Start Camunda Platform 7:**
   ```bash
   cd src/camunda_integration/docker
   docker-compose up -d
   ```

2. **Access Camunda:**
   - **Cockpit**: http://localhost:8080/camunda/app/cockpit/
   - **Tasklist**: http://localhost:8080/camunda/app/tasklist/
   - **Admin**: http://localhost:8080/camunda/app/admin/
   - **REST API**: http://localhost:8080/engine-rest/

3. **Default Login:**
   - Username: `demo`
   - Password: `demo`

## Docker Configuration

### Database Options

**Current Setup (H2 In-Memory):**
- Fast startup, perfect for development
- Data is lost when container restarts
- No additional setup required

**PostgreSQL Setup (Production):**
- Uncomment PostgreSQL service in docker-compose.yml
- Update Camunda environment variables:
  ```yaml
  environment:
    - DB_DRIVER=org.postgresql.Driver
    - DB_URL=jdbc:postgresql://postgres:5432/camunda
    - DB_USERNAME=camunda
    - DB_PASSWORD=camunda
  ```

### Health Check

The container includes a health check that monitors:
- Camunda REST API availability
- Engine status endpoint
- 60 seconds startup grace period

### Useful Commands

```bash
# View logs
docker-compose logs -f camunda

# Stop services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Check service status
docker-compose ps

# Access container shell
docker exec -it camunda-platform bash
```

## REST API Endpoints

Base URL: `http://localhost:8080/engine-rest`

**Key Endpoints:**
- `GET /engine` - Engine information
- `POST /deployment/create` - Deploy BPMN
- `POST /process-definition/key/{key}/start` - Start process
- `GET /task` - Get tasks
- `POST /task/{id}/complete` - Complete task

## Troubleshooting

**Container won't start:**
- Check port 8080 availability: `netstat -an | findstr :8080`
- Verify Docker is running
- Check logs: `docker-compose logs camunda`

**Memory Issues:**
- Increase Java heap: Modify `JAVA_OPTS` in docker-compose.yml
- Available memory: `docker stats camunda-platform`

**API Connection Issues:**
- Verify health check: `docker-compose ps`
- Test API: `curl http://localhost:8080/engine-rest/engine`
- Check firewall settings