#!/usr/bin/env python3
"""
Minimaler Streamlit Test für Camunda Interface Debug
"""
import streamlit as st
import sys
import os
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

st.title("🔧 Camunda Interface Debug Test")

try:
    st.write("Testing imports...")
    
    from src.ui.camunda_interface import get_camunda_service, get_docker_manager
    st.success("✅ Camunda interface imports OK")
    
    st.write("Testing service creation...")
    camunda_service = get_camunda_service()
    docker_manager = get_docker_manager()
    st.success("✅ Services created successfully")
    
    st.write("Testing service methods...")
    engine_running = camunda_service.is_engine_running()
    docker_available = docker_manager.is_docker_available()
    
    st.success(f"✅ Engine running: {engine_running}")
    st.success(f"✅ Docker available: {docker_available}")
    
    st.write("Testing display function import...")
    from src.ui.camunda_interface import display_camunda_engine_interface
    st.success("✅ Display function imported")
    
    st.write("Testing display function execution...")
    display_camunda_engine_interface()
    st.success("✅ Display function executed")
    
except Exception as e:
    st.error(f"❌ Error: {e}")
    st.text(f"Error details: {str(e)}")
    import traceback
    st.text(traceback.format_exc())