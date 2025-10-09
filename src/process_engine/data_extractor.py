"""
Intelligente Datenextraktion aus Chatbot-Unterhaltungen
Erkennt automatisch relevante Informationen für Universitätsprozesse
"""

import re
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from langchain_core.messages import BaseMessage

@dataclass
class ExtractedData:
    """Container für extrahierte Daten aus Unterhaltungen"""
    entity_type: str  # z.B. "student", "professor", "course", "exam"
    data: Dict[str, Any]
    confidence: float
    source_message: str
    timestamp: datetime

class ConversationDataExtractor:
    """Extrahiert strukturierte Daten aus Chatbot-Unterhaltungen für Prozessautomatisierung"""
    
    def __init__(self):
        self.patterns = self._initialize_patterns()
        self.context_cache = {}
    
    def _initialize_patterns(self) -> Dict[str, List[str]]:
        """Initialisiert Regex-Pattern für Universitätsdatenextraktion"""
        return {
            'student_id': [
                r'(?:matrikel|student|matrikelnummer|id)[\s]*(?:nummer|nr|id)?[\s]*:?[\s]*(\d{6,8})',
                r'meine\s+(?:matrikel|student)?(?:nummer)?\s+(?:ist|lautet)?\s*:?\s*(\d{6,8})',
                r'ich\s+bin\s+student\s+(\d{6,8})'
            ],
            'email': [
                r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
            ],
            'name': [
                r'(?:ich\s+heiße|mein\s+name\s+ist|ich\s+bin)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)',
                r'name:\s*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)'
            ],
            'course': [
                r'ich\s+studiere\s+([A-ZÄÖÜ][a-zäöüß]+)(?:\s+im\s+(?:bachelor|master))?',
                r'(?:studiere|studium)\s+([A-ZÄÖÜ][a-zäöüß]+)',
                r'(?:bachelor|master)[\s\w]*(?:in|im|der)?\s+([A-ZÄÖÜ][a-zäöüß]+)',
                r'mein\s+(?:studiengang|fach)\s+ist\s+([A-ZÄÖÜ][a-zäöüß]+)'
            ],
            'semester': [
                r'(?:im|bin\s+im|aktuell\s+im)?\s*(\d+)\.?\s*semester',
                r'semester\s*:?\s*(\d+)'
            ],
            'exam_date': [
                r'(?:prüfung|klausur|exam)[\s\w]*(?:am|ist\s+am)?\s*(\d{1,2}\.?\s*\d{1,2}\.?\s*\d{2,4})',
                r'(?:termin|datum)[\s\w]*:?\s*(\d{1,2}\.?\s*\d{1,2}\.?\s*\d{2,4})'
            ],
            'grade': [
                r'(?:note|bewertung|ergebnis)[\s\w]*:?\s*([1-6][,.]?[0-9]?)',
                r'(?:habe|bekommen|erhalten)\s+(?:die\s+)?note\s+([1-6][,.]?[0-9]?)'
            ],
            'room': [
                r'(?:raum|zimmer|büro|seminarraum)[\s\w]*:?\s*([A-Z]?\d+[a-zA-Z]?(?:\.\d+)?)',
                r'in\s+(?:raum|zimmer)\s+([A-Z]?\d+[a-zA-Z]?(?:\.\d+)?)'
            ],
            'time': [
                r'(?:um|zeit|zeitpunkt)[\s\w]*:?\s*(\d{1,2}[:.]?\d{2})',
                r'(?:termin|meeting|sprechstunde)[\s\w]*um\s+(\d{1,2}[:.]?\d{2})'
            ]
        }
    
    def extract_from_conversation(self, messages: List[BaseMessage]) -> List[ExtractedData]:
        """Extrahiert strukturierte Daten aus einer kompletten Unterhaltung"""
        extracted_data = []
        
        for message in messages:
            if hasattr(message, 'content'):
                message_data = self.extract_from_message(message.content)
                extracted_data.extend(message_data)
        
        # Konsolidiere und priorisiere Daten
        return self._consolidate_data(extracted_data)
    
    def extract_from_message(self, message_text: str) -> List[ExtractedData]:
        """Extrahiert Daten aus einer einzelnen Nachricht"""
        extracted = []
        message_lower = message_text.lower()
        
        for data_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, message_lower, re.IGNORECASE)
                for match in matches:
                    confidence = self._calculate_confidence(data_type, match.group(), message_text)
                    
                    extracted_data = ExtractedData(
                        entity_type=data_type,
                        data={data_type: match.group(1) if match.groups() else match.group()},
                        confidence=confidence,
                        source_message=message_text,
                        timestamp=datetime.now()
                    )
                    extracted.append(extracted_data)
        
        # Kontextuelle Extraktion
        context_data = self._extract_contextual_data(message_text)
        extracted.extend(context_data)
        
        return extracted
    
    def _calculate_confidence(self, data_type: str, match_text: str, full_message: str) -> float:
        """Berechnet Vertrauenswert für extrahierte Daten"""
        base_confidence = 0.7
        
        # Erhöhe Vertrauen basierend auf Kontext
        confidence_boosts = {
            'student_id': 0.9 if len(match_text.strip()) in [6, 7, 8] else 0.5,
            'email': 0.95 if '@' in match_text and '.' in match_text else 0.3,
            'name': 0.8 if len(match_text.split()) >= 2 else 0.6,
            'semester': 0.9 if '1' <= match_text <= '12' else 0.4
        }
        
        return min(1.0, base_confidence + confidence_boosts.get(data_type, 0.0))
    
    def _extract_contextual_data(self, message_text: str) -> List[ExtractedData]:
        """Extrahiert kontextuelle Informationen basierend auf Gesprächsinhalt"""
        contextual_data = []
        message_lower = message_text.lower()
        
        # Erkenne Absichten und Anliegen
        intent_patterns = {
            'transcript_request': [
                'transcript', 'zeugnis', 'leistungsnachweis', 'notenbescheinigung'
            ],
            'exam_registration': [
                'prüfungsanmeldung', 'klausuranmeldung', 'exam registration', 'prüfung registrieren', 
                'prüfungsregistrierung', 'für die prüfungsanmeldung registrieren'
            ],
            'enrollment': [
                'einschreibung', 'anmeldung', 'registration', 'immatrikulation'
            ],
            'grade_inquiry': [
                'noten', 'bewertung', 'ergebnis', 'grade'
            ],
            'schedule_request': [
                'stundenplan', 'schedule', 'termine', 'zeitplan'
            ]
        }
        
        for intent, keywords in intent_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                contextual_data.append(ExtractedData(
                    entity_type='intent',
                    data={'intent': intent, 'keywords': keywords},
                    confidence=0.8,
                    source_message=message_text,
                    timestamp=datetime.now()
                ))
        
        return contextual_data
    
    def _consolidate_data(self, extracted_data: List[ExtractedData]) -> List[ExtractedData]:
        """Konsolidiert und dedupliziert extrahierte Daten"""
        consolidated = {}
        
        for data in extracted_data:
            key = f"{data.entity_type}_{list(data.data.values())[0]}"
            
            if key not in consolidated or data.confidence > consolidated[key].confidence:
                consolidated[key] = data
        
        return list(consolidated.values())
    
    def get_process_variables(self, extracted_data: List[ExtractedData]) -> Dict[str, Any]:
        """Konvertiert extrahierte Daten in Process Engine Variablen"""
        variables = {}
        
        for data in extracted_data:
            if data.confidence >= 0.7:  # Nur hochvertrauenswürdige Daten
                variables.update(data.data)
                variables[f"{data.entity_type}_confidence"] = data.confidence
        
        # Standard-Prozessvariablen
        variables['extraction_timestamp'] = datetime.now().isoformat()
        variables['has_student_data'] = any(d.entity_type in ['student_id', 'name'] for d in extracted_data)
        variables['data_quality_score'] = sum(d.confidence for d in extracted_data) / len(extracted_data) if extracted_data else 0
        
        return variables
    
    def export_training_data(self, extracted_data: List[ExtractedData], output_file: str):
        """Exportiert extrahierte Daten für ML-Training"""
        training_data = []
        
        for data in extracted_data:
            training_data.append({
                'text': data.source_message,
                'entity': data.entity_type,
                'value': data.data,
                'confidence': data.confidence,
                'timestamp': data.timestamp.isoformat()
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)