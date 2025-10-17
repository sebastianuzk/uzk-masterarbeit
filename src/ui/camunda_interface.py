"""
Camunda Engine Interface for Streamlit

Provides UI components for Camunda Platform 7 management.
"""

import streamlit as st
import logging
import traceback
from pathlib import Path

from config.settings import settings
from src.camunda_integration.client.camunda_client import CamundaClient
from src.camunda_integration.services.camunda_service import CamundaService
from src.camunda_integration.services.docker_manager import DockerManager


logger = logging.getLogger(__name__)


def get_camunda_service() -> CamundaService:
    """
    Get or create Camunda service instance
    
    Returns:
        CamundaService instance
    """
    if 'camunda_service' not in st.session_state:
        # Create Camunda client and service with new API
        client = CamundaClient(settings.CAMUNDA_BASE_URL)
        bpmn_dir = Path("src/camunda_integration/bpmn_processes")
        st.session_state.camunda_service = CamundaService(
            client=client,
            bpmn_dir=bpmn_dir
        )
    
    return st.session_state.camunda_service


def get_docker_manager() -> DockerManager:
    """
    Get or create Docker manager instance
    
    Returns:
        DockerManager instance
    """
    if 'docker_manager' not in st.session_state:
        compose_file = Path("src/camunda_integration/docker/docker-compose.yml")
        st.session_state.docker_manager = DockerManager(compose_file=compose_file)
    
    return st.session_state.docker_manager


def display_camunda_engine_interface():
    """
    Main Camunda engine interface
    """
    st.markdown("## 🏗️ Camunda Platform 7 Engine")
    st.markdown("Enterprise-grade BPMN 2.0 process engine with full Camunda integration.")
    
    # Initialize services
    camunda_service = get_camunda_service()
    docker_manager = get_docker_manager()
    
    # Check Docker availability
    if not docker_manager.is_docker_available():
        st.error("🐳 Docker ist nicht verfügbar. Bitte installieren Sie Docker Desktop.")
        st.markdown("""
        **Docker Installation:**
        1. Laden Sie Docker Desktop herunter: https://www.docker.com/products/docker-desktop
        2. Installieren und starten Sie Docker Desktop
        3. Laden Sie diese Seite neu
        """)
        return
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎛️ Engine Control", 
        "📋 Process Management", 
        "✅ Task Management", 
        "📊 Statistics"
    ])
    
    with tab1:
        display_engine_control(camunda_service, docker_manager)
    
    with tab2:
        display_process_management(camunda_service)
    
    with tab3:
        display_task_management(camunda_service)
    
    with tab4:
        display_statistics(camunda_service)


