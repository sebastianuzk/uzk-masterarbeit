#!/usr/bin/env python3
"""
Test Script für den erweiterten BPMNEngineManager
Testet das Laden von BPMN-Dateien aus einem Ordner
"""

import sys
import logging
from pathlib import Path

# Füge src-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bpmn_engine.integration import BPMNEngineManager

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_directory_loading():
    """Test des Ordner-basiertes Laden"""
    print("🚀 Testing BPMN Engine Manager with Directory Loading")
    print("=" * 70)
    
    # Erstelle Manager mit Ordner-Konfiguration
    manager = BPMNEngineManager(
        db_path="test_bpmn_engine.db",
        processes_directory="bpmn_processes"
    )
    
    print("\n📁 Starting engine (should load from directory)...")
    manager.start()
    
    # Statistiken abrufen
    print("\n📊 Process Statistics:")
    stats = manager.get_process_statistics()
    
    for key, value in stats.items():
        if key == 'file_details':
            print(f"   📋 {key}: {len(value)} files")
            for file_info in value:
                print(f"      📄 {file_info['file']}: {file_info['name']}")
        elif key == 'changed_files':
            print(f"   🔄 {key}: {len(value)} changed files")
        else:
            print(f"   📊 {key}: {value}")
    
    # Verfügbare Dateien
    print("\n📂 Available Process Files:")
    available_files = manager.get_available_process_files()
    for file_info in available_files:
        print(f"   📄 {file_info['file']}: {file_info['name']} (ID: {file_info['id']})")
    
    # Engine Status
    print("\n⚙️ Engine Status:")
    engine_status = manager.get_engine_status()
    for key, value in engine_status.items():
        print(f"   ⚙️ {key}: {value}")
    
    # Test Prozess-Start wenn verfügbar
    deployed_processes = manager.execution_engine.process_definitions
    if deployed_processes:
        first_process = list(deployed_processes.keys())[0]
        print(f"\n🚀 Testing process start with: {first_process}")
        
        try:
            instance_id = manager.start_process_instance(
                first_process,
                {
                    'student_name': 'Max Mustermann',
                    'studiengang': 'Informatik',
                    'bewerbung_gueltig': True
                }
            )
            print(f"   ✅ Started process instance: {instance_id}")
            
            # Aktive Tasks
            active_tasks = manager.get_active_tasks()
            print(f"   📋 Active tasks: {len(active_tasks)}")
            for task in active_tasks:
                print(f"      🔸 {task.id}: {task.task_definition.name}")
                
        except Exception as e:
            print(f"   ❌ Error starting process: {e}")
    
    print("\n🛑 Stopping engine...")
    manager.stop()
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    try:
        test_directory_loading()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)