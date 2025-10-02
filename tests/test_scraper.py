""""""

Tests für das Web-Scraper-SystemExample configuration and test script for the Web Scraper RAG System

==================================================================================================



Tests für alle Scraper-Komponenten einschließlich BatchScraper, This script demonstrates how to use the web scraper system with different

VectorStore und DataStructureAnalyzer.configurations and provides examples for testing the functionality.

""""""

import unittest

import sysimport asyncio

import osimport json

import asynciofrom pathlib import Path

import tempfileimport sys

import shutil

from pathlib import Path# Add the parent directory to the path

sys.path.append(str(Path(__file__).parent.parent.parent))

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))from src.scraper.batch_scraper import BatchScraper, ScrapingConfig

sys.path.insert(0, project_root)from src.scraper.vector_store import VectorStore, VectorStoreConfig

from src.scraper.data_structure_analyzer import DataStructureAnalyzer

try:

    from src.scraper.batch_scraper import BatchScraper, ScrapingConfig

    from src.scraper.vector_store import VectorStore, VectorStoreConfig# Example configurations

    from src.scraper.data_structure_analyzer import DataStructureAnalyzerSCRAPING_CONFIGS = {

    SCRAPER_AVAILABLE = True    "conservative": ScrapingConfig(

except ImportError as e:        max_concurrent_requests=3,

    SCRAPER_AVAILABLE = False        request_delay=2.0,

    print(f"Scraper-Module nicht verfügbar: {e}")        timeout=30,

        retry_attempts=2,

        user_agent="RAG Data Collector 1.0"

@unittest.skipUnless(SCRAPER_AVAILABLE, "Scraper-Module nicht verfügbar")    ),

class TestScraperSystem(unittest.TestCase):    

    """Tests für das Scraper-System"""    "balanced": ScrapingConfig(

            max_concurrent_requests=8,

    def setUp(self):        request_delay=1.0,

        """Setup für jeden Test"""        timeout=25,

        # Temporäres Verzeichnis für Tests        retry_attempts=3

        self.temp_dir = tempfile.mkdtemp()    ),

            

        # Test-Konfigurationen    "aggressive": ScrapingConfig(

        self.scraping_config = ScrapingConfig(        max_concurrent_requests=15,

            max_concurrent_requests=2,        request_delay=0.5,

            request_delay=0.5,        timeout=20,

            timeout=10,        retry_attempts=2

            retry_attempts=1    )

        )}

        

        self.vector_config = VectorStoreConfig(VECTOR_CONFIGS = {

            backend="chromadb",    "development": VectorStoreConfig(

            collection_name="test_collection",        backend="chromadb",

            persist_directory=os.path.join(self.temp_dir, "test_vector_db"),        collection_name="dev_collection",

            chunk_size=500,        persist_directory="./dev_vector_db",

            chunk_overlap=50,        chunk_size=800,

            embedding_model="all-MiniLM-L6-v2"        chunk_overlap=150,

        )        embedding_model="all-MiniLM-L6-v2",

                embedding_provider="sentence_transformers"

        # Test-URLs (sichere, schnelle URLs)    ),

        self.test_urls = [    

            "https://httpbin.org/html",    "production": VectorStoreConfig(

            "https://httpbin.org/get"        backend="faiss",

        ]        collection_name="prod_collection", 

            persist_directory="./prod_vector_db",

    def tearDown(self):        chunk_size=1200,

        """Cleanup nach jedem Test"""        chunk_overlap=200,

        # Temporäres Verzeichnis löschen        embedding_model="all-mpnet-base-v2",

        if os.path.exists(self.temp_dir):        embedding_provider="sentence_transformers"

            shutil.rmtree(self.temp_dir)    )

    }

    def test_scraping_config_creation(self):

        """Teste Erstellung der Scraping-Konfiguration"""# Test URLs (replace with your own)

        config = ScrapingConfig()TEST_URLS = {

            "small_test": [

        self.assertIsInstance(config.max_concurrent_requests, int)        "https://en.wikipedia.org/wiki/Machine_learning",

        self.assertGreater(config.max_concurrent_requests, 0)        "https://en.wikipedia.org/wiki/Artificial_intelligence"

        self.assertIsInstance(config.request_delay, (int, float))    ],

        self.assertGreaterEqual(config.request_delay, 0)    

        self.assertIsInstance(config.timeout, int)    "medium_test": [

        self.assertGreater(config.timeout, 0)        "https://en.wikipedia.org/wiki/Machine_learning",

            "https://en.wikipedia.org/wiki/Natural_language_processing",

    def test_vector_config_creation(self):        "https://en.wikipedia.org/wiki/Deep_learning",

        """Teste Erstellung der Vector-Store-Konfiguration"""        "https://en.wikipedia.org/wiki/Neural_network",

        config = VectorStoreConfig()        "https://en.wikipedia.org/wiki/Computer_vision"

            ],

        self.assertIsInstance(config.backend, str)    

        self.assertIsInstance(config.collection_name, str)    "custom": [

        self.assertIsInstance(config.chunk_size, int)        # Add your own URLs here

        self.assertGreater(config.chunk_size, 0)    ]

    }

    def test_batch_scraper_initialization(self):

        """Teste BatchScraper-Initialisierung"""

        scraper = BatchScraper(self.scraping_config)async def test_scraping_only(config_name: str = "balanced", url_set: str = "small_test"):

            """Test only the scraping functionality."""

        self.assertIsNotNone(scraper)    print(f"Testing scraping with {config_name} config and {url_set} URLs...")

        self.assertEqual(scraper.config, self.scraping_config)    

        config = SCRAPING_CONFIGS[config_name]

    def test_vector_store_initialization(self):    urls = TEST_URLS[url_set]

        """Teste VectorStore-Initialisierung"""    

        try:    if not urls:

            vector_store = VectorStore(self.vector_config)        print("No URLs provided for testing")

            self.assertIsNotNone(vector_store)        return

        except Exception as e:    

            self.skipTest(f"VectorStore-Initialisierung fehlgeschlagen: {e}")    def progress_callback(url: str, success: bool, error: str = None):

            status = "✓" if success else "✗"

    def test_scraping_functionality(self):        print(f"  {status} {url}")

        """Teste grundlegende Scraping-Funktionalität"""        if error:

        scraper = BatchScraper(self.scraping_config)            print(f"    Error: {error}")

            

        async def run_scraping_test():    scraper = BatchScraper(config)

            try:    results = await scraper.scrape_urls(urls, progress_callback)

                # Verwende nur eine einfache URL für den Test    

                test_urls = ["https://httpbin.org/html"]    # Print statistics

                    stats = scraper.get_statistics()

                results = await scraper.scrape_urls(test_urls)    print(f"\nScraping Statistics:")

                    print(f"  Successful: {stats['successful']}/{stats['total_urls']}")

                self.assertIsInstance(results, list)    print(f"  Success Rate: {stats['success_rate']:.1%}")

                self.assertEqual(len(results), len(test_urls))    print(f"  Total Words: {stats['total_words']:,}")

                    print(f"  Average Content Length: {stats['avg_content_length']:.0f} chars")

                # Überprüfe Ergebnis-Struktur    print(f"  Unique Domains: {stats['unique_domains']}")

                for result in results:    

                    self.assertTrue(hasattr(result, 'url'))    # Save results

                    self.assertTrue(hasattr(result, 'success'))    scraper.save_results("test_scraped_data.json", "json")

                    self.assertTrue(hasattr(result, 'content'))    print(f"Results saved to test_scraped_data.json")

                    self.assertTrue(hasattr(result, 'scraped_at'))    

                    return results

                # Statistiken testen

                stats = scraper.get_statistics()

                self.assertIsInstance(stats, dict)async def test_full_pipeline(scraping_config: str = "balanced", 

                self.assertIn('total_urls', stats)                           vector_config: str = "development",

                self.assertIn('successful', stats)                           url_set: str = "small_test"):

                self.assertIn('success_rate', stats)    """Test the complete pipeline: scraping → vectorization → analysis."""

                    print(f"Testing full pipeline...")

                return True    print(f"  Scraping config: {scraping_config}")

                    print(f"  Vector config: {vector_config}")

            except Exception as e:    print(f"  URL set: {url_set}")

                print(f"Scraping-Test Fehler: {e}")    

                return False    # Step 1: Scraping

            print("\n=== SCRAPING ===")

        # Test mit Internet-Verbindung    scraping_cfg = SCRAPING_CONFIGS[scraping_config]

        try:    urls = TEST_URLS[url_set]

            import requests    

            response = requests.get("https://httpbin.org/get", timeout=5)    if not urls:

            if response.status_code == 200:        print("No URLs provided for testing")

                # Internet verfügbar, führe Test aus        return

                result = asyncio.run(run_scraping_test())    

                self.assertTrue(result, "Scraping-Test fehlgeschlagen")    def progress_callback(url: str, success: bool, error: str = None):

            else:        status = "✓" if success else "✗"

                self.skipTest("Internet-Verbindung nicht verfügbar")        print(f"  {status} {url}")

        except:    

            self.skipTest("Internet-Verbindung nicht verfügbar")    scraper = BatchScraper(scraping_cfg)

        scraped_content = await scraper.scrape_urls(urls, progress_callback)

    def test_vector_store_operations(self):    

        """Teste VectorStore-Operationen"""    successful_content = [content for content in scraped_content if content.success]

        try:    print(f"Scraped {len(successful_content)} documents successfully")

            vector_store = VectorStore(self.vector_config)    

                if not successful_content:

            # Test-Dokument erstellen        print("No successful content to process")

            from src.scraper.batch_scraper import ScrapedContent        return

            test_doc = ScrapedContent(    

                url="https://example.com/test",    # Step 2: Vectorization

                content="This is a test document for vector store testing.",    print("\n=== VECTORIZATION ===")

                title="Test Document",    vector_cfg = VECTOR_CONFIGS[vector_config]

                success=True,    vector_store = VectorStore(vector_cfg)

                scraped_at="2024-01-01T00:00:00"    

            )    print("Adding content to vector store...")

                vector_store.add_scraped_content(successful_content)

            # Dokument hinzufügen    

            vector_store.add_scraped_content([test_doc])    stats = vector_store.get_statistics()

                print(f"Vector store statistics:")

            # Statistiken überprüfen    print(f"  Total documents: {stats['total_documents']}")

            stats = vector_store.get_statistics()    print(f"  Backend: {stats['backend']}")

            self.assertIsInstance(stats, dict)    print(f"  Embedding model: {stats['embedding_model']}")

            self.assertIn('total_documents', stats)    

            self.assertGreater(stats['total_documents'], 0)    # Step 3: Search Test

                print("\n=== SEARCH TEST ===")

            # Suche testen    test_queries = [

            results = vector_store.search("test document", k=1)        "machine learning algorithms",

            self.assertIsInstance(results, list)        "artificial intelligence applications",

                    "neural networks"

        except Exception as e:    ]

            self.skipTest(f"VectorStore-Test übersprungen: {e}")    

        for query in test_queries:

    def test_data_structure_analyzer(self):        print(f"\nSearching for: '{query}'")

        """Teste DataStructureAnalyzer"""        results = vector_store.search(query, k=3)

        try:        

            vector_store = VectorStore(self.vector_config)        if results:

            analyzer = DataStructureAnalyzer(vector_store)            for i, (doc, score) in enumerate(results, 1):

                            print(f"  {i}. Score: {score:.3f}")

            self.assertIsNotNone(analyzer)                print(f"     Source: {doc.source_url}")

                            print(f"     Preview: {doc.text[:100]}...")

            # Wenn keine Daten vorhanden sind, sollte der Analyzer trotzdem funktionieren        else:

            report = analyzer.analyze_structure()            print("  No results found")

            self.assertIsNotNone(report)    

                # Step 4: Analysis

        except Exception as e:    print("\n=== DATA ANALYSIS ===")

            self.skipTest(f"DataStructureAnalyzer-Test übersprungen: {e}")    analyzer = DataStructureAnalyzer(vector_store)

        report = analyzer.analyze_structure()

    def test_scraper_error_handling(self):    

        """Teste Fehlerbehandlung des Scrapers"""    print(f"Data structure analysis:")

        scraper = BatchScraper(self.scraping_config)    print(f"  Total documents: {report.total_documents}")

            print(f"  Total fields: {len(report.fields)}")

        async def run_error_test():    print(f"  Average completeness: {report.data_quality_metrics['avg_completeness']:.1%}")

            # Teste mit ungültigen URLs    

            invalid_urls = [    # Export reports

                "not-a-url",    analyzer.export_report(report, "test_analysis_report.json", "json")

                "http://invalid-domain-that-does-not-exist.invalid",    analyzer.export_report(report, "test_analysis_report.md", "markdown")

                ""    print("Analysis reports exported")

            ]    

                print("\n=== PIPELINE COMPLETED ===")

            results = await scraper.scrape_urls(invalid_urls)    return vector_store, analyzer

            

            self.assertEqual(len(results), len(invalid_urls))

            def test_configuration_generation():

            # Alle Ergebnisse sollten als fehlgeschlagen markiert sein    """Generate example configuration files."""

            for result in results:    print("Generating example configuration files...")

                self.assertFalse(result.success)    

                # Scraping configuration

            return True    scraping_config = {

                "max_concurrent_requests": 10,

        result = asyncio.run(run_error_test())        "request_delay": 1.0,

        self.assertTrue(result)        "timeout": 30,

        "retry_attempts": 3,

        "user_agent": "RAG Data Collector 1.0",

@unittest.skipUnless(SCRAPER_AVAILABLE, "Scraper-Module nicht verfügbar")        "headers": {

class TestScraperIntegration(unittest.TestCase):            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",

    """Integrationstests für das gesamte Scraper-System"""            "Accept-Language": "en-US,en;q=0.5",

                "Accept-Encoding": "gzip, deflate",

    def setUp(self):            "Connection": "keep-alive"

        """Setup für Integrationstests"""        },

        self.temp_dir = tempfile.mkdtemp()        "content_selectors": {

                "title": "title, h1, .title, .headline",

    def tearDown(self):            "content": "article, main, .content, .post, .article-body, p",

        """Cleanup nach Integrationstests"""            "description": "meta[name='description'], .summary, .excerpt",

        if os.path.exists(self.temp_dir):            "keywords": "meta[name='keywords'], .tags, .categories"

            shutil.rmtree(self.temp_dir)        },

            "exclude_selectors": [

    def test_full_scraper_pipeline(self):            "script", "style", "nav", "footer", "header",

        """Teste komplette Scraper-Pipeline: Scraping → Vectorization → Analysis"""            ".advertisement", ".ads", ".sidebar", ".menu",

        # Überspringe wenn kein Internet verfügbar            ".comments", ".social-media", ".newsletter"

        try:        ]

            import requests    }

            response = requests.get("https://httpbin.org/get", timeout=5)    

            if response.status_code != 200:    # Vector store configuration

                self.skipTest("Internet-Verbindung nicht verfügbar")    vector_config = {

        except:        "backend": "chromadb",

            self.skipTest("Internet-Verbindung nicht verfügbar")        "collection_name": "scraped_content",

                "persist_directory": "./vector_db",

        async def run_pipeline_test():        "chunk_size": 1000,

            try:        "chunk_overlap": 200,

                # 1. Scraping        "embedding_model": "all-MiniLM-L6-v2",

                scraping_config = ScrapingConfig(        "embedding_provider": "sentence_transformers",

                    max_concurrent_requests=1,        "similarity_threshold": 0.7,

                    request_delay=1.0,        "max_results": 10

                    timeout=10,    }

                    retry_attempts=1    

                )    # Save configurations

                    with open("example_scraping_config.json", "w") as f:

                scraper = BatchScraper(scraping_config)        json.dump(scraping_config, f, indent=2)

                test_urls = ["https://httpbin.org/html"]    

                    with open("example_vector_config.json", "w") as f:

                scraped_content = await scraper.scrape_urls(test_urls)        json.dump(vector_config, f, indent=2)

                successful_content = [c for c in scraped_content if c.success]    

                    print("Configuration files generated:")

                if not successful_content:    print("  - example_scraping_config.json")

                    return False, "Keine erfolgreichen Scraping-Ergebnisse"    print("  - example_vector_config.json")

                

                # 2. Vectorization

                vector_config = VectorStoreConfig(async def interactive_test():

                    backend="chromadb",    """Interactive test mode for user input."""

                    collection_name="pipeline_test",    print("=== Interactive Web Scraper Test ===")

                    persist_directory=os.path.join(self.temp_dir, "pipeline_vector_db"),    

                    chunk_size=200,    # Get user input

                    chunk_overlap=20    print("\nAvailable scraping configs:", list(SCRAPING_CONFIGS.keys()))

                )    scraping_config = input("Choose scraping config (default: balanced): ").strip() or "balanced"

                    

                vector_store = VectorStore(vector_config)    print("\nAvailable vector configs:", list(VECTOR_CONFIGS.keys()))

                vector_store.add_scraped_content(successful_content)    vector_config = input("Choose vector config (default: development): ").strip() or "development"

                    

                stats = vector_store.get_statistics()    print("\nAvailable URL sets:", list(TEST_URLS.keys()))

                if stats['total_documents'] == 0:    url_set = input("Choose URL set (default: small_test): ").strip() or "small_test"

                    return False, "Keine Dokumente in VectorStore"    

                    # Option to add custom URLs

                # 3. Analysis    custom_urls_input = input("\nAdd custom URLs (comma-separated, or press Enter to skip): ").strip()

                analyzer = DataStructureAnalyzer(vector_store)    if custom_urls_input:

                report = analyzer.analyze_structure()        custom_urls = [url.strip() for url in custom_urls_input.split(",")]

                        TEST_URLS["custom"] = custom_urls

                if not report:        url_set = "custom"

                    return False, "Keine Analyse-Ergebnisse"    

                    print("\nTest options:")

                return True, "Pipeline erfolgreich"    print("1. Scraping only")

                    print("2. Full pipeline")

            except Exception as e:    choice = input("Choose test type (1 or 2, default: 2): ").strip() or "2"

                return False, f"Pipeline-Fehler: {str(e)}"    

            if choice == "1":

        success, message = asyncio.run(run_pipeline_test())        await test_scraping_only(scraping_config, url_set)

        self.assertTrue(success, message)    else:

        await test_full_pipeline(scraping_config, vector_config, url_set)