def display_engine_control(camunda_service: CamundaService, docker_manager: DockerManager):
    """
    Engine control panel
    """
    st.markdown("### 🎛️ Engine Control")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Docker Container")
        
        # Get container status
        status = docker_manager.get_status()
        
        if status.get("running", False):
            st.success("✅ Camunda Container läuft")
            
            if st.button("🛑 Stop Camunda", type="secondary"):
                with st.spinner("Stopping Camunda..."):
                    result = docker_manager.stop_camunda()
                    if result["success"]:
                        st.success("Camunda gestoppt")
                        st.rerun()
                    else:
                        st.error(f"Fehler beim Stoppen: {result['error']}")
            
            if st.button("🔄 Restart Camunda", type="secondary"):
                with st.spinner("Restarting Camunda..."):
                    result = docker_manager.restart_camunda()
                    if result["success"]:
                        st.success("Camunda neu gestartet")
                        st.rerun()
                    else:
                        st.error(f"Fehler beim Neustart: {result['error']}")
        else:
            st.warning("⚠️ Camunda Container läuft nicht")
            
            if st.button("🚀 Start Camunda", type="primary"):
                with st.spinner("Starting Camunda... (kann bis zu 2 Minuten dauern)"):
                    result = docker_manager.start_camunda()
                    if result["success"]:
                        st.success("Camunda gestartet")
                        # Wait for engine to be ready
                        with st.spinner("Warte auf Engine..."):
                            if camunda_service.wait_for_engine(attempts=120, sleep_seconds=1.0):
                                st.success("Camunda Engine ist bereit!")
                            else:
                                st.warning("Engine braucht länger zum Starten")
                        st.rerun()
                    else:
                        st.error(f"Fehler beim Starten: {result['error']}")
                        if result.get("output"):
                            st.code(result["output"])
        
        # Container logs
        if st.button("📄 Show Logs"):
            logs_result = docker_manager.get_logs()
            if logs_result["success"]:
                st.code(logs_result["logs"], language="text")
            else:
                st.error(f"Fehler beim Laden der Logs: {logs_result['error']}")
    
    with col2:
        st.markdown("#### Engine Status")
        
        # Engine connectivity
        if camunda_service.is_engine_running():
            st.success("✅ Engine API erreichbar")
            
            # Get engine info directly from client
            try:
                # Get basic engine info
                version_info = camunda_service.client.get_version()
                st.write(f"**Version:** {version_info.get('version', 'Unknown')}")
                
                # Get statistics directly
                process_definitions = camunda_service.client.get_process_definitions()
                process_instances = camunda_service.client.get_process_instances()
                tasks = camunda_service.client.get_all_tasks()
                
                st.write(f"**Process Definitions:** {len(process_definitions) if process_definitions else 0}")
                st.write(f"**Active Instances:** {len(process_instances) if process_instances else 0}")
                st.write(f"**Open Tasks:** {len(tasks) if tasks else 0}")
                
                # Camunda UI Links
                st.markdown("#### 🌐 Camunda Web Apps")
                st.markdown("**Cockpit:** [http://localhost:8080/camunda/app/cockpit/](http://localhost:8080/camunda/app/cockpit/)")
                st.markdown("**Tasklist:** [http://localhost:8080/camunda/app/tasklist/](http://localhost:8080/camunda/app/tasklist/)")
                st.markdown("**Admin:** [http://localhost:8080/camunda/app/admin/](http://localhost:8080/camunda/app/admin/)")
                st.markdown("**Login:** demo / demo")
                
            except Exception as e:
                st.error(f"Fehler beim Abrufen des Engine-Status: {str(e)}")
        else:
            st.error("❌ Engine API nicht erreichbar")
            st.markdown("Stellen Sie sicher, dass:")
            st.markdown("- Docker Container läuft")
            st.markdown("- Port 8080 verfügbar ist")
            st.markdown("- Engine vollständig gestartet ist")


