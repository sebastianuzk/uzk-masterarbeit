"""
Data Structure Analyzer for RAG System
======================================

This module provides dynamic analysis and documentation of data structures
stored in the vector database. It helps understand and optimize the data
organization for the RAG system.

Features:
- Dynamic schema analysis
- Data quality metrics
- Structure optimization suggestions
- Export documentation in multiple formats
"""

import json
import statistics
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from datetime import datetime
import logging
from pathlib import Path

from .vector_store import VectorDocument, VectorStore
from .batch_scraper import ScrapedContent


@dataclass
class FieldAnalysis:
    """Analysis of a single field in the data structure."""
    field_name: str
    data_type: str
    presence_rate: float  # Percentage of documents that have this field
    unique_values: int
    sample_values: List[Any]
    avg_length: Optional[float] = None  # For string fields
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    null_count: int = 0


@dataclass
class DataStructureReport:
    """Complete data structure analysis report."""
    collection_name: str
    total_documents: int
    analysis_timestamp: str
    fields: List[FieldAnalysis]
    data_quality_metrics: Dict[str, Any]
    optimization_suggestions: List[str]
    sample_documents: List[Dict[str, Any]]


class DataStructureAnalyzer:
    """
    Analyzer for vector database data structures.
    
    Provides insights into the data organization, quality metrics,
    and optimization suggestions for the RAG system.
    """
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize the analyzer.
        
        Args:
            vector_store: VectorStore instance to analyze
        """
        self.vector_store = vector_store
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the analyzer."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def analyze_structure(self, sample_size: Optional[int] = None) -> DataStructureReport:
        """
        Analyze the data structure of stored documents.
        
        Args:
            sample_size: Number of documents to sample for analysis
            
        Returns:
            DataStructureReport with complete analysis
        """
        self.logger.info("Starting data structure analysis...")
        
        # Get sample documents
        documents = self._get_sample_documents(sample_size)
        
        if not documents:
            raise ValueError("No documents found in vector store")
        
        # Analyze fields
        fields_analysis = self._analyze_fields(documents)
        
        # Calculate data quality metrics
        quality_metrics = self._calculate_quality_metrics(documents, fields_analysis)
        
        # Generate optimization suggestions
        suggestions = self._generate_suggestions(fields_analysis, quality_metrics)
        
        # Create sample documents for the report
        sample_docs = [self._document_to_dict(doc) for doc in documents[:5]]
        
        report = DataStructureReport(
            collection_name=self.vector_store.config.collection_name,
            total_documents=self.vector_store.backend.get_document_count(),
            analysis_timestamp=datetime.now().isoformat(),
            fields=fields_analysis,
            data_quality_metrics=quality_metrics,
            optimization_suggestions=suggestions,
            sample_documents=sample_docs
        )
        
        self.logger.info("Data structure analysis completed")
        return report
    
    def _get_sample_documents(self, sample_size: Optional[int]) -> List[VectorDocument]:
        """
        Get a sample of documents from the vector store.
        
        Args:
            sample_size: Number of documents to sample
            
        Returns:
            List of VectorDocument objects
        """
        # Since we don't have a direct way to get all documents,
        # we'll use a broad search to get a representative sample
        
        # Use common words to get diverse results
        search_terms = [
            "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
            "a", "an", "is", "are", "was", "were", "be", "been", "have", "has"
        ]
        
        documents = []
        seen_ids = set()
        
        for term in search_terms:
            try:
                results = self.vector_store.search(
                    term, k=50, metadata_filter=None
                )
                
                for doc, _ in results:
                    if doc.id not in seen_ids:
                        documents.append(doc)
                        seen_ids.add(doc.id)
                        
                        if sample_size and len(documents) >= sample_size:
                            break
                
                if sample_size and len(documents) >= sample_size:
                    break
            
            except Exception as e:
                self.logger.warning(f"Search failed for term '{term}': {e}")
                continue
        
        return documents
    
    def _analyze_fields(self, documents: List[VectorDocument]) -> List[FieldAnalysis]:
        """
        Analyze all fields across documents.
        
        Args:
            documents: List of documents to analyze
            
        Returns:
            List of FieldAnalysis objects
        """
        # Collect all field information
        field_data = defaultdict(list)
        field_types = defaultdict(set)
        field_presence = defaultdict(int)
        
        for doc in documents:
            doc_dict = self._document_to_dict(doc)
            
            # Track which fields are present in this document
            present_fields = set()
            
            for field_name, value in doc_dict.items():
                field_data[field_name].append(value)
                field_types[field_name].add(type(value).__name__)
                present_fields.add(field_name)
            
            # Count presence for each field
            for field_name in field_data.keys():
                if field_name in present_fields:
                    field_presence[field_name] += 1
        
        # Analyze each field
        analyses = []
        total_docs = len(documents)
        
        for field_name, values in field_data.items():
            analysis = self._analyze_single_field(
                field_name, values, field_types[field_name], 
                field_presence[field_name], total_docs
            )
            analyses.append(analysis)
        
        # Sort by presence rate (most common fields first)
        analyses.sort(key=lambda x: x.presence_rate, reverse=True)
        
        return analyses
    
    def _analyze_single_field(self, field_name: str, values: List[Any],
                             types: Set[str], presence_count: int, 
                             total_docs: int) -> FieldAnalysis:
        """
        Analyze a single field.
        
        Args:
            field_name: Name of the field
            values: All values for this field
            types: Set of data types found
            presence_count: Number of documents with this field
            total_docs: Total number of documents
            
        Returns:
            FieldAnalysis object
        """
        # Determine primary data type
        type_counts = Counter(type(v).__name__ for v in values if v is not None)
        primary_type = type_counts.most_common(1)[0][0] if type_counts else "unknown"
        
        # Filter out None values for analysis
        non_null_values = [v for v in values if v is not None]
        null_count = len(values) - len(non_null_values)
        
        # Calculate unique values
        unique_values = len(set(str(v) for v in non_null_values))
        
        # Get sample values
        sample_values = list(set(non_null_values))[:10]
        
        # Calculate statistics based on data type
        avg_length = None
        min_value = None
        max_value = None
        
        if primary_type == "str" and non_null_values:
            lengths = [len(str(v)) for v in non_null_values]
            avg_length = statistics.mean(lengths)
            min_value = min(non_null_values, key=len)
            max_value = max(non_null_values, key=len)
        
        elif primary_type in ["int", "float"] and non_null_values:
            try:
                numeric_values = [float(v) for v in non_null_values]
                min_value = min(numeric_values)
                max_value = max(numeric_values)
            except (ValueError, TypeError):
                pass
        
        return FieldAnalysis(
            field_name=field_name,
            data_type=primary_type,
            presence_rate=presence_count / total_docs,
            unique_values=unique_values,
            sample_values=sample_values,
            avg_length=avg_length,
            min_value=min_value,
            max_value=max_value,
            null_count=null_count
        )
    
    def _calculate_quality_metrics(self, documents: List[VectorDocument],
                                  fields: List[FieldAnalysis]) -> Dict[str, Any]:
        """
        Calculate data quality metrics.
        
        Args:
            documents: List of documents
            fields: List of field analyses
            
        Returns:
            Dictionary with quality metrics
        """
        total_docs = len(documents)
        
        # Calculate completeness metrics
        completeness_scores = [field.presence_rate for field in fields]
        avg_completeness = statistics.mean(completeness_scores)
        
        # Calculate consistency metrics
        consistency_issues = []
        for field in fields:
            if field.presence_rate < 0.5:  # Less than 50% presence
                consistency_issues.append(f"Field '{field.field_name}' is missing in {100-field.presence_rate*100:.1f}% of documents")
        
        # Calculate content quality metrics
        text_fields = [f for f in fields if f.field_name in ['text', 'content', 'title']]
        avg_text_length = 0
        if text_fields:
            text_lengths = []
            for doc in documents:
                doc_dict = self._document_to_dict(doc)
                for field in text_fields:
                    if field.field_name in doc_dict:
                        text_lengths.append(len(str(doc_dict[field.field_name])))
            
            if text_lengths:
                avg_text_length = statistics.mean(text_lengths)
        
        # Calculate diversity metrics
        source_urls = [doc.source_url for doc in documents]
        unique_sources = len(set(source_urls))
        source_diversity = unique_sources / total_docs if total_docs > 0 else 0
        
        return {
            'total_documents': total_docs,
            'total_fields': len(fields),
            'avg_completeness': avg_completeness,
            'consistency_issues': consistency_issues,
            'avg_text_length': avg_text_length,
            'unique_sources': unique_sources,
            'source_diversity': source_diversity,
            'fields_with_high_completeness': len([f for f in fields if f.presence_rate > 0.9]),
            'fields_with_low_completeness': len([f for f in fields if f.presence_rate < 0.5])
        }
    
    def _generate_suggestions(self, fields: List[FieldAnalysis],
                            metrics: Dict[str, Any]) -> List[str]:
        """
        Generate optimization suggestions.
        
        Args:
            fields: List of field analyses
            metrics: Quality metrics
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        # Completeness suggestions
        if metrics['avg_completeness'] < 0.8:
            suggestions.append(
                "Consider standardizing data collection to improve field completeness. "
                f"Current average completeness: {metrics['avg_completeness']:.1%}"
            )
        
        # Field-specific suggestions
        low_completeness_fields = [f for f in fields if f.presence_rate < 0.5]
        if low_completeness_fields:
            field_names = [f.field_name for f in low_completeness_fields]
            suggestions.append(
                f"Fields with low completeness should be reviewed: {', '.join(field_names)}"
            )
        
        # Text length suggestions
        if metrics['avg_text_length'] < 100:
            suggestions.append(
                "Average text length is quite short. Consider collecting more detailed content "
                "or adjusting chunking strategy for better RAG performance."
            )
        elif metrics['avg_text_length'] > 2000:
            suggestions.append(
                "Average text length is quite long. Consider smaller chunk sizes "
                "for more precise retrieval in RAG queries."
            )
        
        # Source diversity suggestions
        if metrics['source_diversity'] < 0.1:
            suggestions.append(
                "Low source diversity detected. Consider scraping from more varied sources "
                "to improve knowledge coverage."
            )
        
        # Field optimization suggestions
        text_field = next((f for f in fields if f.field_name == 'text'), None)
        if text_field and text_field.avg_length:
            if text_field.avg_length < 200:
                suggestions.append(
                    "Text chunks are quite small. Consider increasing chunk size or "
                    "improving content extraction to capture more context."
            )
        
        # Metadata suggestions
        metadata_fields = [f for f in fields if f.field_name.startswith('metadata')]
        if len(metadata_fields) < 3:
            suggestions.append(
                "Consider enriching metadata with additional fields like categories, "
                "tags, or content quality scores for better filtering capabilities."
            )
        
        return suggestions
    
    def _document_to_dict(self, doc: VectorDocument) -> Dict[str, Any]:
        """
        Convert VectorDocument to dictionary for analysis.
        
        Args:
            doc: VectorDocument to convert
            
        Returns:
            Dictionary representation
        """
        doc_dict = {
            'id': doc.id,
            'text': doc.text,
            'source_url': doc.source_url,
            'chunk_index': doc.chunk_index,
            'total_chunks': doc.total_chunks
        }
        
        # Add metadata fields
        if doc.metadata:
            for key, value in doc.metadata.items():
                doc_dict[f'metadata_{key}'] = value
        
        return doc_dict
    
    def export_report(self, report: DataStructureReport, 
                     output_path: str, format: str = 'json') -> None:
        """
        Export the analysis report to file.
        
        Args:
            report: DataStructureReport to export
            output_path: Output file path
            format: Export format ('json', 'markdown', 'html')
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            self._export_json(report, output_path)
        elif format == 'markdown':
            self._export_markdown(report, output_path)
        elif format == 'html':
            self._export_html(report, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Report exported to {output_path}")
    
    def _export_json(self, report: DataStructureReport, output_path: Path) -> None:
        """Export report as JSON."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)
    
    def _export_markdown(self, report: DataStructureReport, output_path: Path) -> None:
        """Export report as Markdown."""
        md_content = f"""# Data Structure Analysis Report

**Collection:** {report.collection_name}  
**Total Documents:** {report.total_documents:,}  
**Analysis Date:** {report.analysis_timestamp}

## Data Quality Metrics

| Metric | Value |
|--------|-------|
| Total Fields | {len(report.fields)} |
| Average Completeness | {report.data_quality_metrics['avg_completeness']:.1%} |
| Average Text Length | {report.data_quality_metrics['avg_text_length']:.0f} chars |
| Unique Sources | {report.data_quality_metrics['unique_sources']} |
| Source Diversity | {report.data_quality_metrics['source_diversity']:.1%} |

## Field Analysis

| Field Name | Type | Presence Rate | Unique Values | Avg Length |
|------------|------|---------------|---------------|------------|
"""
        
        for field in report.fields:
            avg_len = f"{field.avg_length:.1f}" if field.avg_length else "N/A"
            md_content += f"| {field.field_name} | {field.data_type} | {field.presence_rate:.1%} | {field.unique_values} | {avg_len} |\n"
        
        md_content += "\n## Optimization Suggestions\n\n"
        for i, suggestion in enumerate(report.optimization_suggestions, 1):
            md_content += f"{i}. {suggestion}\n\n"
        
        if report.data_quality_metrics['consistency_issues']:
            md_content += "## Consistency Issues\n\n"
            for issue in report.data_quality_metrics['consistency_issues']:
                md_content += f"- {issue}\n"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
    
    def _export_html(self, report: DataStructureReport, output_path: Path) -> None:
        """Export report as HTML."""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Data Structure Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .metric {{ background-color: #f9f9f9; padding: 10px; margin: 10px 0; }}
        .suggestion {{ background-color: #e8f4f8; padding: 10px; margin: 5px 0; border-left: 4px solid #2196F3; }}
    </style>
</head>
<body>
    <h1>Data Structure Analysis Report</h1>
    
    <div class="metric">
        <strong>Collection:</strong> {report.collection_name}<br>
        <strong>Total Documents:</strong> {report.total_documents:,}<br>
        <strong>Analysis Date:</strong> {report.analysis_timestamp}
    </div>
    
    <h2>Data Quality Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Total Fields</td><td>{len(report.fields)}</td></tr>
        <tr><td>Average Completeness</td><td>{report.data_quality_metrics['avg_completeness']:.1%}</td></tr>
        <tr><td>Average Text Length</td><td>{report.data_quality_metrics['avg_text_length']:.0f} chars</td></tr>
        <tr><td>Unique Sources</td><td>{report.data_quality_metrics['unique_sources']}</td></tr>
        <tr><td>Source Diversity</td><td>{report.data_quality_metrics['source_diversity']:.1%}</td></tr>
    </table>
    
    <h2>Field Analysis</h2>
    <table>
        <tr>
            <th>Field Name</th>
            <th>Type</th>
            <th>Presence Rate</th>
            <th>Unique Values</th>
            <th>Avg Length</th>
        </tr>
"""
        
        for field in report.fields:
            avg_len = f"{field.avg_length:.1f}" if field.avg_length else "N/A"
            html_content += f"""
        <tr>
            <td>{field.field_name}</td>
            <td>{field.data_type}</td>
            <td>{field.presence_rate:.1%}</td>
            <td>{field.unique_values}</td>
            <td>{avg_len}</td>
        </tr>"""
        
        html_content += """
    </table>
    
    <h2>Optimization Suggestions</h2>
"""
        
        for i, suggestion in enumerate(report.optimization_suggestions, 1):
            html_content += f'    <div class="suggestion">{i}. {suggestion}</div>\n'
        
        html_content += """
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def get_field_statistics(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed statistics for a specific field.
        
        Args:
            field_name: Name of the field to analyze
            
        Returns:
            Dictionary with field statistics
        """
        # Get sample documents
        documents = self._get_sample_documents(1000)
        
        if not documents:
            return None
        
        # Extract values for the specific field
        values = []
        for doc in documents:
            doc_dict = self._document_to_dict(doc)
            if field_name in doc_dict:
                values.append(doc_dict[field_name])
        
        if not values:
            return None
        
        # Calculate statistics
        stats = {
            'total_count': len(values),
            'unique_count': len(set(str(v) for v in values)),
            'data_types': list(set(type(v).__name__ for v in values)),
            'sample_values': list(set(values))[:20]
        }
        
        # Type-specific statistics
        if all(isinstance(v, str) for v in values):
            lengths = [len(v) for v in values]
            stats['min_length'] = min(lengths)
            stats['max_length'] = max(lengths)
            stats['avg_length'] = statistics.mean(lengths)
        
        elif all(isinstance(v, (int, float)) for v in values):
            stats['min_value'] = min(values)
            stats['max_value'] = max(values)
            stats['avg_value'] = statistics.mean(values)
        
        return stats


# Example usage
if __name__ == "__main__":
    import asyncio
    from batch_scraper import BatchScraper, ScrapingConfig
    from vector_store import VectorStore, VectorStoreConfig
    
    async def main():
        # Example: Analyze existing vector store
        vector_config = VectorStoreConfig(
            backend="chromadb",
            collection_name="example_collection"
        )
        
        vector_store = VectorStore(vector_config)
        analyzer = DataStructureAnalyzer(vector_store)
        
        try:
            # Analyze structure
            print("Analyzing data structure...")
            report = analyzer.analyze_structure(sample_size=100)
            
            # Print summary
            print(f"\nAnalysis Summary:")
            print(f"Total Documents: {report.total_documents}")
            print(f"Total Fields: {len(report.fields)}")
            print(f"Average Completeness: {report.data_quality_metrics['avg_completeness']:.1%}")
            
            # Export reports
            analyzer.export_report(report, "data_structure_report.json", "json")
            analyzer.export_report(report, "data_structure_report.md", "markdown")
            analyzer.export_report(report, "data_structure_report.html", "html")
            
            print("\nReports exported to data_structure_report.[json|md|html]")
            
        except Exception as e:
            print(f"Analysis failed: {e}")
    
    asyncio.run(main())