"""
Checkpoint Manager für inkrementelle Scraper-Runs
=================================================
Verwaltet Checkpoints für Resume-Funktionalität.
"""
import pickle
from pathlib import Path
from typing import Dict, Any, Optional

class CheckpointManager:
    """Manager für Scraper-Checkpoints."""
    
    def __init__(self, checkpoint_dir: Path = Path("checkpoints")):
        """
        Initialisiere CheckpointManager.
        
        Args:
            checkpoint_dir: Verzeichnis für Checkpoint-Dateien
        """
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.phase1_checkpoint = self.checkpoint_dir / "phase1_processed_docs.pkl"
    
    def load_phase1_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Lade Phase 1 Checkpoint falls vorhanden.
        
        Returns:
            Dictionary mit verarbeiteten Dokumenten oder None
        """
        if not self.phase1_checkpoint.exists():
            return None
        
        print("\n📂 Lade Phase 1 Checkpoint...")
        try:
            with open(self.phase1_checkpoint, 'rb') as f:
                data = pickle.load(f)
            
            print(f"   ✅ {len(data):,} verarbeitete Dokumente aus Checkpoint geladen")
            total_chunks = sum(len(docs) for docs in data.values())
            print(f"   📊 Insgesamt {total_chunks:,} Collections mit Dokumenten")
            
            return data
        except Exception as e:
            print(f"   ⚠️  Fehler beim Laden: {e}")
            return None
    
    def save_phase1_checkpoint(self, docs_by_collection: Dict[str, Any]) -> None:
        """
        Speichere Phase 1 Ergebnisse als Checkpoint.
        
        Args:
            docs_by_collection: Dictionary mit verarbeiteten Dokumenten pro Collection
        """
        print("\n💾 Speichere Phase 1 Checkpoint...")
        try:
            with open(self.phase1_checkpoint, 'wb') as f:
                pickle.dump(docs_by_collection, f)
            
            file_size = self.phase1_checkpoint.stat().st_size / (1024 * 1024)
            print(f"   ✅ Checkpoint gespeichert ({file_size:.1f} MB)")
            print(f"   📍 Pfad: {self.phase1_checkpoint}")
        except Exception as e:
            print(f"   ⚠️  Fehler beim Speichern: {e}")
    
    def delete_phase1_checkpoint(self) -> None:
        """Lösche Phase 1 Checkpoint nach erfolgreichem Abschluss."""
        if self.phase1_checkpoint.exists():
            try:
                self.phase1_checkpoint.unlink()
                print("\n🗑️  Phase 1 Checkpoint gelöscht")
            except Exception as e:
                print(f"\n⚠️  Fehler beim Löschen des Checkpoints: {e}")
    
    def checkpoint_exists(self) -> bool:
        """Prüfe ob ein Checkpoint existiert."""
        return self.phase1_checkpoint.exists()