def display_process_management(camunda_service: CamundaService):
    """
    Process deployment and management
    """
    st.markdown("### 📋 Process Management")
    
    if not camunda_service.is_engine_running():
        st.warning("⚠️ Engine nicht verfügbar. Bitte starten Sie zuerst die Engine.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🚀 Manual Process Deployment")
        
        # Show BPMN files in directory
        camunda_service = get_camunda_service()
        bpmn_files = list(camunda_service.bpmn_dir.glob("**/*.bpmn"))
        
        if bpmn_files:
            st.success(f"✅ {len(bpmn_files)} BPMN file(s) found:")
            for bpmn_file in bpmn_files:
                st.write(f"- {bpmn_file.name}")
            
            # Manual deployment button
            if st.button("🚀 Deploy All BPMN Files", type="primary"):
                with st.spinner("Deploying BPMN files..."):
                    try:
                        result = camunda_service.deploy_all()
                        if result.get("success"):
                            deployment_result = result.get("result", {})
                            deployed_count = len(deployment_result.get("deployedProcessDefinitions", []))
                            st.success(f"✅ Successfully deployed {deployed_count} process definition(s)!")
                            if "id" in deployment_result:
                                st.info(f"Deployment ID: {deployment_result['id']}")
                            st.rerun()
                        else:
                            st.error(f"❌ Deployment failed: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"❌ Deployment error: {str(e)}")
            
            # Delete all deployments button
            if st.button("🗑️ Delete All Deployments", type="secondary"):
                with st.spinner("Deleting all deployments..."):
                    try:
                        # Hole alle Deployments
                        deployments_response = camunda_service.client._session.get(
                            f"{camunda_service.client.base_url}/deployment"
                        )
                        
                        if deployments_response.status_code == 200:
                            deployments = deployments_response.json()
                            deleted_count = 0
                            
                            for deployment in deployments:
                                deployment_id = deployment['id']
                                
                                # Lösche Deployment mit cascade=true (entfernt auch aktive Instanzen)
                                delete_response = camunda_service.client._session.delete(
                                    f"{camunda_service.client.base_url}/deployment/{deployment_id}",
                                    params={'cascade': 'true'}
                                )
                                
                                if delete_response.status_code == 204:
                                    deleted_count += 1
                                else:
                                    st.warning(f"⚠️ Failed to delete deployment {deployment_id}")
                            
                            if deleted_count > 0:
                                st.success(f"✅ Successfully deleted {deleted_count} deployment(s) and all associated process instances!")
                                st.rerun()
                            else:
                                st.info("ℹ️ No deployments found to delete")
                        else:
                            st.error(f"❌ Failed to retrieve deployments: {deployments_response.status_code}")
                            
                    except Exception as e:
                        st.error(f"❌ Delete error: {str(e)}")
        else:
            st.warning(f"⚠️ No BPMN files found in {camunda_service.bpmn_dir}")
            st.markdown("**To add processes:**")
            st.markdown("1. Place .bpmn files in `src/camunda_integration/bpmn_processes/`")
            st.markdown("2. Click 'Deploy All BPMN Files'")
        
        st.markdown("---")
        st.info("ℹ️ **Note**: Processes are no longer automatically deployed when the container starts. Use the deployment button above to manually deploy your BPMN files.")
        
        # Show deployed processes
        try:
            process_definitions = camunda_service.client.get_process_definitions()
            if process_definitions:
                st.success(f"✅ {len(process_definitions)} processes currently deployed:")
                for proc in process_definitions:
                    st.write(f"- **{proc.key}**: {proc.name}")
            else:
                st.info("ℹ️ No processes deployed yet. Click 'Deploy All BPMN Files' above.")
        except Exception as e:
            st.error(f"Failed to get process definitions: {str(e)}")
    
    with col2:
        st.markdown("#### 🚀 Process Starting")
        
        # Get process definitions
        try:
            process_definitions = camunda_service.client.get_process_definitions()
            
            if process_definitions:
                # Select process to start
                process_options = {f"{pd.name or pd.key} (v{pd.version})": pd.key 
                                  for pd in process_definitions}
                selected_process_display = st.selectbox("Select Process", list(process_options.keys()))
                
                if selected_process_display:
                    selected_process_key = process_options[selected_process_display]
                    
                    # Business key
                    business_key = st.text_input("Business Key (optional)")
                    
                    # Variables
                    st.markdown("**Process Variables (JSON format):**")
                    
                    # Show required fields from Camunda API
                    try:
                        # Get form variables directly from Camunda
                        definition = camunda_service.client.get_definition_by_key(selected_process_key)
                        if definition:
                            form_vars = camunda_service.client.get_start_form_variables(definition.id)
                            if form_vars:
                                st.markdown("**Required Fields (from Camunda):**")
                                required_fields = []
                                for var_name, var_spec in form_vars.items():
                                    field_info = f"- `{var_name}` ({var_spec.get('type', 'String')})"
                                    if var_spec.get('required', False):
                                        field_info += " **required**"
                                    st.markdown(field_info)
                                    
                                    if var_spec.get('required', False):
                                        required_fields.append({
                                            'id': var_name,
                                            'type': var_spec.get('type', 'String').lower(),
                                            'required': True
                                        })
                                
                                # Generate example JSON from Camunda form variables
                                example_vars = {}
                                for field in required_fields:
                                    if field['type'] == 'string':
                                        example_vars[field['id']] = f"Beispiel für {field['id']}"
                                    elif field['type'] == 'long' or field['type'] == 'integer':
                                        example_vars[field['id']] = 12345
                                    elif field['type'] == 'boolean':
                                        example_vars[field['id']] = True
                                    else:
                                        example_vars[field['id']] = f"Wert für {field['id']}"
                                
                                import json
                                example_json = json.dumps(example_vars, indent=2, ensure_ascii=False)
                                variables_text = st.text_area("Variables", example_json, height=120)
                            else:
                                variables_text = st.text_area("Variables", '{}', height=100)
                        else:
                            variables_text = st.text_area("Variables", '{}', height=100)
                    except Exception:
                        variables_text = st.text_area("Variables", '{}', height=100)
                    
                    if st.button("🚀 Start Process Instance"):
                        try:
                            variables = {}
                            if variables_text.strip():
                                import json
                                variables = json.loads(variables_text)
                            
                            result = camunda_service.start_process(
                                selected_process_key, 
                                variables, 
                                business_key if business_key else None
                            )
                            
                            if result.success:
                                st.success(f"✅ Process started! Instance ID: {result.process_instance_id}")
                                if result.next_tasks:
                                    st.info(f"Next tasks: {len(result.next_tasks)} task(s) created")
                            else:
                                st.error(f"❌ Process start failed: {result.message}")
                                if result.missing:
                                    st.error("**Missing required fields (use these exact parameter names):**")
                                    for missing in result.missing:
                                        field_id = missing.get('id')
                                        field_label = missing.get('label', field_id)
                                        st.write(f"- **`{field_id}`** ({field_label})")
                                    
                                    st.info("💡 **Tip**: Use the field IDs (in backticks) as JSON keys, not the labels.")
                            
                        except json.JSONDecodeError:
                            st.error("Invalid JSON format for variables")
                        except Exception as e:
                            st.error(f"Failed to start process: {str(e)}")
            else:
                st.info("No process definitions found. Deploy BPMN files first.")
                
        except Exception as e:
            st.error(f"Failed to load process definitions: {str(e)}")
    
    # Process Definitions Table
    st.markdown("#### 📋 Deployed Process Definitions")
    try:
        process_definitions = camunda_service.client.get_process_definitions()
        
        if process_definitions:
            # Convert to display format
            process_data = []
            for pd in process_definitions:
                process_data.append({
                    "Name": pd.name or pd.key,
                    "Key": pd.key,
                    "Version": pd.version,
                    "Deployment ID": pd.deployment_id,
                    "Suspended": "Yes" if pd.suspended else "No"
                })
            
            st.dataframe(process_data, width='stretch')
        else:
            st.info("No process definitions deployed yet.")
            
    except Exception as e:
        st.error(f"Failed to load process definitions: {str(e)}")


def display_task_management(camunda_service: CamundaService):
    """
    Task management interface
    """
    st.markdown("### ✅ Task Management")
    
    if not camunda_service.is_engine_running():
        st.warning("⚠️ Engine nicht verfügbar. Bitte starten Sie zuerst die Engine.")
        return
    
    # Get tasks
    try:
        tasks = camunda_service.client.get_all_tasks()
        
        if tasks:
            st.markdown(f"#### 📋 Open Tasks ({len(tasks)})")
            
            # Task filters
            col1, col2 = st.columns(2)
            with col1:
                assignee_filter = st.text_input("Filter by Assignee")
            with col2:
                process_filter = st.selectbox("Filter by Process", 
                                            ["All"] + list(set([t.processInstanceId or "unknown" for t in tasks])))
            
            # Filter tasks
            filtered_tasks = tasks
            if assignee_filter:
                filtered_tasks = [t for t in filtered_tasks if t.assignee and assignee_filter in t.assignee]
            if process_filter != "All":
                filtered_tasks = [t for t in filtered_tasks if t.processInstanceId == process_filter]
            
            # Display tasks
            for task in filtered_tasks:
                with st.expander(f"📌 {task.name or task.id} - {task.assignee or 'Unassigned'}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Task ID:** {task.id}")
                        st.write(f"**Name:** {task.name or 'N/A'}")
                        st.write(f"**Assignee:** {task.assignee or 'Unassigned'}")
                        st.write(f"**Process Instance:** {task.processInstanceId or 'N/A'}")
                        
                    with col2:
                        # Task completion
                        st.markdown("**Complete Task:**")
                        
                        # Task variables
                        task_variables = st.text_area(
                            "Completion Variables (JSON)",
                            '{}',
                            key=f"vars_{task.id}",
                            height=80
                        )
                        
                        if st.button("✅ Complete Task", key=f"complete_{task.id}"):
                            try:
                                variables = {}
                                if task_variables.strip():
                                    import json
                                    variables = json.loads(task_variables)
                                
                                camunda_service.complete_task(task.id, variables)
                                st.success(f"✅ Task {task.id} completed!")
                                st.rerun()
                                
                            except json.JSONDecodeError:
                                st.error("Invalid JSON format for variables")
                            except Exception as e:
                                st.error(f"Failed to complete task: {str(e)}")
        else:
            st.info("🎉 No open tasks found!")
            
    except Exception as e:
        st.error(f"Failed to load tasks: {str(e)}")


def display_statistics(camunda_service: CamundaService):
    """
    Statistics and monitoring
    """
    st.markdown("### 📊 Engine Statistics")
    
    if not camunda_service.is_engine_running():
        st.warning("⚠️ Engine nicht verfügbar. Bitte starten Sie zuerst die Engine.")
        return
    
    try:
        # Get data directly from client
        process_definitions = camunda_service.client.get_process_definitions()
        active_instances = camunda_service.client.get_process_instances()
        completed_instances = camunda_service.client.get_history_process_instances()
        tasks = camunda_service.client.get_all_tasks()
        
        # Calculate statistics
        process_def_count = len(process_definitions) if process_definitions else 0
        active_count = len(active_instances) if active_instances else 0
        completed_count = len(completed_instances) if completed_instances else 0
        tasks_count = len(tasks) if tasks else 0
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Process Definitions", process_def_count)
        with col2:
            st.metric("Active Instances", active_count)
        with col3:
            st.metric("Completed Instances", completed_count)
        with col4:
            st.metric("Open Tasks", tasks_count)
        
        # Process breakdown
        if active_instances or completed_instances:
            st.markdown("#### 📈 Processes Breakdown")
            
            # Count by process definition
            process_counts = {}
            
            # Count active instances by process
            if active_instances:
                for instance in active_instances:
                    process_key = "unknown"
                    if hasattr(instance, 'definitionId') and instance.definitionId:
                        try:
                            process_key = instance.definitionId.split(':')[0]
                        except:
                            process_key = str(instance.definitionId)
                    
                    if process_key not in process_counts:
                        process_counts[process_key] = {"active": 0, "completed": 0}
                    process_counts[process_key]["active"] += 1
            
            # Count completed instances by process
            if completed_instances:
                for instance in completed_instances[:50]:  # Limit to avoid performance issues
                    process_key = instance.get('processDefinitionKey', 'unknown')
                    if not process_key or process_key == 'unknown':
                        definition_id = instance.get('processDefinitionId', '')
                        if definition_id and ':' in definition_id:
                            process_key = definition_id.split(':')[0]
                    
                    if process_key not in process_counts:
                        process_counts[process_key] = {"active": 0, "completed": 0}
                    process_counts[process_key]["completed"] += 1
            
            # Display process breakdown
            if process_counts:
                process_data = []
                for process_key, counts in process_counts.items():
                    process_data.append({
                        "Process": process_key,
                        "Active": counts["active"],
                        "Completed": counts["completed"],
                        "Total": counts["active"] + counts["completed"]
                    })
                
                st.dataframe(process_data, width='stretch')
        
        # Active Process Instances
        st.markdown("#### 🔄 Active Process Instances")
        try:
            active_instances = camunda_service.client.get_process_instances()
            
            if active_instances:
                instance_data = []
                for instance in active_instances:
                    # Extract process key from definitionId (format: "processKey:version:id")
                    process_key = "unknown"
                    if hasattr(instance, 'definitionId') and instance.definitionId:
                        try:
                            process_key = instance.definitionId.split(':')[0]
                        except:
                            process_key = instance.definitionId
                    
                    instance_data.append({
                        "Instance ID": instance.id,
                        "Process": process_key,
                        "Business Key": instance.businessKey or "N/A",
                        "Suspended": "Yes" if instance.suspended else "No"
                    })
                
                st.dataframe(instance_data, width='stretch')
            else:
                st.info("No active process instances")
                
        except Exception as e:
            st.error(f"Failed to load active instances: {str(e)}")
            logger.error(f"Active instances error: {e}")
            st.code(traceback.format_exc())
        
        # Process History
        st.markdown("#### 📜 Process History (Last 10)")
        try:
            history = camunda_service.client.get_history_process_instances()
            
            if history:
                # Process raw JSON history data
                history_data = []
                for hist_item in history[:10]:  # Take first 10
                    # Extract process key from processDefinitionKey or processDefinitionId
                    process_key = hist_item.get('processDefinitionKey', 'unknown')
                    if not process_key or process_key == 'unknown':
                        definition_id = hist_item.get('processDefinitionId', '')
                        if definition_id and ':' in definition_id:
                            process_key = definition_id.split(':')[0]
                    
                    # Parse timestamps
                    start_time = hist_item.get('startTime', 'N/A')
                    end_time = hist_item.get('endTime', 'N/A')
                    duration = hist_item.get('durationInMillis')
                    
                    # Format duration
                    duration_text = "N/A"
                    if duration:
                        duration_seconds = duration / 1000
                        if duration_seconds < 60:
                            duration_text = f"{duration_seconds:.1f}s"
                        else:
                            duration_text = f"{duration_seconds/60:.1f}min"
                    
                    history_data.append({
                        "Process": process_key,
                        "Started": start_time,
                        "Ended": end_time,
                        "Duration": duration_text,
                        "Business Key": hist_item.get('businessKey', 'N/A') or 'N/A',
                        "State": hist_item.get('state', 'COMPLETED')
                    })
                
                st.dataframe(history_data, width='stretch')
            else:
                st.info("No process history found")
                
        except Exception as e:
            st.error(f"Failed to load process history: {str(e)}")
            
    except Exception as e:
        st.error(f"Failed to load statistics: {str(e)}")