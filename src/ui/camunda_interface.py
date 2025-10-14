"""
Camunda Engine Interface for Streamlit

Provides UI components for Camunda Platform 7 management.
"""

import streamlit as st
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback

from ..camunda_integration.services.camunda_service import CamundaService
from ..camunda_integration.services.docker_manager import DockerManager


logger = logging.getLogger(__name__)


def get_camunda_service() -> CamundaService:
    """
    Get Camunda service instance from session state
    
    Returns:
        CamundaService instance
    """
    if 'camunda_service' in st.session_state:
        return st.session_state.camunda_service
    else:
        st.error("Camunda Service nicht initialisiert. Bitte laden Sie die App neu.")
        # Fallback
        auto_deploy_dir = "src/process_automation/deployed_processes"
        return CamundaService(auto_deploy_dir=auto_deploy_dir)


def get_docker_manager() -> DockerManager:
    """
    Get Docker manager instance from session state
    
    Returns:
        DockerManager instance
    """
    if 'docker_manager' in st.session_state:
        return st.session_state.docker_manager
    else:
        st.error("Docker Manager nicht initialisiert. Bitte laden Sie die App neu.")
        # Fallback
        return DockerManager()


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
        st.markdown("#### 📤 BPMN Deployment")
        
        # Auto-deploy from directory
        if st.button("🔄 Auto-Deploy from Directory", type="primary"):
            with st.spinner("Deploying BPMN files..."):
                try:
                    results = camunda_service.deploy_from_directory()
                    if results:
                        st.success(f"✅ {len(results)} BPMN files deployed!")
                        for result in results:
                            st.write(f"- {result.name} (ID: {result.id})")
                    else:
                        st.info("No BPMN files found in deployment directory")
                except Exception as e:
                    st.error(f"Deployment failed: {str(e)}")
        
        # Manual file upload
        uploaded_file = st.file_uploader("Upload BPMN file", type=['bpmn', 'xml'])
        if uploaded_file is not None:
            if st.button("Deploy Uploaded File"):
                with st.spinner("Deploying..."):
                    try:
                        # Save uploaded file temporarily
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.bpmn') as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_file_path = tmp_file.name
                        
                        result = camunda_service.deploy_file(tmp_file_path, uploaded_file.name)
                        st.success(f"✅ Deployed: {result.name}")
                        
                        # Cleanup
                        import os
                        os.unlink(tmp_file_path)
                        
                    except Exception as e:
                        st.error(f"Deployment failed: {str(e)}")
    
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
                    variables_text = st.text_area("Variables", '{"key": "value"}', height=100)
                    
                    if st.button("🚀 Start Process Instance"):
                        try:
                            variables = {}
                            if variables_text.strip():
                                import json
                                variables = json.loads(variables_text)
                            
                            instance = camunda_service.start_process(
                                selected_process_key, 
                                variables, 
                                business_key if business_key else None
                            )
                            st.success(f"✅ Process started! Instance ID: {instance.id}")
                            
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
                                            ["All"] + list(set([t.process_definition_id for t in tasks])))
            
            # Filter tasks
            filtered_tasks = tasks
            if assignee_filter:
                filtered_tasks = [t for t in filtered_tasks if t.assignee and assignee_filter in t.assignee]
            if process_filter != "All":
                filtered_tasks = [t for t in filtered_tasks if t.process_definition_id == process_filter]
            
            # Display tasks
            for task in filtered_tasks:
                with st.expander(f"📌 {task.name or task.id} - {task.assignee or 'Unassigned'}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Task ID:** {task.id}")
                        st.write(f"**Name:** {task.name or 'N/A'}")
                        st.write(f"**Assignee:** {task.assignee or 'Unassigned'}")
                        st.write(f"**Created:** {task.created.strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Process:** {task.process_definition_id}")
                        
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
                    instance_data.append({
                        "Instance ID": instance.id,
                        "Process": instance.definition_id,
                        "Business Key": instance.business_key or "N/A",
                        "Suspended": "Yes" if instance.suspended else "No"
                    })
                
                st.dataframe(instance_data, use_container_width=True)
            else:
                st.info("No active process instances")
                
        except Exception as e:
            st.error(f"Failed to load active instances: {str(e)}")
        
        # Process History
        st.markdown("#### 📜 Process History (Last 10)")
        try:
            history = camunda_service.get_process_history()
            
            if history:
                # Show last 10
                recent_history = sorted(history, key=lambda x: x.start_time, reverse=True)[:10]
                
                history_data = []
                for hist in recent_history:
                    duration = ""
                    if hist.duration_in_millis:
                        duration_sec = hist.duration_in_millis / 1000
                        duration = f"{duration_sec:.1f}s"
                    
                    history_data.append({
                        "Process": hist.process_definition_key,
                        "Started": hist.start_time.strftime('%Y-%m-%d %H:%M'),
                        "Ended": hist.end_time.strftime('%Y-%m-%d %H:%M') if hist.end_time else "N/A",
                        "Duration": duration,
                        "Business Key": hist.business_key or "N/A",
                        "State": hist.state
                    })
                
                st.dataframe(history_data, use_container_width=True)
            else:
                st.info("No process history found")
                
        except Exception as e:
            st.error(f"Failed to load process history: {str(e)}")
            
    except Exception as e:
        st.error(f"Failed to load statistics: {str(e)}")
        st.code(traceback.format_exc())