"""
Streamlit Interface für CAMUNDA Process Engine
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import json
from src.process_engine.camunda_engine import get_engine, start_engine
import logging

logger = logging.getLogger(__name__)


def display_process_engine_interface():
    """Zeige Process Engine Interface"""
    st.header("🔄 CAMUNDA Process Engine")
    
    # Engine Status
    engine = get_engine()
    status = engine.get_status()
    
    # Status-Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if status['running']:
            st.success("✅ Engine läuft")
        else:
            st.error("❌ Engine gestoppt")
    
    with col2:
        st.info(f"🔧 {status['engine_type']} Engine")
    
    with col3:
        st.metric("Aktive Prozesse", status['active_instances'])
    
    with col4:
        st.metric("Gesamt Prozesse", status['total_instances'])
    
    # Engine Controls
    st.subheader("Engine Kontrolle")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Engine starten", disabled=status['running']):
            try:
                start_engine()
                st.success("Engine gestartet!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Starten: {e}")
    
    with col2:
        if st.button("🛑 Engine stoppen", disabled=not status['running']):
            try:
                engine.stop()
                st.success("Engine gestoppt!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Stoppen: {e}")
    
    if not status['running']:
        st.warning("⚠️ Starten Sie die Engine um Prozesse zu verwalten")
        return
    
    # Tabs für verschiedene Bereiche
    tab1, tab2, tab3 = st.tabs(["🆕 Neuer Prozess", "📋 Aktive Prozesse", "📊 Alle Prozesse"])
    
    with tab1:
        display_new_process_form(engine)
    
    with tab2:
        display_active_processes(engine)
    
    with tab3:
        display_all_processes(engine)


def display_new_process_form(engine):
    """Formular für neuen Bewerbungsprozess"""
    st.subheader("Neuen Bewerbungsprozess starten")
    
    with st.form("new_bewerbung", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            student_name = st.text_input(
                "Name des Studierenden *", 
                placeholder="Max Mustermann"
            )
        
        with col2:
            studiengang = st.text_input(
                "Studiengang *", 
                placeholder="Informatik Master"
            )
        
        submitted = st.form_submit_button("📝 Bewerbungsprozess starten")
        
        if submitted:
            if not student_name or not studiengang:
                st.error("Bitte füllen Sie alle Pflichtfelder aus!")
            else:
                try:
                    instance_id = engine.start_bewerbung_process(student_name, studiengang)
                    st.success(f"✅ Bewerbungsprozess gestartet!")
                    st.info(f"Process Instance ID: {instance_id}")
                    st.info("Nächster Schritt: Angaben prüfen")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")


def display_active_processes(engine):
    """Zeige aktive Prozesse"""
    st.subheader("Aktive Bewerbungsprozesse")
    
    active_instances = engine.get_active_instances()
    
    if not active_instances:
        st.info("Keine aktiven Prozesse vorhanden")
        return
    
    for instance in active_instances:
        with st.expander(f"Prozess {instance['id']} - {instance['variables'].get('student_name', 'Unbekannt')}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**Student:** {instance['variables'].get('student_name', 'N/A')}")
                st.write(f"**Studiengang:** {instance['variables'].get('studiengang', 'N/A')}")
                st.write(f"**Status:** {instance['status']}")
                st.write(f"**Aktueller Task:** {instance['current_task']}")
                st.write(f"**Gestartet:** {instance['created_at']}")
            
            with col2:
                if instance['current_task'] == 'angaben_pruefen':
                    st.write("**Nächster Schritt:**")
                    with st.form(f"complete_task_{instance['id']}", clear_on_submit=True):
                        student_email = st.text_input(
                            "E-Mail des Studenten", 
                            key=f"email_{instance['id']}",
                            placeholder="student@uni-koeln.de"
                        )
                        
                        if st.form_submit_button("✅ Angaben geprüft"):
                            if student_email:
                                try:
                                    engine.complete_angaben_pruefen(instance['id'], student_email)
                                    st.success("Task abgeschlossen!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler: {e}")
                            else:
                                st.error("E-Mail erforderlich!")


def display_all_processes(engine):
    """Zeige alle Prozesse in Tabelle"""
    st.subheader("Alle Bewerbungsprozesse")
    
    all_instances = engine.get_all_instances()
    
    if not all_instances:
        st.info("Keine Prozesse vorhanden")
        return
    
    # Konvertiere zu DataFrame für bessere Darstellung
    df_data = []
    for instance in all_instances:
        variables = instance.get('variables', {})
        df_data.append({
            'ID': instance['id'],
            'Student': variables.get('student_name', 'N/A'),
            'Studiengang': variables.get('studiengang', 'N/A'),
            'E-Mail': variables.get('student_email', 'N/A'),
            'Status': instance['status'],
            'Aktueller Task': instance.get('current_task', 'Beendet'),
            'Erstellt': instance['created_at'],
            'Aktualisiert': instance.get('updated_at', instance['created_at'])
        })
    
    df = pd.DataFrame(df_data)
    
    # Filtermöglichkeiten
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Status Filter", 
            ["Alle", "ACTIVE", "COMPLETED"],
            index=0
        )
    
    with col2:
        search_term = st.text_input("Suche (Name/Studiengang)", "")
    
    # Anwenden der Filter
    filtered_df = df.copy()
    if status_filter != "Alle":
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['Student'].str.contains(search_term, case=False, na=False) |
            filtered_df['Studiengang'].str.contains(search_term, case=False, na=False)
        ]
    
    # Tabelle anzeigen
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Statistiken
    if not filtered_df.empty:
        st.subheader("Statistiken")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Gefilterte Prozesse", len(filtered_df))
        
        with col2:
            active_count = len(filtered_df[filtered_df['Status'] == 'ACTIVE'])
            st.metric("Aktive Prozesse", active_count)
        
        with col3:
            completed_count = len(filtered_df[filtered_df['Status'] == 'COMPLETED'])
            st.metric("Abgeschlossene Prozesse", completed_count)
    
    # Export-Option
    if st.button("📥 Als CSV exportieren"):
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="CSV herunterladen",
            data=csv,
            file_name=f"bewerbungsprozesse_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )