# Pipeline - can be safely deleted (replaced by test_real_chatbot.py)
    """
    End-to-End Pipeline für RAG-Evaluation.
    
    Führt vollständige Evaluationen durch:
    1. Lädt Testfälle
    2. Führt RAG-Queries aus
    3. Evaluiert mit ARES
    4. Berechnet Metriken
    5. Erstellt Berichte
    """
    
    def __init__(
        self,
        rag_tool: Optional[RAGTool] = None,
        ares_evaluator: Optional[ARESEvaluator] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialisiere die Evaluation Pipeline.
        
        Args:
            rag_tool: RAG-Tool für Queries (optional, wird automatisch erstellt)
            ares_evaluator: ARES Evaluator (optional, wird automatisch erstellt)
            output_dir: Ausgabeverzeichnis für Berichte
        """
        self.rag_tool = rag_tool
        self.ares_evaluator = ares_evaluator or ARESEvaluator()
        self.metrics_calculator = MetricsCalculator()
        self.reporter = EvaluationReporter(self.metrics_calculator)
        
        # Output-Verzeichnis setup
        self.output_dir = output_dir or Path("evaluation_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _initialize_rag_tool(self):
        """Initialisiere das RAG-Tool falls noch nicht vorhanden."""
        if self.rag_tool is None:
            logger.info("🔧 Initialisiere RAG-Tool...")
            # TODO: Hier sollte das echte RAG-Tool initialisiert werden
            # Für jetzt verwenden wir eine Mock-Implementation
            self.rag_tool = MockRAGTool()
            
    def run_single_evaluation(self, test_case: TestCase) -> Tuple[EvaluationResult, RAGMetrics]:
        """
        Führe Evaluation für einen einzelnen Testfall durch.
        
        Args:
            test_case: Testfall für die Evaluation
            
        Returns:
            Tuple von (EvaluationResult, RAGMetrics)
        """
        logger.info(f"🔍 Evaluiere Testfall: {test_case.id}")
        
        # RAG Query ausführen
        start_time = time.time()
        retrieval_start = time.time()
        
        # Simuliere RAG-Query (in Realität würde hier das echte RAG-Tool verwendet)
        retrieved_context, generation_time_ms = self._execute_rag_query(test_case.question)
        retrieval_time_ms = (time.time() - retrieval_start) * 1000
        
        # Simuliere Antwort-Generierung
        generation_start = time.time()
        generated_answer = self._generate_answer(test_case.question, retrieved_context)
        actual_generation_time = (time.time() - generation_start) * 1000
        
        total_time = (time.time() - start_time) * 1000
        
        # ARES Evaluation
        ares_result = self.ares_evaluator.evaluate_single(
            question=test_case.question,
            context=retrieved_context,
            answer=generated_answer
        )
        
        # RAG Metriken berechnen
        metrics = RAGMetrics(
            context_relevance=ares_result.context_relevance,
            answer_faithfulness=ares_result.answer_faithfulness,
            answer_relevance=ares_result.answer_relevance,
            overall_ares_score=ares_result.overall_score,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=actual_generation_time,
            total_time_ms=total_time,
            num_retrieved_docs=3,  # Mock-Wert
            avg_relevance_score=0.75,  # Mock-Wert
            response_length=len(generated_answer),
            response_completeness=self.metrics_calculator.calculate_response_completeness(
                test_case.question, generated_answer
            )
        )
        
        return ares_result, metrics
        
    def _execute_rag_query(self, question: str) -> Tuple[str, float]:
        """
        Führe RAG-Query aus (Mock-Implementation).
        
        Args:
            question: Die Frage
            
        Returns:
            Tuple von (retrieved_context, generation_time_ms)
        """
        # TODO: Hier würde das echte RAG-Tool verwendet
        # Für jetzt: Mock-Kontext
        mock_context = f"""
Relevante Informationen zur Frage '{question}':

Die WiSo-Fakultät der Universität zu Köln bietet verschiedene 
Studienprogramme und Services an. Weitere Informationen finden 
Sie auf der Website der Fakultät oder in der Studienberatung.

Kontakt: wiso-dekanat@uni-koeln.de
Website: https://wiso.uni-koeln.de
        """.strip()
        
        return mock_context, 50.0  # Mock generation time
        
    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generiere Antwort basierend auf Kontext (Mock-Implementation).
        
        Args:
            question: Die Frage
            context: Der abgerufene Kontext
            
        Returns:
            Generierte Antwort
        """
        # TODO: Hier würde das echte LLM verwendet
        # Für jetzt: Mock-Antwort
        return f"Basierend auf den verfügbaren Informationen kann ich Ihnen zur Frage '{question}' folgendes mitteilen: Die WiSo-Fakultät bietet umfassende Unterstützung und Services. Für spezifische Details empfehle ich, die Website zu besuchen oder die Studienberatung zu kontaktieren."

    def run_batch_evaluation(
        self, 
        test_cases: List[TestCase],
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        Führe Batch-Evaluation für mehrere Testfälle durch.
        
        Args:
            test_cases: Liste von Testfällen
            save_results: Ob Ergebnisse gespeichert werden sollen
            
        Returns:
            Dictionary mit Evaluation-Ergebnissen
        """
        logger.info(f"🚀 Starte Batch-Evaluation für {len(test_cases)} Testfälle")
        
        self._initialize_rag_tool()
        self.metrics_calculator.reset()
        
        start_time = datetime.now()
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"📊 Evaluiere Testfall {i}/{len(test_cases)}: {test_case.id}")
            
            try:
                ares_result, rag_metrics = self.run_single_evaluation(test_case)
                
                # Sammle Metriken
                self.metrics_calculator.add_metrics(rag_metrics)
                
                # Sammle Ergebnisse
                results.append({
                    'test_case_id': test_case.id,
                    'question': test_case.question,
                    'category': test_case.category,
                    'difficulty': test_case.difficulty,
                    'ares_result': ares_result,
                    'rag_metrics': rag_metrics
                })
                
                logger.info(f"✅ Testfall {test_case.id} abgeschlossen (ARES Score: {ares_result.overall_score:.3f})")
                
            except Exception as e:
                logger.error(f"❌ Fehler bei Testfall {test_case.id}: {e}")
                continue
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Zusammenfassung erstellen
        summary = {
            'evaluation_summary': {
                'total_test_cases': len(test_cases),
                'successful_evaluations': len(results),
                'failed_evaluations': len(test_cases) - len(results),
                'total_duration_seconds': total_duration,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            },
            'results': results,
            'aggregated_metrics': self.metrics_calculator.get_summary_stats()
        }
        
        if save_results:
            self._save_evaluation_results(summary)
            
        logger.info(f"🎉 Batch-Evaluation abgeschlossen!")
        logger.info(f"   📊 {len(results)}/{len(test_cases)} Testfälle erfolgreich")
        logger.info(f"   ⏱️ Gesamtdauer: {total_duration:.1f}s")
        
        return summary
        
    def _save_evaluation_results(self, results: Dict[str, Any]):
        """Speichere Evaluation-Ergebnisse."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON-Ergebnisse speichern
        json_file = self.output_dir / f"evaluation_results_{timestamp}.json"
        import json
        with open(json_file, 'w', encoding='utf-8') as f:
            # Konvertiere datetime objects für JSON serialization
            serializable_results = self._make_json_serializable(results)
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        # Metriken exportieren
        metrics_file = self.output_dir / f"metrics_{timestamp}.json"
        self.metrics_calculator.export_metrics(metrics_file)
        
        # Text-Bericht erstellen
        report_file = self.output_dir / f"evaluation_report_{timestamp}.txt"
        report_text = self.reporter.generate_text_report()
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        logger.info(f"💾 Ergebnisse gespeichert in: {self.output_dir}")
        
    def _make_json_serializable(self, obj):
        """Konvertiere Objekte für JSON-Serialisierung."""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._make_json_serializable(obj.__dict__)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    def run_evaluation_from_file(
        self,
        test_cases_file: Path,
        category_filter: Optional[str] = None,
        difficulty_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Führe Evaluation basierend auf Testfällen aus einer Datei durch.
        
        Args:
            test_cases_file: Pfad zur Testfälle-Datei
            category_filter: Filtere nach Kategorie (optional)
            difficulty_filter: Filtere nach Schwierigkeit (optional)
            
        Returns:
            Evaluation-Ergebnisse
        """
        from .test_cases import filter_test_cases
        
        # Lade Testfälle
        test_cases = load_test_cases(test_cases_file)
        
        # Filtere wenn nötig
        if category_filter or difficulty_filter:
            test_cases = filter_test_cases(
                test_cases,
                category=category_filter,
                difficulty=difficulty_filter
            )
        
        # Führe Evaluation durch
        return self.run_batch_evaluation(test_cases)


class MockRAGTool:
    """Mock-Implementation des RAG-Tools für Testing."""
    
    def __init__(self):
        self.name = "Mock RAG Tool"
        
    def query(self, question: str) -> str:
        """Mock RAG query."""
        return f"Mock-Antwort für: {question}"