"""
Testfall-Generator für RAG-Evaluation
=====================================

Generiert automatisch Testfälle basierend auf den gescrapten Dokumenten
der WiSo-Fakultät für zukünftige erweiterte Evaluationen.
"""

import logging
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import asdict

# Import für Zugriff auf die Scraper-Daten und RAG-Tool
from src.evaluation.test_real_chatbot import SimpleTestCase
from src.tools.rag_tool import UniversityRAGTool

logger = logging.getLogger(__name__)


class TestCaseGenerator:
    """
    Generator für Testfälle basierend auf gescrapten Dokumenten.
    
    Analysiert die vorhandenen Dokumente und generiert automatisch
    relevante Fragen für die RAG-Evaluation.
    """
    
    def __init__(self):
        """Initialisiere den Generator."""
        self.rag_tool = UniversityRAGTool()
        self.question_templates = self._create_question_templates()
        self.categories = {
            'studium': ['studium', 'bachelor', 'master', 'bewerbung', 'einschreibung', 'prüfung'],
            'services': ['beratung', 'sprechstunden', 'kontakt', 'service', 'hilfe'],
            'forschung': ['forschung', 'projekt', 'institut', 'professor', 'publikation'],
            'international': ['ausland', 'international', 'austausch', 'erasmus', 'partner'],
            'organisation': ['fakultät', 'dekan', 'verwaltung', 'struktur', 'mitarbeiter']
        }
    
    def _create_question_templates(self) -> Dict[str, List[str]]:
        """Erstelle Templates für verschiedene Fragetypen."""
        return {
            'studium': [
                "Wie bewerbe ich mich für {topic}?",
                "Was sind die Voraussetzungen für {topic}?",
                "Welche Fristen gibt es für {topic}?",
                "Wo finde ich Informationen zu {topic}?",
                "Was muss ich bei {topic} beachten?"
            ],
            'services': [
                "Wo finde ich {topic}?",
                "Wie kann ich {topic} nutzen?",
                "Wer ist für {topic} zuständig?",
                "Was bietet {topic}?",
                "Wie erreiche ich {topic}?"
            ],
            'forschung': [
                "Welche Forschungsschwerpunkte gibt es bei {topic}?",
                "Wer forscht zu {topic}?",
                "Was sind aktuelle Projekte zu {topic}?",
                "Wie kann ich bei {topic} mitarbeiten?",
                "Welche Institute beschäftigen sich mit {topic}?"
            ],
            'international': [
                "Gibt es {topic} an der WiSo-Fakultät?",
                "Wie funktioniert {topic}?",
                "Was sind die Voraussetzungen für {topic}?",
                "Welche Möglichkeiten gibt es für {topic}?",
                "Wen kann ich zu {topic} fragen?"
            ],
            'organisation': [
                "Wie ist {topic} organisiert?",
                "Wer gehört zu {topic}?",
                "Was sind die Aufgaben von {topic}?",
                "Wie erreiche ich {topic}?",
                "Wo finde ich Informationen zu {topic}?"
            ]
        }
    
    def analyze_scraped_documents(self) -> Dict[str, Any]:
        """
        Analysiere die gescrapten Dokumente um Topics zu extrahieren.
        
        Returns:
            Dictionary mit gefundenen Topics pro Kategorie
        """
        logger.info("🔍 Analysiere gescrapte Dokumente...")
        
        analysis = {
            'total_collections': 0,
            'topics_by_category': {},
            'sample_content': {}
        }
        
        try:
            # Teste verschiedene Suchbegriffe um Inhalte zu analysieren
            test_queries = [
                "studium bachelor master",
                "bewerbung einschreibung", 
                "forschung projekte",
                "beratung sprechstunden",
                "international ausland"
            ]
            
            for query in test_queries:
                try:
                    result = self.rag_tool._run(query)
                    if result and not result.startswith("❌"):
                        # Extrahiere Schlüsselwörter aus dem Ergebnis
                        words = result.lower().split()
                        
                        # Kategorisiere gefundene Begriffe
                        for category, keywords in self.categories.items():
                            found_topics = []
                            for word in words:
                                if any(kw in word for kw in keywords):
                                    found_topics.append(word)
                            
                            if found_topics:
                                if category not in analysis['topics_by_category']:
                                    analysis['topics_by_category'][category] = set()
                                analysis['topics_by_category'][category].update(found_topics[:5])
                        
                        # Speichere Sample-Content
                        analysis['sample_content'][query] = result[:200] + "..."
                        
                except Exception as e:
                    logger.warning(f"⚠️ Fehler bei Query '{query}': {e}")
                    continue
            
            # Konvertiere Sets zu Lists für JSON-Serialisierung
            analysis['topics_by_category'] = {
                k: list(v) for k, v in analysis['topics_by_category'].items()
            }
            
            logger.info(f"✅ Analyse abgeschlossen: {len(analysis['topics_by_category'])} Kategorien gefunden")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Fehler bei der Dokument-Analyse: {e}")
            return analysis
    
    def generate_test_cases_from_analysis(
        self, 
        analysis: Dict[str, Any], 
        num_cases_per_category: int = 3
    ) -> List[SimpleTestCase]:
        """
        Generiere Testfälle basierend auf der Dokument-Analyse.
        
        Args:
            analysis: Ergebnis der Dokument-Analyse
            num_cases_per_category: Anzahl Testfälle pro Kategorie
            
        Returns:
            Liste generierter Testfälle
        """
        logger.info(f"🎯 Generiere Testfälle ({num_cases_per_category} pro Kategorie)...")
        
        test_cases = []
        case_id = 1
        
        for category, topics in analysis['topics_by_category'].items():
            if not topics:
                continue
                
            templates = self.question_templates.get(category, self.question_templates['studium'])
            
            for i in range(min(num_cases_per_category, len(topics))):
                # Wähle zufällig Topic und Template
                topic = random.choice(topics)
                template = random.choice(templates)
                
                # Generiere Frage
                question = template.format(topic=topic)
                
                # Generiere erwartete Keywords basierend auf Topic und Kategorie
                expected_keywords = [topic]
                if category in self.categories:
                    expected_keywords.extend(random.sample(
                        self.categories[category], 
                        min(2, len(self.categories[category]))
                    ))
                
                test_case = SimpleTestCase(
                    id=f"gen_{case_id:03d}",
                    question=question,
                    category=category,
                    expected_keywords=expected_keywords[:4]  # Max 4 Keywords
                )
                
                test_cases.append(test_case)
                case_id += 1
        
        logger.info(f"✅ {len(test_cases)} Testfälle generiert")
        return test_cases
    
    def generate_test_cases_from_templates(self, num_cases: int = 10) -> List[SimpleTestCase]:
        """
        Generiere Testfälle basierend auf Standard-Templates ohne Dokument-Analyse.
        Fallback-Methode wenn keine gescrapten Dokumente verfügbar sind.
        
        Args:
            num_cases: Anzahl zu generierender Testfälle
            
        Returns:
            Liste generierter Testfälle
        """
        logger.info(f"🎲 Generiere {num_cases} Template-basierte Testfälle...")
        
        # Standard-Topics für WiSo-Fakultät
        standard_topics = {
            'studium': ['Bachelor VWL', 'Master BWL', 'Prüfungsanmeldung', 'Modulwahl', 'Praktikum'],
            'services': ['Studienberatung', 'Prüfungsamt', 'IT-Services', 'Bibliothek', 'Mensa'],
            'forschung': ['Wirtschaftsinformatik', 'Marketing', 'Finance', 'Supply Chain', 'Accounting'],
            'international': ['Erasmus-Austausch', 'Doppelabschluss', 'Sprachkurse', 'Summer Schools'],
            'organisation': ['Fakultätsrat', 'Dekanat', 'Sekretariat', 'Institute', 'Lehrstühle']
        }
        
        test_cases = []
        categories = list(standard_topics.keys())
        
        for i in range(num_cases):
            # Zufällige Auswahl
            category = random.choice(categories)
            topic = random.choice(standard_topics[category])
            template = random.choice(self.question_templates[category])
            
            # Generiere Frage
            question = template.format(topic=topic)
            
            # Keywords basierend auf Topic und Kategorie
            expected_keywords = [topic.split()[0].lower()]  # Erstes Wort vom Topic
            expected_keywords.extend(random.sample(
                self.categories[category], 
                min(2, len(self.categories[category]))
            ))
            
            test_case = SimpleTestCase(
                id=f"tpl_{i+1:03d}",
                question=question,
                category=category,
                expected_keywords=expected_keywords[:3]  # Max 3 Keywords
            )
            
            test_cases.append(test_case)
        
        logger.info(f"✅ {len(test_cases)} Template-Testfälle generiert")
        return test_cases
    
    def save_generated_test_cases(self, test_cases: List[SimpleTestCase], output_file: Path):
        """
        Speichere generierte Testfälle in eine JSON-Datei.
        
        Args:
            test_cases: Liste der Testfälle
            output_file: Ausgabedatei
        """
        data = {
            'metadata': {
                'total_test_cases': len(test_cases),
                'generated_at': str(Path(__file__).name),
                'categories': list(set(tc.category for tc in test_cases))
            },
            'test_cases': [asdict(tc) for tc in test_cases]
        }
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 {len(test_cases)} Testfälle gespeichert in: {output_file}")


