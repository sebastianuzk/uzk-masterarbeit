#!/usr/bin/env python3
"""
Ultra-minimaler Streamlit Test
"""
import streamlit as st
import sys
import os

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

st.title("🔧 Ultra-minimal Test")

try:
    st.write("Step 1: Basic imports...")
    from pathlib import Path
    from config.settings import settings
    st.success("✅ Basic imports OK")
    
    st.write("Step 2: Camunda client...")
    from src.camunda_integration.client.camunda_client import CamundaClient
    client = CamundaClient(settings.CAMUNDA_BASE_URL)
    st.success("✅ Camunda client OK")
    
    st.write("Step 3: Camunda service...")
    from src.camunda_integration.services.camunda_service import CamundaService
    bpmn_dir = Path("src/camunda_integration/bpmn_processes")
    service = CamundaService(client=client, bpmn_dir=bpmn_dir)
    st.success("✅ Camunda service OK")
    
    st.write("Step 4: Docker manager...")
    from src.camunda_integration.services.docker_manager import DockerManager
    compose_file = Path("src/camunda_integration/docker/docker-compose.yml")
    docker_manager = DockerManager(compose_file=compose_file)
    st.success("✅ Docker manager OK")
    
    st.write("Step 5: Test methods...")
    engine_running = service.is_engine_running()
    docker_available = docker_manager.is_docker_available()
    st.success(f"✅ Engine: {engine_running}, Docker: {docker_available}")
    
    st.write("Step 6: UI interface import...")
    from src.ui.camunda_interface import get_camunda_service, get_docker_manager
    st.success("✅ Interface functions imported")
    
    st.write("Step 7: Creating services via interface...")
    svc = get_camunda_service()
    mgr = get_docker_manager()
    st.success("✅ Services created via interface")
    
    # Stop here for now - don't call display function yet
    st.info("All steps completed successfully!")
    
except Exception as e:
    st.error(f"❌ Error at step: {e}")
    import traceback
    st.text(traceback.format_exc())