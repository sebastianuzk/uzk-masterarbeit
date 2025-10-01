"""
Example configuration and test script for the Web Scraper RAG System
===================================================================

This script demonstrates how to use the web scraper system with different
configurations and provides examples for testing the functionality.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.scraper.batch_scraper import BatchScraper, ScrapingConfig
from src.scraper.vector_store import VectorStore, VectorStoreConfig
from src.scraper.data_structure_analyzer import DataStructureAnalyzer


# Example configurations
SCRAPING_CONFIGS = {
    "conservative": ScrapingConfig(
        max_concurrent_requests=3,
        request_delay=2.0,
        timeout=30,
        retry_attempts=2,
        user_agent="RAG Data Collector 1.0"
    ),
    
    "balanced": ScrapingConfig(
        max_concurrent_requests=8,
        request_delay=1.0,
        timeout=25,
        retry_attempts=3
    ),
    
    "aggressive": ScrapingConfig(
        max_concurrent_requests=15,
        request_delay=0.5,
        timeout=20,
        retry_attempts=2
    )
}

VECTOR_CONFIGS = {
    "development": VectorStoreConfig(
        backend="chromadb",
        collection_name="dev_collection",
        persist_directory="./dev_vector_db",
        chunk_size=800,
        chunk_overlap=150,
        embedding_model="all-MiniLM-L6-v2",
        embedding_provider="sentence_transformers"
    ),
    
    "production": VectorStoreConfig(
        backend="faiss",
        collection_name="prod_collection", 
        persist_directory="./prod_vector_db",
        chunk_size=1200,
        chunk_overlap=200,
        embedding_model="all-mpnet-base-v2",
        embedding_provider="sentence_transformers"
    )
}

# Test URLs (replace with your own)
TEST_URLS = {
    "small_test": [
        "https://en.wikipedia.org/wiki/Machine_learning",
        "https://en.wikipedia.org/wiki/Artificial_intelligence"
    ],
    
    "medium_test": [
        "https://en.wikipedia.org/wiki/Machine_learning",
        "https://en.wikipedia.org/wiki/Natural_language_processing",
        "https://en.wikipedia.org/wiki/Deep_learning",
        "https://en.wikipedia.org/wiki/Neural_network",
        "https://en.wikipedia.org/wiki/Computer_vision"
    ],
    
    "custom": [
        # Add your own URLs here
    ]
}


async def test_scraping_only(config_name: str = "balanced", url_set: str = "small_test"):
    """Test only the scraping functionality."""
    print(f"Testing scraping with {config_name} config and {url_set} URLs...")
    
    config = SCRAPING_CONFIGS[config_name]
    urls = TEST_URLS[url_set]
    
    if not urls:
        print("No URLs provided for testing")
        return
    
    def progress_callback(url: str, success: bool, error: str = None):
        status = "✓" if success else "✗"
        print(f"  {status} {url}")
        if error:
            print(f"    Error: {error}")
    
    scraper = BatchScraper(config)
    results = await scraper.scrape_urls(urls, progress_callback)
    
    # Print statistics
    stats = scraper.get_statistics()
    print(f"\nScraping Statistics:")
    print(f"  Successful: {stats['successful']}/{stats['total_urls']}")
    print(f"  Success Rate: {stats['success_rate']:.1%}")
    print(f"  Total Words: {stats['total_words']:,}")
    print(f"  Average Content Length: {stats['avg_content_length']:.0f} chars")
    print(f"  Unique Domains: {stats['unique_domains']}")
    
    # Save results
    scraper.save_results("test_scraped_data.json", "json")
    print(f"Results saved to test_scraped_data.json")
    
    return results


async def test_full_pipeline(scraping_config: str = "balanced", 
                           vector_config: str = "development",
                           url_set: str = "small_test"):
    """Test the complete pipeline: scraping → vectorization → analysis."""
    print(f"Testing full pipeline...")
    print(f"  Scraping config: {scraping_config}")
    print(f"  Vector config: {vector_config}")
    print(f"  URL set: {url_set}")
    
    # Step 1: Scraping
    print("\n=== SCRAPING ===")
    scraping_cfg = SCRAPING_CONFIGS[scraping_config]
    urls = TEST_URLS[url_set]
    
    if not urls:
        print("No URLs provided for testing")
        return
    
    def progress_callback(url: str, success: bool, error: str = None):
        status = "✓" if success else "✗"
        print(f"  {status} {url}")
    
    scraper = BatchScraper(scraping_cfg)
    scraped_content = await scraper.scrape_urls(urls, progress_callback)
    
    successful_content = [content for content in scraped_content if content.success]
    print(f"Scraped {len(successful_content)} documents successfully")
    
    if not successful_content:
        print("No successful content to process")
        return
    
    # Step 2: Vectorization
    print("\n=== VECTORIZATION ===")
    vector_cfg = VECTOR_CONFIGS[vector_config]
    vector_store = VectorStore(vector_cfg)
    
    print("Adding content to vector store...")
    vector_store.add_scraped_content(successful_content)
    
    stats = vector_store.get_statistics()
    print(f"Vector store statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Backend: {stats['backend']}")
    print(f"  Embedding model: {stats['embedding_model']}")
    
    # Step 3: Search Test
    print("\n=== SEARCH TEST ===")
    test_queries = [
        "machine learning algorithms",
        "artificial intelligence applications",
        "neural networks"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = vector_store.search(query, k=3)
        
        if results:
            for i, (doc, score) in enumerate(results, 1):
                print(f"  {i}. Score: {score:.3f}")
                print(f"     Source: {doc.source_url}")
                print(f"     Preview: {doc.text[:100]}...")
        else:
            print("  No results found")
    
    # Step 4: Analysis
    print("\n=== DATA ANALYSIS ===")
    analyzer = DataStructureAnalyzer(vector_store)
    report = analyzer.analyze_structure()
    
    print(f"Data structure analysis:")
    print(f"  Total documents: {report.total_documents}")
    print(f"  Total fields: {len(report.fields)}")
    print(f"  Average completeness: {report.data_quality_metrics['avg_completeness']:.1%}")
    
    # Export reports
    analyzer.export_report(report, "test_analysis_report.json", "json")
    analyzer.export_report(report, "test_analysis_report.md", "markdown")
    print("Analysis reports exported")
    
    print("\n=== PIPELINE COMPLETED ===")
    return vector_store, analyzer


def test_configuration_generation():
    """Generate example configuration files."""
    print("Generating example configuration files...")
    
    # Scraping configuration
    scraping_config = {
        "max_concurrent_requests": 10,
        "request_delay": 1.0,
        "timeout": 30,
        "retry_attempts": 3,
        "user_agent": "RAG Data Collector 1.0",
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        },
        "content_selectors": {
            "title": "title, h1, .title, .headline",
            "content": "article, main, .content, .post, .article-body, p",
            "description": "meta[name='description'], .summary, .excerpt",
            "keywords": "meta[name='keywords'], .tags, .categories"
        },
        "exclude_selectors": [
            "script", "style", "nav", "footer", "header",
            ".advertisement", ".ads", ".sidebar", ".menu",
            ".comments", ".social-media", ".newsletter"
        ]
    }
    
    # Vector store configuration
    vector_config = {
        "backend": "chromadb",
        "collection_name": "scraped_content",
        "persist_directory": "./vector_db",
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_provider": "sentence_transformers",
        "similarity_threshold": 0.7,
        "max_results": 10
    }
    
    # Save configurations
    with open("example_scraping_config.json", "w") as f:
        json.dump(scraping_config, f, indent=2)
    
    with open("example_vector_config.json", "w") as f:
        json.dump(vector_config, f, indent=2)
    
    print("Configuration files generated:")
    print("  - example_scraping_config.json")
    print("  - example_vector_config.json")


async def interactive_test():
    """Interactive test mode for user input."""
    print("=== Interactive Web Scraper Test ===")
    
    # Get user input
    print("\nAvailable scraping configs:", list(SCRAPING_CONFIGS.keys()))
    scraping_config = input("Choose scraping config (default: balanced): ").strip() or "balanced"
    
    print("\nAvailable vector configs:", list(VECTOR_CONFIGS.keys()))
    vector_config = input("Choose vector config (default: development): ").strip() or "development"
    
    print("\nAvailable URL sets:", list(TEST_URLS.keys()))
    url_set = input("Choose URL set (default: small_test): ").strip() or "small_test"
    
    # Option to add custom URLs
    custom_urls_input = input("\nAdd custom URLs (comma-separated, or press Enter to skip): ").strip()
    if custom_urls_input:
        custom_urls = [url.strip() for url in custom_urls_input.split(",")]
        TEST_URLS["custom"] = custom_urls
        url_set = "custom"
    
    print("\nTest options:")
    print("1. Scraping only")
    print("2. Full pipeline")
    choice = input("Choose test type (1 or 2, default: 2): ").strip() or "2"
    
    if choice == "1":
        await test_scraping_only(scraping_config, url_set)
    else:
        await test_full_pipeline(scraping_config, vector_config, url_set)


async def main():
    """Main function to run tests."""
    print("Web Scraper RAG System - Test & Example Script")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        print("\nAvailable modes:")
        print("1. interactive - Interactive test mode")
        print("2. quick - Quick test with defaults")
        print("3. scraping - Test scraping only")
        print("4. configs - Generate example configs")
        mode = input("\nChoose mode (1-4, default: interactive): ").strip() or "interactive"
    
    try:
        if mode in ["1", "interactive"]:
            await interactive_test()
        
        elif mode in ["2", "quick"]:
            print("\nRunning quick test with default settings...")
            await test_full_pipeline()
        
        elif mode in ["3", "scraping"]:
            print("\nTesting scraping functionality only...")
            await test_scraping_only()
        
        elif mode in ["4", "configs"]:
            test_configuration_generation()
        
        else:
            print(f"Unknown mode: {mode}")
            return
        
        print("\n✓ Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())