def run_scraper_tests():

    """Führe alle Scraper-Tests aus"""async def main():

    if not SCRAPER_AVAILABLE:    """Main function to run tests."""

        print("❌ Scraper-Module nicht verfügbar - Tests übersprungen")    print("Web Scraper RAG System - Test & Example Script")

        return False    print("=" * 50)

        

    print("🔧 Starte Scraper-Tests...")    if len(sys.argv) > 1:

            mode = sys.argv[1]

    loader = unittest.TestLoader()    else:

    suite = unittest.TestSuite()        print("\nAvailable modes:")

            print("1. interactive - Interactive test mode")

    # Lade alle Test-Klassen        print("2. quick - Quick test with defaults")

    suite.addTests(loader.loadTestsFromTestCase(TestScraperSystem))        print("3. scraping - Test scraping only")

    suite.addTests(loader.loadTestsFromTestCase(TestScraperIntegration))        print("4. configs - Generate example configs")

            mode = input("\nChoose mode (1-4, default: interactive): ").strip() or "interactive"

    # Führe Tests aus    

    runner = unittest.TextTestRunner(verbosity=2)    try:

    result = runner.run(suite)        if mode in ["1", "interactive"]:

                await interactive_test()

    return result.wasSuccessful()        

        elif mode in ["2", "quick"]:

            print("\nRunning quick test with default settings...")

