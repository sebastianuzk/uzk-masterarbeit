"""
Streamlit Interface für die BPMN Process Engine
"""
import streamlit as st
import json
from datetime import datetime
from typing import Dict, List, Optional

from src.bpmn_engine.integration import get_bpmn_engine
from src.bpmn_engine.engine import ProcessInstance, TaskInstance


def display_bpmn_engine_interface():
    """Zeige BPMN Process Engine Management Interface"""
    st.markdown("### 🔄 BPMN Process Engine Management")
    st.markdown("Verwalten Sie BPMN-Prozesse und Tasks über die echte BPMN 2.0 konforme Process Engine.")
    
    try:
        bpmn_manager = get_bpmn_engine()
        
        # Haupttabs für verschiedene Bereiche
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Dashboard", 
            "🚀 Prozess starten", 
            "📋 Tasks verwalten", 
            "🔍 Engine Details"
        ])
        
        with tab1:
            display_dashboard(bpmn_manager)
        
        with tab2:
            display_start_process(bpmn_manager)
        
        with tab3:
            display_task_management(bpmn_manager)
        
        with tab4:
            display_engine_details(bpmn_manager)
            
    except Exception as e:
        st.error(f"❌ Fehler beim Laden der BPMN Engine: {str(e)}")


def display_dashboard(bpmn_manager):
    """Zeige Dashboard mit Übersicht"""
    st.markdown("#### 📊 Process Engine Dashboard")
    
    try:
        # Hole alle Process Instances
        instances = bpmn_manager.execution_engine.get_active_instances()
        
        # Statistiken
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Gesamt Prozesse", len(instances))
        
        with col2:
            active_count = len([i for i in instances if i.status == 'ACTIVE'])
            st.metric("Aktive Prozesse", active_count)
        
        with col3:
            completed_count = len([i for i in instances if i.status == 'COMPLETED'])
            st.metric("Abgeschlossen", completed_count)
        
        with col4:
            # Hole alle Tasks
            all_tasks = []
            for instance in instances:
                if instance.status == 'ACTIVE':
                    tasks = bpmn_manager.get_tasks_for_instance(instance.instance_id)
                    all_tasks.extend([t for t in tasks if t.status == 'ACTIVE'])
            st.metric("Offene Tasks", len(all_tasks))
        
        st.markdown("---")
        
        # Aktive Prozesse anzeigen
        if instances:
            st.markdown("#### 🔄 Aktuelle Prozess-Instanzen")
            
            # Erstelle DataFrame für bessere Darstellung
            instance_data = []
            for instance in instances:
                tasks = bpmn_manager.get_tasks_for_instance(instance.instance_id)
                active_tasks = [t for t in tasks if t.status == 'ACTIVE']
                
                instance_data.append({
                    "Instance ID": instance.instance_id[:12] + "...",
                    "Prozess": instance.process_definition_id,
                    "Status": instance.status,
                    "Gestartet": instance.start_time.strftime("%Y-%m-%d %H:%M") if instance.start_time else "N/A",
                    "Aktive Tasks": len(active_tasks),
                    "Variablen": len(instance.variables) if instance.variables else 0
                })
            
            st.dataframe(instance_data, use_container_width=True)
            
        else:
            st.info("Noch keine Prozess-Instanzen vorhanden. Starten Sie einen neuen Prozess im 'Prozess starten' Tab.")
    
    except Exception as e:
        st.error(f"Fehler beim Laden des Dashboards: {str(e)}")


