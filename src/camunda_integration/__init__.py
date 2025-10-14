"""
Camunda Platform 7 Integration

This module provides integration with Camunda Platform 7 for BPMN process execution.
It includes Docker setup, REST API client, and service layer for process management.
"""

__version__ = "1.0.0"
__author__ = "Chatbot Agent"

# Import main classes when they're needed to avoid circular imports
def get_camunda_service():
    from .services.camunda_service import CamundaService
    return CamundaService

def get_camunda_client():
    from .client.camunda_client import CamundaClient
    return CamundaClient

__all__ = ["get_camunda_service", "get_camunda_client"]