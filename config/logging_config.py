"""
Zentralisierte Logging-Konfiguration für den Autonomen Chatbot-Agenten
"""
import logging
import sys
from typing import Optional


def setup_logging(level: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """
    Konfiguriert das Logging für die gesamte Anwendung.
    
    Args:
        level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional - Pfad zur Log-Datei
    """
    log_level = getattr(logging, level.upper() if level else "INFO")
    
    # Log-Format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Handler erstellen
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    # Logging konfigurieren
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True  # Überschreibt vorhandene Konfiguration
    )
    
    # Unterdrücke zu verbose Logs von externen Bibliotheken
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("undetected_chromedriver").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Gibt einen Logger mit dem angegebenen Namen zurück.
    
    Args:
        name: Name des Loggers (üblicherweise __name__)
    
    Returns:
        Logger-Instanz
    """
    return logging.getLogger(name)
