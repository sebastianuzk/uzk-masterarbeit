"""
Process Engine Service für automatische Initialisierung
Startet die Process Engine im Hintergrund beim App-Start
"""

import asyncio
import threading
import time
from typing import Optional

from .engine import get_process_engine, initialize_process_engine


class ProcessEngineService:
    """Service für Process Engine Management"""
    
    def __init__(self):
        self.engine = get_process_engine()
        self.initialization_thread: Optional[threading.Thread] = None
        self.is_initializing = False
        self.initialization_complete = False
        self.initialization_error: Optional[str] = None
    
    def start_background_initialization(self):
        """Startet Process Engine Initialisierung im Hintergrund"""
        if self.is_initializing or self.initialization_complete:
            return
        
        self.is_initializing = True
        self.initialization_thread = threading.Thread(
            target=self._initialize_in_thread,
            daemon=True
        )
        self.initialization_thread.start()
        print("🚀 Process Engine Initialisierung gestartet...")
    
    def _initialize_in_thread(self):
        """Führt Initialisierung in separatem Thread aus"""
        try:
            # Neuen Event Loop für Thread erstellen
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Process Engine initialisieren
            success = loop.run_until_complete(initialize_process_engine())
            
            if success:
                self.initialization_complete = True
                print("✅ Process Engine erfolgreich initialisiert")
            else:
                self.initialization_error = "Initialisierung fehlgeschlagen"
                print("❌ Process Engine Initialisierung fehlgeschlagen")
            
        except Exception as e:
            self.initialization_error = str(e)
            print(f"❌ Process Engine Initialisierungsfehler: {e}")
        
        finally:
            self.is_initializing = False
    
    def get_status(self) -> dict:
        """Gibt aktuellen Status zurück"""
        base_status = {
            "is_initializing": self.is_initializing,
            "initialization_complete": self.initialization_complete,
            "initialization_error": self.initialization_error
        }
        
        if self.initialization_complete:
            engine_status = self.engine.get_engine_status()
            base_status.update(engine_status)
        
        return base_status
    
    def wait_for_initialization(self, timeout: float = 10.0) -> bool:
        """Wartet auf Initialisierung (mit Timeout)"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.initialization_complete:
                return True
            if self.initialization_error:
                return False
            time.sleep(0.1)
        
        return False


# Globale Service-Instanz
_service_instance: Optional[ProcessEngineService] = None


def get_process_engine_service() -> ProcessEngineService:
    """Gibt die globale Service-Instanz zurück"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ProcessEngineService()
    return _service_instance


def auto_start_process_engine():
    """Startet Process Engine automatisch beim Import"""
    service = get_process_engine_service()
    service.start_background_initialization()