def display_start_process(bpmn_manager):
    """Interface zum Starten neuer Prozesse"""
    st.markdown("#### 🚀 Neuen BPMN-Prozess starten")
    
    try:
        # Verfügbare Prozesse anzeigen
        available_processes = list(bpmn_manager.execution_engine.process_definitions.keys())
        
        if not available_processes:
            st.warning("Keine BPMN-Prozesse verfügbar. Der Engine-Manager sollte automatisch einen Bewerbungsprozess bereitstellen.")
            return
        
        st.markdown("**Verfügbare Prozesse:**")
        for process_id in available_processes:
            st.write(f"• `{process_id}`")
        
        st.markdown("---")
        
        # Bewerbungsprozess-Formular
        st.markdown("#### 📝 Bewerbungsprozess starten")
        
        with st.form("start_bewerbung_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                student_name = st.text_input(
                    "Name des Studierenden *",
                    placeholder="z.B. Max Mustermann"
                )
            
            with col2:
                studiengang = st.selectbox(
                    "Studiengang *",
                    ["", "Betriebswirtschaftslehre", "Volkswirtschaftslehre", "Wirtschaftsinformatik", 
                     "Medienkulturwissenschaft", "Sozialwissenschaften", "Business Administration"]
                )
            
            email = st.text_input(
                "E-Mail (optional)",
                placeholder="max.mustermann@example.com"
            )
            
            submitted = st.form_submit_button("🚀 Bewerbungsprozess starten")
            
            if submitted:
                if not student_name or not studiengang:
                    st.error("Bitte füllen Sie alle Pflichtfelder (*) aus.")
                else:
                    try:
                        # Starte Bewerbungsprozess
                        result = bpmn_manager.start_bewerbung_process(
                            student_name=student_name,
                            studiengang=studiengang,
                            email=email if email else None
                        )
                        
                        st.success("✅ Bewerbungsprozess erfolgreich gestartet!")
                        st.json(result)
                        
                        # Auto-refresh nach 2 Sekunden
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Fehler beim Starten des Prozesses: {str(e)}")
        
        st.markdown("---")
        
        # Manueller Prozessstart (für Entwickler)
        with st.expander("🔧 Erweitert: Manueller Prozessstart"):
            process_id = st.selectbox(
                "Prozess ID",
                available_processes
            )
            
            variables_json = st.text_area(
                "Prozessvariablen (JSON)",
                value='{\n  "student_name": "Test Student",\n  "studiengang": "Betriebswirtschaftslehre"\n}',
                height=100
            )
            
            if st.button("Manual Start"):
                try:
                    variables = json.loads(variables_json) if variables_json.strip() else {}
                    result = bpmn_manager.execution_engine.start_process(process_id, variables)
                    st.success(f"✅ Prozess gestartet: {result.instance_id}")
                    st.json({
                        "instance_id": result.instance_id,
                        "status": result.status,
                        "variables": result.variables
                    })
                except json.JSONDecodeError:
                    st.error("❌ Ungültiges JSON in Prozessvariablen")
                except Exception as e:
                    st.error(f"❌ Fehler: {str(e)}")
    
    except Exception as e:
        st.error(f"Fehler beim Anzeigen der Prozessstart-Optionen: {str(e)}")