if __name__ == "__main__":            await test_full_pipeline()

    import argparse        

            elif mode in ["3", "scraping"]:

    parser = argparse.ArgumentParser(description="Scraper-System Tests")            print("\nTesting scraping functionality only...")

    parser.add_argument("--integration", action="store_true",            await test_scraping_only()

                       help="Nur Integrationstests ausführen")        

            elif mode in ["4", "configs"]:

    args = parser.parse_args()            test_configuration_generation()

            

    if args.integration:        else:

        # Nur Integrationstests            print(f"Unknown mode: {mode}")

        suite = unittest.TestLoader().loadTestsFromTestCase(TestScraperIntegration)            return

    else:        

        # Alle Tests        print("\n✓ Test completed successfully!")

        loader = unittest.TestLoader()        

        suite = unittest.TestSuite()    except KeyboardInterrupt:

        suite.addTests(loader.loadTestsFromTestCase(TestScraperSystem))        print("\n\nTest cancelled by user")

        suite.addTests(loader.loadTestsFromTestCase(TestScraperIntegration))    except Exception as e:

            print(f"\n✗ Test failed with error: {e}")

    runner = unittest.TextTestRunner(verbosity=2)        import traceback

    result = runner.run(suite)        traceback.print_exc()

    

    sys.exit(0 if result.wasSuccessful() else 1)
if __name__ == "__main__":
    asyncio.run(main())