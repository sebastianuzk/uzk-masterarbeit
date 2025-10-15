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
                            if camunda_service.wait_for_engine(timeout=120):
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
            
            # Get engine info
            try:
                engine_status = camunda_service.get_engine_status()
                if engine_status["running"]:
                    engine_info = engine_status["engine_info"]
                    st.write(f"**Name:** {engine_info['name']}")
                    st.write(f"**Version:** {engine_info['version']}")
                    st.write(f"**Process Definitions:** {engine_status['process_definitions']}")
                    st.write(f"**Active Instances:** {engine_status['active_instances']}")
                    st.write(f"**Open Tasks:** {engine_status['open_tasks']}")
                    
                    # Camunda UI Links
                    st.markdown("#### 🌐 Camunda Web Apps")
                    st.markdown("**Cockpit:** [http://localhost:8080/camunda/app/cockpit/](http://localhost:8080/camunda/app/cockpit/)")
                    st.markdown("**Tasklist:** [http://localhost:8080/camunda/app/tasklist/](http://localhost:8080/camunda/app/tasklist/)")
                    st.markdown("**Admin:** [http://localhost:8080/camunda/app/admin/](http://localhost:8080/camunda/app/admin/)")
                    st.markdown("**Login:** demo / demo")
                    
                else:
                    st.error(f"Engine Error: {engine_status.get('error', 'Unknown error')}")
                    
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
            process_definitions = camunda_service.get_process_definitions()
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
            process_definitions = camunda_service.get_process_definitions()
            
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
                    
                    # Show required fields from BPMN
                    try:
                        from src.camunda_integration.services.form_validator import load_required_fields_from_bpmn
                        bpmn_file = camunda_service.bpmn_dir / f"{selected_process_key}.bpmn"
                        if bpmn_file.exists():
                            required_fields = load_required_fields_from_bpmn(bpmn_file)
                            if required_fields:
                                st.markdown("**Required Fields:**")
                                for field in required_fields:
                                    if field.get('required'):
                                        field_info = f"- `{field['id']}` ({field.get('type', 'string')})"
                                        if field.get('label'):
                                            field_info += f": {field['label']}"
                                        st.markdown(field_info)
                                
                                # Generate example JSON
                                example_vars = {}
                                for field in required_fields:
                                    if field.get('required'):
                                        if field['type'] == 'string':
                                            example_vars[field['id']] = f"Beispiel für {field['id']}"
                                        elif field['type'] == 'long':
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
        process_definitions = camunda_service.get_process_definitions()
        
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
            
            st.dataframe(process_data, use_container_width=True)
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
        tasks = camunda_service.get_tasks()
        
        if tasks:
            st.markdown(f"#### 📋 Open Tasks ({len(tasks)})")
            
            # Task filters
            col1, col2 = st.columns(2)
            with col1:
                assignee_filter = st.text_input("Filter by Assignee")
            with col2:
                process_filter = st.selectbox("Filter by Process", 
                                            ["All"] + list(set([t.get("processInstanceId", "unknown") for t in tasks])))
            
            # Filter tasks
            filtered_tasks = tasks
            if assignee_filter:
                filtered_tasks = [t for t in filtered_tasks if t.get("assignee") and assignee_filter in t.get("assignee")]
            if process_filter != "All":
                filtered_tasks = [t for t in filtered_tasks if t.get("processInstanceId") == process_filter]
            
            # Display tasks
            for task in filtered_tasks:
                with st.expander(f"📌 {task.get('name') or task.get('id')} - {task.get('assignee') or 'Unassigned'}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Task ID:** {task.get('id')}")
                        st.write(f"**Name:** {task.get('name') or 'N/A'}")
                        st.write(f"**Assignee:** {task.get('assignee') or 'Unassigned'}")
                        st.write(f"**Process Instance:** {task.get('processInstanceId') or 'N/A'}")
                        
                    with col2:
                        # Task completion
                        st.markdown("**Complete Task:**")
                        
                        # Task variables
                        task_variables = st.text_area(
                            "Completion Variables (JSON)",
                            '{}',
                            key=f"vars_{task.get('id')}",
                            height=80
                        )
                        
                        if st.button("✅ Complete Task", key=f"complete_{task.get('id')}"):
                            try:
                                variables = {}
                                if task_variables.strip():
                                    import json
                                    variables = json.loads(task_variables)
                                
                                camunda_service.complete_task(task.get('id'), variables)
                                st.success(f"✅ Task {task.get('id')} completed!")
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
        stats = camunda_service.get_statistics()
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Process Definitions", stats["process_definitions"])
        with col2:
            st.metric("Active Instances", stats["active_instances"])
        with col3:
            st.metric("Completed Instances", stats["completed_instances"])
        with col4:
            st.metric("Open Tasks", stats["open_tasks"])
        
        # Process breakdown
        if stats["by_process"]:
            st.markdown("#### 📈 Processes Breakdown")
            
            process_data = []
            for process_key, counts in stats["by_process"].items():
                process_data.append({
                    "Process": process_key,
                    "Active": counts["active"],
                    "Completed": counts["completed"],
                    "Total": counts["active"] + counts["completed"]
                })
            
            st.dataframe(process_data, use_container_width=True)
        
        # Active Process Instances
        st.markdown("#### 🔄 Active Process Instances")
        try:
            active_instances = camunda_service.get_active_processes()
            
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
                
                st.dataframe(instance_data, use_container_width=True)
            else:
                st.info("No active process instances")
                
        except Exception as e:
            st.error(f"Failed to load active instances: {str(e)}")
            logger.error(f"Active instances error: {e}")
            st.code(traceback.format_exc())
        
        # Process History
        st.markdown("#### 📜 Process History (Last 10)")
        try:
            history = camunda_service.get_process_history()
            
            if history:
                # Show last 10 - angepasst an tatsächliche Struktur
                recent_history = history[:10]  # Backend liefert bereits sortiert
                
                history_data = []
                for hist in recent_history:
                    # Extract process key from definitionId
                    process_key = "unknown"
                    if hasattr(hist, 'definitionId') and hist.definitionId:
                        try:
                            process_key = hist.definitionId.split(':')[0]
                        except:
                            process_key = hist.definitionId
                    
                    # Backend liefert andere Attribute als erwartet
                    start_time_str = "N/A"
                    end_time_str = "N/A"
                    
                    if hasattr(hist, 'startTime') and hist.startTime:
                        start_time_str = hist.startTime
                    elif hasattr(hist, 'start_time') and hist.start_time:
                        start_time_str = hist.start_time.strftime('%Y-%m-%d %H:%M') if hasattr(hist.start_time, 'strftime') else str(hist.start_time)
                    
                    if hasattr(hist, 'endTime') and hist.endTime:
                        end_time_str = hist.endTime
                    elif hasattr(hist, 'end_time') and hist.end_time:
                        end_time_str = hist.end_time.strftime('%Y-%m-%d %H:%M') if hasattr(hist.end_time, 'strftime') else str(hist.end_time)
                    
                    duration = ""
                    if hasattr(hist, 'durationInMillis') and hist.durationInMillis:
                        duration_sec = hist.durationInMillis / 1000
                        duration = f"{duration_sec:.1f}s"
                    elif hasattr(hist, 'duration_in_millis') and hist.duration_in_millis:
                        duration_sec = hist.duration_in_millis / 1000
                        duration = f"{duration_sec:.1f}s"
                    
                    history_data.append({
                        "Process": process_key,
                        "Started": start_time_str,
                        "Ended": end_time_str,
                        "Duration": duration,
                        "Business Key": getattr(hist, 'businessKey', getattr(hist, 'business_key', "N/A")) or "N/A",
                        "State": getattr(hist, 'state', "COMPLETED")
                    })
                
                st.dataframe(history_data, use_container_width=True)
            else:
                st.info("No process history found")
                
        except Exception as e:
            st.error(f"Failed to load process history: {str(e)}")
            logger.error(f"Process history error: {e}")
            st.code(traceback.format_exc())
            
    except Exception as e:
        st.error(f"Failed to load statistics: {str(e)}")
        st.code(traceback.format_exc())