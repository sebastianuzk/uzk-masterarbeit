"""
Generic Form Validator für Camunda Platform 7

Parst BPMN Start Event Forms automatisch und validiert Eingaben
basierend auf Camunda Form Field Constraints.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class FormField:
    """Repräsentiert ein Camunda Form Field mit Validierungsregeln"""
    id: str
    label: str
    type: str  # string, long, boolean, enum, date
    required: bool = False
    readonly: bool = False
    default_value: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[str]] = None


@dataclass
class ValidationError:
    """Repräsentiert einen Validierungsfehler"""
    field_id: str
    field_label: str
    message: str


class ProcessFormValidator:
    """
    Generischer Form Validator für BPMN Prozesse
    
    Liest Start Event Forms aus BPMN XML und validiert Eingaben
    automatisch basierend auf Camunda Constraints.
    """
    
    def __init__(self, bpmn_file_path: str):
        """
        Initialisiert den Validator für eine BPMN-Datei
        
        Args:
            bpmn_file_path: Pfad zur BPMN XML Datei
        """
        self.bpmn_file_path = Path(bpmn_file_path)
        self.form_fields: Dict[str, FormField] = {}
        self.process_id: Optional[str] = None
        self.process_name: Optional[str] = None
        
        self._parse_bpmn_forms()
    
    def _parse_bpmn_forms(self):
        """Parst BPMN XML und extrahiert Start Event Form Fields"""
        try:
            tree = ET.parse(self.bpmn_file_path)
            root = tree.getroot()
            
            # Namespace mapping für BPMN und Camunda
            namespaces = {
                'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
                'camunda': 'http://camunda.org/schema/1.0/bpmn'
            }
            
            # Finde Prozess-Information
            process_elem = root.find('.//bpmn:process', namespaces)
            if process_elem is not None:
                self.process_id = process_elem.get('id')
                self.process_name = process_elem.get('name')
            
            # Finde Start Event mit Form Data
            start_events = root.findall('.//bpmn:startEvent', namespaces)
            
            for start_event in start_events:
                form_data = start_event.find('.//camunda:formData', namespaces)
                if form_data is not None:
                    # Parse Form Fields
                    form_fields = form_data.findall('camunda:formField', namespaces)
                    
                    for field_elem in form_fields:
                        field = self._parse_form_field(field_elem, namespaces)
                        if field:
                            self.form_fields[field.id] = field
                            
            logger.info(f"Loaded {len(self.form_fields)} form fields for process '{self.process_id}'")
                            
        except Exception as e:
            logger.error(f"Error parsing BPMN file {self.bpmn_file_path}: {e}")
            raise
    
    def _parse_form_field(self, field_elem, namespaces) -> Optional[FormField]:
        """Parst ein einzelnes Form Field Element"""
        try:
            field_id = field_elem.get('id')
            field_label = field_elem.get('label', field_id)
            field_type = field_elem.get('type', 'string')
            default_value = field_elem.get('defaultValue')
            
            # Parse validation constraints
            required = False
            readonly = False
            min_length = None
            max_length = None
            pattern = None
            enum_values = None
            
            validation_elem = field_elem.find('camunda:validation', namespaces)
            if validation_elem is not None:
                constraints = validation_elem.findall('camunda:constraint', namespaces)
                
                for constraint in constraints:
                    constraint_name = constraint.get('name')
                    constraint_config = constraint.get('config')
                    
                    if constraint_name == 'required':
                        required = True
                    elif constraint_name == 'readonly':
                        readonly = True
                    elif constraint_name == 'minlength':
                        min_length = int(constraint_config) if constraint_config else None
                    elif constraint_name == 'maxlength':
                        max_length = int(constraint_config) if constraint_config else None
                    elif constraint_name == 'pattern':
                        pattern = constraint_config
            
            # Parse enum values (wenn type = enum)
            if field_type == 'enum':
                value_elems = field_elem.findall('camunda:value', namespaces)
                enum_values = [v.get('id') for v in value_elems if v.get('id')]
            
            return FormField(
                id=field_id,
                label=field_label,
                type=field_type,
                required=required,
                readonly=readonly,
                default_value=default_value,
                min_length=min_length,
                max_length=max_length,
                pattern=pattern,
                enum_values=enum_values
            )
            
        except Exception as e:
            logger.error(f"Error parsing form field: {e}")
            return None
    
    def validate_variables(self, variables: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """
        Validiert Variables gegen Form Field Constraints
        
        Args:
            variables: Dictionary mit Variable-Namen als Keys
            
        Returns:
            Tuple von (is_valid, error_list)
        """
        errors = []
        
        # Prüfe Required Fields
        for field in self.form_fields.values():
            if field.required:
                if field.id not in variables or variables[field.id] is None:
                    errors.append(ValidationError(
                        field_id=field.id,
                        field_label=field.label,
                        message=f"{field.label} is required"
                    ))
                    continue
                
                value = variables[field.id]
                
                # String-spezifische Validierung
                if field.type == 'string' and isinstance(value, str):
                    if field.min_length and len(value.strip()) < field.min_length:
                        errors.append(ValidationError(
                            field_id=field.id,
                            field_label=field.label,
                            message=f"{field.label} must be at least {field.min_length} characters long"
                        ))
                    
                    if field.max_length and len(value.strip()) > field.max_length:
                        errors.append(ValidationError(
                            field_id=field.id,
                            field_label=field.label,
                            message=f"{field.label} must not exceed {field.max_length} characters"
                        ))
        
        # Prüfe Optional Fields (wenn vorhanden)
        for var_name, var_value in variables.items():
            if var_name in self.form_fields:
                field = self.form_fields[var_name]
                
                if var_value is not None and field.type == 'string':
                    if field.max_length and len(str(var_value).strip()) > field.max_length:
                        errors.append(ValidationError(
                            field_id=field.id,
                            field_label=field.label,
                            message=f"{field.label} must not exceed {field.max_length} characters"
                        ))
        
        return len(errors) == 0, errors
    
    def get_required_fields(self) -> List[FormField]:
        """Gibt Liste aller Required Fields zurück"""
        return [field for field in self.form_fields.values() if field.required]
    
    def get_all_fields(self) -> List[FormField]:
        """Gibt Liste aller Form Fields zurück"""
        return list(self.form_fields.values())
    
    def get_field_info(self, field_id: str) -> Optional[FormField]:
        """Gibt Informationen zu einem spezifischen Field zurück"""
        return self.form_fields.get(field_id)
    
    def format_validation_errors(self, errors: List[ValidationError]) -> str:
        """Formatiert Validation Errors als String"""
        if not errors:
            return "No validation errors"
        
        error_messages = [error.message for error in errors]
        return "; ".join(error_messages)


def validate_process_start(bpmn_file_path: str, variables: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Convenience-Funktion für Prozess-Start-Validierung
    
    Args:
        bpmn_file_path: Pfad zur BPMN-Datei
        variables: Variables für Prozessstart
        
    Returns:
        Tuple von (is_valid, error_message)
    """
    try:
        validator = ProcessFormValidator(bpmn_file_path)
        is_valid, errors = validator.validate_variables(variables)
        
        if is_valid:
            return True, "Validation successful"
        else:
            return False, validator.format_validation_errors(errors)
            
    except Exception as e:
        return False, f"Validation error: {str(e)}"