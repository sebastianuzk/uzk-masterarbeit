"""
Scraper Configuration Management
===============================

Loads and manages configuration for Naive vs Advanced RAG scraping modes.
"""

import os
from pathlib import Path
from typing import Dict, Any, Union
from dataclasses import dataclass


@dataclass
class ScraperConfig:
    """Configuration class for scraper features"""
    
    # Performance & Caching
    enable_caching: bool = False
    enable_incremental_scraping: bool = False
    cache_validity_hours: int = 24
    
    # Content Processing
    enable_deduplication: bool = False
    enable_content_cleaning: bool = False
    enable_semantic_chunking: bool = False
    enable_quality_assessment: bool = False
    
    # Metadata Enrichment
    enable_metadata_enrichment: bool = False
    enable_auto_categorization: bool = False
    enable_url_categorization: bool = False
    
    # Robustness & Resilience
    enable_resilient_scraping: bool = False
    max_retries: int = 3
    initial_retry_delay: float = 2.0
    max_retry_delay: float = 60.0
    
    # Vector Store Optimization
    organize_by_category: bool = False
    enable_advanced_embeddings: bool = False
    custom_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Monitoring & Analytics
    enable_detailed_metrics: bool = False
    enable_change_detection: bool = False
    enable_performance_monitoring: bool = False
    enable_report_export: bool = False
    
    # PDF Processing
    enable_advanced_pdf_processing: bool = False
    enable_pdf_metadata_extraction: bool = False
    enable_pdf_ocr: bool = False
    
    # Error Handling & Logging
    enable_detailed_error_logging: bool = False
    enable_failed_urls_export: bool = False
    
    # Experimental Features
    enable_ml_content_analysis: bool = False
    enable_keyword_extraction: bool = False
    enable_similarity_clustering: bool = False
    
    # Debugging
    debug_mode: bool = False
    dry_run: bool = False
    debug_max_urls: int = 0
    
    @classmethod
    def load_from_env(cls, env_file: Union[str, Path] = "scraper.env") -> "ScraperConfig":
        """
        Load configuration from environment file.
        
        Args:
            env_file: Path to the scraper.env file
            
        Returns:
            ScraperConfig instance with loaded values
        """
        config = cls()  # Start with defaults (all False for Naive RAG)
        
        env_path = Path(env_file)
        if not env_path.exists():
            print(f"⚠️  scraper.env not found at {env_path}")
            print("   Using Naive RAG mode (all optimizations disabled)")
            return config
        
        # Load environment variables from file
        env_vars = {}
        try:
            with env_path.open('r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        env_vars[key] = value
                    
        except Exception as e:
            print(f"⚠️  Error reading {env_file}: {e}")
            print("   Using Naive RAG mode (all optimizations disabled)")
            return config
        
        # Helper function to parse boolean values
        def parse_bool(value: str) -> bool:
            return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
        
        def parse_int(value: str, default: int) -> int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        def parse_float(value: str, default: float) -> float:
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        # Map environment variables to config attributes
        config.enable_caching = parse_bool(env_vars.get('ENABLE_CACHING', 'false'))
        config.enable_incremental_scraping = parse_bool(env_vars.get('ENABLE_INCREMENTAL_SCRAPING', 'false'))
        config.cache_validity_hours = parse_int(env_vars.get('CACHE_VALIDITY_HOURS', '24'), 24)
        
        config.enable_deduplication = parse_bool(env_vars.get('ENABLE_DEDUPLICATION', 'false'))
        config.enable_content_cleaning = parse_bool(env_vars.get('ENABLE_CONTENT_CLEANING', 'false'))
        config.enable_semantic_chunking = parse_bool(env_vars.get('ENABLE_SEMANTIC_CHUNKING', 'false'))
        config.enable_quality_assessment = parse_bool(env_vars.get('ENABLE_QUALITY_ASSESSMENT', 'false'))
        
        config.enable_metadata_enrichment = parse_bool(env_vars.get('ENABLE_METADATA_ENRICHMENT', 'false'))
        config.enable_auto_categorization = parse_bool(env_vars.get('ENABLE_AUTO_CATEGORIZATION', 'false'))
        config.enable_url_categorization = parse_bool(env_vars.get('ENABLE_URL_CATEGORIZATION', 'false'))
        
        config.enable_resilient_scraping = parse_bool(env_vars.get('ENABLE_RESILIENT_SCRAPING', 'false'))
        config.max_retries = parse_int(env_vars.get('MAX_RETRIES', '3'), 3)
        config.initial_retry_delay = parse_float(env_vars.get('INITIAL_RETRY_DELAY', '2.0'), 2.0)
        config.max_retry_delay = parse_float(env_vars.get('MAX_RETRY_DELAY', '60.0'), 60.0)
        
        config.organize_by_category = parse_bool(env_vars.get('ORGANIZE_BY_CATEGORY', 'false'))
        config.enable_advanced_embeddings = parse_bool(env_vars.get('ENABLE_ADVANCED_EMBEDDINGS', 'false'))
        config.custom_embedding_model = env_vars.get('CUSTOM_EMBEDDING_MODEL', config.custom_embedding_model)
        
        config.enable_detailed_metrics = parse_bool(env_vars.get('ENABLE_DETAILED_METRICS', 'false'))
        config.enable_change_detection = parse_bool(env_vars.get('ENABLE_CHANGE_DETECTION', 'false'))
        config.enable_performance_monitoring = parse_bool(env_vars.get('ENABLE_PERFORMANCE_MONITORING', 'false'))
        config.enable_report_export = parse_bool(env_vars.get('ENABLE_REPORT_EXPORT', 'false'))
        
        config.enable_advanced_pdf_processing = parse_bool(env_vars.get('ENABLE_ADVANCED_PDF_PROCESSING', 'false'))
        config.enable_pdf_metadata_extraction = parse_bool(env_vars.get('ENABLE_PDF_METADATA_EXTRACTION', 'false'))
        config.enable_pdf_ocr = parse_bool(env_vars.get('ENABLE_PDF_OCR', 'false'))
        
        config.enable_detailed_error_logging = parse_bool(env_vars.get('ENABLE_DETAILED_ERROR_LOGGING', 'false'))
        config.enable_failed_urls_export = parse_bool(env_vars.get('ENABLE_FAILED_URLS_EXPORT', 'false'))
        
        config.enable_ml_content_analysis = parse_bool(env_vars.get('ENABLE_ML_CONTENT_ANALYSIS', 'false'))
        config.enable_keyword_extraction = parse_bool(env_vars.get('ENABLE_KEYWORD_EXTRACTION', 'false'))
        config.enable_similarity_clustering = parse_bool(env_vars.get('ENABLE_SIMILARITY_CLUSTERING', 'false'))
        
        config.debug_mode = parse_bool(env_vars.get('DEBUG_MODE', 'false'))
        config.dry_run = parse_bool(env_vars.get('DRY_RUN', 'false'))
        config.debug_max_urls = parse_int(env_vars.get('DEBUG_MAX_URLS', '0'), 0)
        
        return config
    
    def get_active_features(self) -> Dict[str, bool]:
        """Return a dictionary of all active features for logging."""
        features = {}
        for field_name, field_obj in self.__dataclass_fields__.items():
            if field_obj.type == bool:
                features[field_name] = getattr(self, field_name)
        return {k: v for k, v in features.items() if v}
    
    def is_naive_mode(self) -> bool:
        """Check if running in naive RAG mode (no optimizations)."""
        return len(self.get_active_features()) == 0
    
    def log_configuration(self) -> None:
        """Log the current configuration."""
        active_features = self.get_active_features()
        
        if self.is_naive_mode():
            print("🔍 Running in NAIVE RAG mode")
            print("   • No advanced optimizations")
            print("   • Basic crawling + scraping + chunking only")
        else:
            print("🚀 Running in ADVANCED RAG mode")
            print(f"   • {len(active_features)} optimization features active:")
            for feature in sorted(active_features.keys()):
                print(f"     - {feature}")


def load_scraper_config(env_file: Union[str, Path] = "scraper.env") -> ScraperConfig:
    """Convenience function to load scraper configuration."""
    return ScraperConfig.load_from_env(env_file)