def display_task_management(bpmn_manager):
    """Interface für Task-Management"""
    st.markdown("#### 📋 Task Management")
    
    try:
        # Hole alle aktiven Tasks
        instances = bpmn_manager.execution_engine.get_active_instances()
        all_active_tasks = []
        
        for instance in instances:
            if instance.status == 'ACTIVE':
                tasks = bpmn_manager.get_tasks_for_instance(instance.instance_id)
                for task in tasks:
                    if task.status == 'ACTIVE':
                        all_active_tasks.append((instance, task))
        
        if not all_active_tasks:
            st.info("Keine aktiven Tasks vorhanden.")
            return
        
        st.markdown(f"**{len(all_active_tasks)} aktive Tasks gefunden:**")
        
        # Tasks anzeigen und bearbeiten
        for i, (instance, task) in enumerate(all_active_tasks):
            with st.expander(f"📋 {task.task_definition.id} - {task.id[:12]}..."):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Task ID:** `{task.id}`")
                    st.write(f"**Prozess Instance:** `{instance.instance_id}`")
                    st.write(f"**Task Type:** {task.task_definition.id}")
                    st.write(f"**Status:** {task.status}")
                    if task.created_at:
                        st.write(f"**Erstellt:** {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Zeige Prozessvariablen
                    if instance.variables:
                        st.markdown("**Prozessvariablen:**")
                        st.json(instance.variables)
                
                with col2:
                    # Task abschließen
                    if task.task_definition.id == "Angaben prüfen":
                        st.markdown("**Angaben-Prüfung abschließen:**")
                        
                        with st.form(f"complete_task_{i}"):
                            email = st.text_input(
                                "E-Mail für Bestätigung",
                                value=instance.variables.get('email', '') if instance.variables else ''
                            )
                            
                            approved = st.selectbox(
                                "Angaben korrekt?",
                                ["", "Ja", "Nein"]
                            )
                            
                            submitted = st.form_submit_button("✅ Task abschließen")
                            
                            if submitted and approved:
                                try:
                                    result = bpmn_manager.complete_angaben_pruefen(
                                        task_id=task.id,
                                        student_email=email,
                                        bewerbung_gueltig=(approved == "Ja")
                                    )
                                    
                                    st.success("✅ Task erfolgreich abgeschlossen!")
                                    st.json(result)
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Fehler: {str(e)}")
                    
                    else:
                        # Generisches Task-Complete
                        st.markdown("**Task abschließen:**")
                        variables_json = st.text_area(
                            "Task-Variablen (JSON)",
                            value='{}',
                            height=80,
                            key=f"vars_{i}"
                        )
                        
                        if st.button(f"✅ Complete Task", key=f"complete_{i}"):
                            try:
                                variables = json.loads(variables_json) if variables_json.strip() else {}
                                bpmn_manager.execution_engine.complete_task(task.id, variables)
                                st.success("✅ Task abgeschlossen!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Fehler: {str(e)}")
    
    except Exception as e:
        st.error(f"Fehler beim Task-Management: {str(e)}")


def display_engine_details(bpmn_manager):
    """Zeige detaillierte Engine-Informationen"""
    st.markdown("#### 🔍 BPMN Engine Details")
    
    try:
        # Engine-Informationen
        st.markdown("##### 🔧 Engine-Konfiguration")
        st.json({
            "engine_type": "BPMN 2.0 Process Engine",
            "parser": "XML ElementTree Parser",
            "execution_model": "Token-based",
            "persistence": "SQLite Database",
            "database_file": str(bpmn_manager.execution_engine.db_file)
        })
        
        # Verfügbare Prozesse
        st.markdown("##### 📋 Verfügbare Prozessdefinitionen")
        available = list(bpmn_manager.execution_engine.process_definitions.keys())
        for process_id in available:
            with st.expander(f"📄 {process_id}"):
                try:
                    process_def = bpmn_manager.execution_engine.process_definitions.get(process_id)
                    if process_def:
                        st.write(f"**Prozess ID:** {process_def.id}")
                        st.write(f"**Elemente:** {len(process_def.elements)}")
                        
                        # Zeige Prozess-Elemente
                        st.markdown("**BPMN Elemente:**")
                        for elem_id, element in process_def.elements.items():
                            st.write(f"• `{elem_id}` - {element.__class__.__name__}")
                    else:
                        st.warning("Prozessdefinition nicht geladen")
                except Exception as e:
                    st.error(f"Fehler beim Laden der Prozessdefinition: {str(e)}")
        
        # Raw Database Content (für Debugging)
        with st.expander("🗄️ Database Content (Debug)"):
            if st.button("📊 Show Database Tables"):
                try:
                    # Zeige Process Instances
                    st.markdown("**Process Instances:**")
                    instances = bpmn_manager.execution_engine.get_active_instances()
                    instances_data = []
                    for inst in instances:
                        instances_data.append({
                            "ID": inst.instance_id[:12] + "...",
                            "Process": inst.process_definition_id,
                            "Status": inst.status,
                            "Started": inst.start_time.isoformat() if inst.start_time else None,
                            "Variables": str(inst.variables)[:50] + "..." if inst.variables else None
                        })
                    st.dataframe(instances_data)
                    
                    # Zeige Tasks
                    st.markdown("**Task Instances:**")
                    all_tasks = []
                    for instance in instances:
                        tasks = bpmn_manager.get_tasks_for_instance(instance.instance_id)
                        for task in tasks:
                            all_tasks.append({
                                "Task ID": task.id[:12] + "...",
                                "Instance": task.process_instance_id[:12] + "...",
                                "Definition": task.task_definition.id,
                                "Status": task.status,
                                "Created": task.created_at.isoformat() if task.created_at else None
                            })
                    st.dataframe(all_tasks)
                    
                except Exception as e:
                    st.error(f"Fehler beim Anzeigen der Datenbank: {str(e)}")
    
    except Exception as e:
        st.error(f"Fehler beim Anzeigen der Engine-Details: {str(e)}")