def main():
    """Hauptfunktion für die Testfall-Generierung."""
    # Logging setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 Starting Test Case Generation...")
    
    generator = TestCaseGenerator()
    output_dir = Path("evaluation_results")
    
    try:
        # 1. Analysiere gescrapte Dokumente
        print("\n📊 Schritt 1: Analysiere gescrapte Dokumente...")
        analysis = generator.analyze_scraped_documents()
        
        # Speichere Analyse
        analysis_file = output_dir / "document_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"💾 Dokument-Analyse gespeichert in: {analysis_file}")
        
        # 2. Generiere Testfälle basierend auf Dokumenten
        if analysis['topics_by_category']:
            print("\n🎯 Schritt 2: Generiere Testfälle aus Dokumenten...")
            doc_test_cases = generator.generate_test_cases_from_analysis(analysis, num_cases_per_category=2)
            
            if doc_test_cases:
                doc_file = output_dir / "generated_test_cases_from_docs.json"
                generator.save_generated_test_cases(doc_test_cases, doc_file)
        else:
            print("\n⚠️ Keine Dokument-Topics gefunden, überspringe dokument-basierte Generierung")
            doc_test_cases = []
        
        # 3. Generiere Template-basierte Testfälle
        print("\n🎲 Schritt 3: Generiere Template-basierte Testfälle...")
        template_test_cases = generator.generate_test_cases_from_templates(num_cases=8)
        template_file = output_dir / "generated_test_cases_templates.json"
        generator.save_generated_test_cases(template_test_cases, template_file)
        
        # 4. Kombiniere alle Testfälle
        all_test_cases = doc_test_cases + template_test_cases
        if all_test_cases:
            combined_file = output_dir / "all_generated_test_cases.json"
            generator.save_generated_test_cases(all_test_cases, combined_file)
            print(f"\n✅ Insgesamt {len(all_test_cases)} Testfälle generiert und gespeichert!")
        
        print("\n🎉 Testfall-Generierung abgeschlossen!")
        print(f"📁 Alle Dateien in: {output_dir}")
        
    except Exception as e:
        logger.error(f"❌ Fehler bei der Testfall-Generierung: {e}")
        return None


if __name__ == "__main__":
    main()