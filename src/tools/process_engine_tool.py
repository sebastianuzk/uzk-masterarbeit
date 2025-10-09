"""
Process Engine Integration Tool für React Agent
Ermöglicht automatische Workflow-Orchestrierung basierend auf Unterhaltungen
"""

from typing import Any, Dict, List, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# Direct imports ohne __init__.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from process_engine.workflow_manager import WorkflowManager
from process_engine.process_client import ProcessEngineClient
from process_engine.bpmn_generator import BPMNGenerator
from config.settings import Settings


class ProcessEngineToolInput(BaseModel):
    """Input Schema für Process Engine Tool"""
    action: str = Field(description="Aktion: 'analyze', 'start_workflow', 'status', 'list_workflows', 'generate_bpmn'")
    workflow_id: Optional[str] = Field(description="ID des Workflows (für start_workflow, status)")
    conversation_context: Optional[str] = Field(description="Unterhaltungskontext für Analyse")
    additional_data: Optional[Dict[str, Any]] = Field(description="Zusätzliche Daten für Workflow")


class ProcessEngineTool(BaseTool):
    """Tool für Process Engine Integration im React Agent"""
    
    name: str = "process_engine"
    description: str = """
    Automatisiert Universitätsprozesse durch intelligente Workflow-Orchestrierung.
    
    Aktionen:
    - analyze: Analysiert Unterhaltung auf relevante Prozesse
    - start_workflow: Startet einen spezifischen Workflow
    - status: Zeigt Status laufender Workflows
    - list_workflows: Listet verfügbare Workflows
    - generate_bpmn: Generiert BPMN-Definitionen
    
    Beispiele:
    - "Analysiere die Unterhaltung auf Universitätsprozesse" → action='analyze'
    - "Starte Zeugnis-Anfrage Workflow" → action='start_workflow', workflow_id='student_transcript_request'
    - "Zeige Status aller Workflows" → action='status'
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Verwende object.__setattr__ um Pydantic-Validierung zu umgehen
        object.__setattr__(self, 'settings', Settings())
        object.__setattr__(self, 'process_client', None)
        object.__setattr__(self, 'workflow_manager', None)
        object.__setattr__(self, 'bpmn_generator', BPMNGenerator())
        
        if self.settings.ENABLE_PROCESS_ENGINE:
            self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialisiert Process Engine Komponenten"""
        try:
            object.__setattr__(self, 'process_client', ProcessEngineClient())
            object.__setattr__(self, 'workflow_manager', WorkflowManager(self.process_client))
            
            # Generiere und deploye Standard-Workflows
            self._deploy_standard_workflows()
            
        except Exception as e:
            print(f"⚠️ Process Engine Initialisierung fehlgeschlagen: {e}")
            print("   Process Engine Funktionen sind eingeschränkt verfügbar.")
    
    def _deploy_standard_workflows(self):
        """Generiert und deployt Standard-BPMN-Workflows"""
        try:
            workflows = self.bpmn_generator.generate_all_university_workflows()
            
            for workflow_id, file_path in workflows.items():
                deployment = self.process_client.deploy_workflow(file_path)
                if deployment:
                    print(f"✅ Workflow deployed: {workflow_id}")
                else:
                    print(f"⚠️ Workflow deployment fehlgeschlagen: {workflow_id}")
                    
        except Exception as e:
            print(f"⚠️ Workflow Deployment Fehler: {e}")
    
    def _run(self, action: str, workflow_id: Optional[str] = None, 
             conversation_context: Optional[str] = None, 
             additional_data: Optional[Dict[str, Any]] = None) -> str:
        """Führt Process Engine Aktionen aus"""
        
        if not self.settings.ENABLE_PROCESS_ENGINE:
            return "❌ Process Engine ist deaktiviert. Aktivieren Sie ENABLE_PROCESS_ENGINE in den Einstellungen."
        
        if not self.workflow_manager:
            return "❌ Process Engine nicht verfügbar. Stellen Sie sicher, dass Camunda Platform 8 läuft."
        
        try:
            if action == "analyze":
                return self._analyze_conversation(conversation_context)
            
            elif action == "start_workflow":
                return self._start_workflow(workflow_id, conversation_context, additional_data)
            
            elif action == "status":
                return self._get_workflow_status(workflow_id)
            
            elif action == "list_workflows":
                return self._list_available_workflows()
            
            elif action == "generate_bpmn":
                return self._generate_bpmn_workflows()
            
            else:
                return f"❌ Unbekannte Aktion: {action}. Verfügbare Aktionen: analyze, start_workflow, status, list_workflows, generate_bpmn"
        
        except Exception as e:
            return f"❌ Process Engine Fehler: {str(e)}"
    
    def _analyze_conversation(self, conversation_context: Optional[str]) -> str:
        """Analysiert Unterhaltung auf relevante Workflows"""
        if not conversation_context:
            return "⚠️ Kein Unterhaltungskontext bereitgestellt für Analyse."
        
        # Simuliere Nachrichten aus Kontext
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content=conversation_context)]
        
        # Analysiere auf relevante Workflows
        triggered_workflows = self.workflow_manager.analyze_conversation_for_workflows(messages)
        
        if not triggered_workflows:
            return "📝 Keine automatisierbaren Universitätsprozesse in der Unterhaltung erkannt."
        
        result = "🔍 **Erkannte Universitätsprozesse:**\n\n"
        
        for workflow_id in triggered_workflows:
            workflow = self.workflow_manager.workflows.get(workflow_id)
            if workflow:
                # Prüfe ob Workflow gestartet werden kann
                extracted_data = self.workflow_manager.data_extractor.extract_from_conversation(messages)
                can_start, missing_data = self.workflow_manager.can_start_workflow(workflow_id, extracted_data)
                
                status_icon = "✅" if can_start else "⚠️"
                result += f"{status_icon} **{workflow.name}**\n"
                result += f"   - Beschreibung: {workflow.description}\n"
                result += f"   - Priorität: {workflow.priority}\n"
                result += f"   - Auto-Start: {'Ja' if workflow.auto_start else 'Nein'}\n"
                
                if not can_start:
                    result += f"   - Fehlende Daten: {', '.join(missing_data)}\n"
                
                result += "\n"
        
        # Empfehlungen
        auto_startable = [wf_id for wf_id in triggered_workflows 
                         if self.workflow_manager.workflows[wf_id].auto_start]
        
        if auto_startable:
            result += f"💡 **Empfehlung:** {len(auto_startable)} Workflow(s) können automatisch gestartet werden.\n"
            result += "Verwenden Sie `start_workflow` mit der entsprechenden workflow_id.\n"
        
        return result
    
    def _start_workflow(self, workflow_id: Optional[str], 
                       conversation_context: Optional[str],
                       additional_data: Optional[Dict[str, Any]]) -> str:
        """Startet einen spezifischen Workflow"""
        if not workflow_id:
            return "❌ Workflow-ID ist erforderlich für start_workflow."
        
        if workflow_id not in self.workflow_manager.workflows:
            available = ", ".join(self.workflow_manager.workflows.keys())
            return f"❌ Workflow '{workflow_id}' nicht gefunden. Verfügbare Workflows: {available}"
        
        if not conversation_context:
            return "⚠️ Kein Unterhaltungskontext bereitgestellt. Workflow wird mit minimalen Daten gestartet."
        
        # Simuliere Nachrichten aus Kontext
        from langchain_core.messages import HumanMessage
        messages = [HumanMessage(content=conversation_context)]
        
        # Starte Workflow
        execution = self.workflow_manager.start_workflow(
            workflow_id, 
            messages, 
            additional_data or {}
        )
        
        if execution:
            workflow = self.workflow_manager.workflows[workflow_id]
            result = f"🚀 **Workflow gestartet:**\n\n"
            result += f"**{workflow.name}** (v{workflow.version})\n"
            result += f"Prozess-ID: {execution.process_instance.process_instance_key}\n"
            result += f"Status: {execution.status}\n"
            result += f"Gestartet: {execution.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n\n"
            result += f"Der Workflow wird automatisch abgearbeitet. "
            result += f"Sie erhalten Benachrichtigungen über den Fortschritt."
            
            return result
        else:
            return f"❌ Workflow '{workflow_id}' konnte nicht gestartet werden. Prüfen Sie die erforderlichen Daten."
    
    def _get_workflow_status(self, workflow_id: Optional[str]) -> str:
        """Zeigt Status von Workflows"""
        active_workflows = self.workflow_manager.list_active_workflows()
        
        if not active_workflows:
            return "📝 Keine aktiven Workflows vorhanden."
        
        if workflow_id:
            # Status für spezifischen Workflow
            specific_workflows = [w for w in active_workflows if w.workflow_id == workflow_id]
            if not specific_workflows:
                return f"❌ Kein aktiver Workflow mit ID '{workflow_id}' gefunden."
            workflows_to_show = specific_workflows
        else:
            # Status für alle Workflows
            workflows_to_show = active_workflows
        
        result = f"📊 **Workflow Status ({len(workflows_to_show)} aktive):**\n\n"
        
        for execution in workflows_to_show:
            workflow = self.workflow_manager.workflows.get(execution.workflow_id)
            result += f"🔄 **{workflow.name if workflow else execution.workflow_id}**\n"
            result += f"   Prozess-ID: {execution.process_instance.process_instance_key}\n"
            result += f"   Status: {execution.status}\n"
            result += f"   Fortschritt: {execution.completion_percentage:.1f}%\n"
            result += f"   Gestartet: {execution.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
            result += f"   Aktualisiert: {execution.updated_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
            
            if execution.progress:
                phase = execution.progress.get('phase', 'Unbekannt')
                step = execution.progress.get('step', 0)
                result += f"   Aktuelle Phase: {phase} (Schritt {step})\n"
            
            result += "\n"
        
        return result
    
    def _list_available_workflows(self) -> str:
        """Listet verfügbare Workflows"""
        workflows = self.workflow_manager.workflows
        
        if not workflows:
            return "📝 Keine Workflows verfügbar."
        
        result = f"📋 **Verfügbare Workflows ({len(workflows)}):**\n\n"
        
        for workflow_id, workflow in workflows.items():
            result += f"🔹 **{workflow.name}** (`{workflow_id}`)\n"
            result += f"   Beschreibung: {workflow.description}\n"
            result += f"   Version: {workflow.version}\n"
            result += f"   Auto-Start: {'✅ Ja' if workflow.auto_start else '❌ Nein'}\n"
            result += f"   Priorität: {workflow.priority}\n"
            result += f"   Trigger: {', '.join(workflow.triggers)}\n"
            result += f"   Benötigte Daten: {', '.join(workflow.required_data)}\n"
            result += "\n"
        
        # Statistiken
        stats = self.workflow_manager.get_workflow_statistics()
        result += f"📊 **Statistiken:**\n"
        result += f"   Aktive Workflows: {stats['total_active_workflows']}\n"
        result += f"   Registrierte Handler: {stats['registered_handlers']}\n"
        
        return result
    
    def _generate_bpmn_workflows(self) -> str:
        """Generiert BPMN-Definitionen"""
        try:
            workflows = self.bpmn_generator.generate_all_university_workflows()
            
            result = f"📄 **BPMN-Workflows generiert ({len(workflows)}):**\n\n"
            
            for workflow_id, file_path in workflows.items():
                result += f"✅ {workflow_id}: {file_path}\n"
            
            result += "\n💡 Die BPMN-Dateien können in Camunda Modeler geöffnet und bearbeitet werden."
            
            # Engine Status prüfen
            if self.process_client:
                health_status = self.process_client.get_health_status()
                result += f"\n\n🏥 **Engine Status:**\n"
                result += f"   Zeebe: {'✅' if health_status['zeebe'] else '❌'}\n"
                result += f"   Operate: {'✅' if health_status['operate'] else '❌'}\n"
                result += f"   Tasklist: {'✅' if health_status['tasklist'] else '❌'}\n"
            
            return result
            
        except Exception as e:
            return f"❌ BPMN-Generierung fehlgeschlagen: {str(e)}"