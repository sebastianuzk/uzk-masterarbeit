"""
Process Engine Tool für LangChain Agent
"""
from langchain_core.tools import BaseTool
from typing import Dict, Any, Optional, List
import json
from src.process_engine.camunda_engine import get_engine, start_engine


class ProcessEngineStartTool(BaseTool):
    """Tool zum Starten neuer Bewerbungsprozesse"""
    
    name: str = "start_bewerbung_process"
    description: str = """
    Startet einen neuen Bewerbungsprozess in der CAMUNDA Process Engine.
    Darf erst erfolgen wenn der Name des Studierenden und die Bezeichnung des Studiengangs bekannt sind.
    
    Parameter:
    - student_name: Name des Studierenden (String)
    - studiengang: Bezeichnung des Studiengangs (String)
    
    Gibt die Process Instance ID zurück.
    """
    
    def _run(self, student_name: str, studiengang: str) -> str:
        try:
            engine = get_engine()
            if not engine.running:
                start_engine()
            
            instance_id = engine.start_bewerbung_process(student_name, studiengang)
            
            return json.dumps({
                "success": True,
                "instance_id": instance_id,
                "message": f"Bewerbungsprozess für {student_name} ({studiengang}) gestartet",
                "next_task": "angaben_pruefen"
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Fehler beim Starten des Bewerbungsprozesses: {e}"
            }, ensure_ascii=False)


class ProcessEngineCompleteTool(BaseTool):
    """Tool zum Abschließen von Tasks"""
    
    name: str = "complete_angaben_pruefen"
    description: str = """
    Schließt den 'Angaben prüfen' Task eines Bewerbungsprozesses ab.
    Benötigt die Process Instance ID und die E-Mail-Adresse des Studenten.
    
    Parameter:
    - instance_id: ID der Process Instance (Integer)
    - student_email: E-Mail-Adresse des Studenten (String)
    
    Schließt den Prozess ab.
    """
    
    def _run(self, instance_id: int, student_email: str) -> str:
        try:
            engine = get_engine()
            if not engine.running:
                return json.dumps({
                    "success": False,
                    "error": "Process Engine nicht gestartet",
                    "message": "Die Process Engine muss zuerst gestartet werden"
                }, ensure_ascii=False)
            
            # Konvertiere instance_id zu int falls String
            if isinstance(instance_id, str):
                instance_id = int(instance_id)
            
            engine.complete_angaben_pruefen(instance_id, student_email)
            
            return json.dumps({
                "success": True,
                "instance_id": instance_id,
                "message": f"Angaben-Prüfung abgeschlossen für Prozess {instance_id}",
                "status": "Bewerbungsprozess beendet"
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Fehler beim Abschließen des Tasks: {e}"
            }, ensure_ascii=False)


class ProcessEngineStatusTool(BaseTool):
    """Tool für Process Engine Status und Instance-Informationen"""
    
    name: str = "process_engine_status"
    description: str = """
    Zeigt den Status der Process Engine und laufende Prozesse an.
    Keine Parameter erforderlich.
    
    Gibt Informationen über:
    - Engine-Status
    - Aktive Process Instances
    - Alle Process Instances
    """
    
    def _run(self) -> str:
        try:
            engine = get_engine()
            
            status = engine.get_status()
            active_instances = engine.get_active_instances()
            all_instances = engine.get_all_instances()
            
            result = {
                "engine_status": status,
                "active_instances": active_instances,
                "total_instances": len(all_instances),
                "recent_instances": all_instances[:5]  # Zeige nur die letzten 5
            }
            
            return json.dumps(result, ensure_ascii=False, default=str)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Fehler beim Abrufen des Engine-Status: {e}"
            }, ensure_ascii=False)


class ProcessEngineInstanceTool(BaseTool):
    """Tool für Details einer spezifischen Process Instance"""
    
    name: str = "get_process_instance"
    description: str = """
    Holt Details einer spezifischen Process Instance.
    
    Parameter:
    - instance_id: ID der Process Instance (Integer)
    
    Gibt alle verfügbaren Informationen zur Instance zurück.
    """
    
    def _run(self, instance_id: int) -> str:
        try:
            engine = get_engine()
            if not engine.running:
                return json.dumps({
                    "success": False,
                    "error": "Process Engine nicht gestartet",
                    "message": "Die Process Engine muss zuerst gestartet werden"
                }, ensure_ascii=False)
            
            # Konvertiere instance_id zu int falls String
            if isinstance(instance_id, str):
                instance_id = int(instance_id)
            
            instance = engine.get_process_instance(instance_id)
            
            if instance:
                return json.dumps({
                    "success": True,
                    "instance": instance
                }, ensure_ascii=False, default=str)
            else:
                return json.dumps({
                    "success": False,
                    "error": "Instance nicht gefunden",
                    "message": f"Process Instance {instance_id} existiert nicht"
                }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Fehler beim Abrufen der Instance-Details: {e}"
            }, ensure_ascii=False)


def get_process_engine_tools() -> List[BaseTool]:
    """Hole alle Process Engine Tools"""
    return [
        ProcessEngineStartTool(),
        ProcessEngineCompleteTool(),
        ProcessEngineStatusTool(),
        ProcessEngineInstanceTool()
    ]