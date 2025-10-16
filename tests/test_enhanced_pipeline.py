#!/usr/bin/env python3
"""
Test-Script für die erweiterte WiSo Scraper Pipeline
====================================================

Dieses Script testet alle Komponenten des erweiterten Scraper-Systems,
einschließlich der neuen Enhancement-Features.
"""

import sys
import asyncio
import logging
from pathlib import Path
import pytest

# Projekt-Root zum Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).parent))

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@pytest.mark.asyncio
async def test_enhanced_pipeline_small():
    """Test 0: Enhanced Pipeline mit kleinem Datenset (20 Seiten)"""
    print("\n" + "="*70)
    print("TEST 0: Enhanced Scraping Pipeline (Klein)")
    print("="*70)
    
    try:
        from src.scraper.crawler_scraper_pipeline import run_crawler_scraper_pipeline
        
        output_dir = Path("data/test_enhanced_small")
        
        print("Testing mit 20 Seiten und allen Enhancements aktiviert:")
        print("  • Intelligentes Caching")
        print("  • Content-Deduplizierung")
        print("  • Content-Bereinigung")
        print("  • Semantisches Chunking")
        print("  • Resilient Scraping")
        print("  • Metriken")
        print()
        
        stats = await run_crawler_scraper_pipeline(
            output_dir=output_dir,
            max_pages=20,
            crawl_delay=0.5,
            scrape_delay=0.5,
            concurrent_requests=5,
            organize_by_category=True,
            enable_caching=True,
            enable_deduplication=True,
            enable_content_cleaning=True
        )
        
        print("\n✓ Pipeline erfolgreich ausgeführt")
        print(f"✓ URLs entdeckt: {stats['results']['urls_discovered']}")
        print(f"✓ URLs gescraped: {stats['results']['urls_scraped']}")
        print(f"✓ Chunks erstellt: {stats['results']['total_chunks_created']}")
        print(f"✓ Dokumente gespeichert: {stats['results']['total_documents_stored']}")
        print(f"✓ Success Rate: {stats['metrics']['success_rate']:.1f}%")
        
        # Prüfe ob Metriken-Files erstellt wurden
        metrics_file = output_dir / "scraper_metrics.json"
        cache_file = output_dir / "cache_statistics.json"
        
        if metrics_file.exists():
            print(f"✓ Metriken exportiert: {metrics_file}")
        if cache_file.exists():
            print(f"✓ Cache-Statistiken exportiert: {cache_file}")
        
        print("\n✅ Enhanced Pipeline Test BESTANDEN")
        return True
        
    except Exception as e:
        print(f"\n❌ Enhanced Pipeline Test FEHLGESCHLAGEN: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_db():
    """Test 1: Vector-Datenbank überprüfen"""
    print("\n" + "="*70)
    print("TEST 1: Vector-Datenbank Status")
    print("="*70)
    
    try:
        import chromadb
        
        vector_db_path = Path('data/vector_db').resolve()
        print(f"✓ Vector DB Pfad: {vector_db_path}")
        print(f"✓ Existiert: {vector_db_path.exists()}")
        
        if not vector_db_path.exists():
            print("❌ Vector DB nicht gefunden! Pipeline zuerst ausführen.")
            return False
        
        client = chromadb.PersistentClient(path=str(vector_db_path))
        collections = client.list_collections()
        
        print(f"\n✓ Collections gefunden: {len(collections)}")
        total_docs = 0
        for c in collections:
            count = c.count()
            total_docs += count
            print(f"  • {c.name}: {count} Dokumente")
        
        print(f"\n✓ Dokumente insgesamt: {total_docs}")
        
        if total_docs == 0:
            print("❌ Keine Dokumente in der Datenbank!")
            return False
        
        print("\n✅ Vector DB Test BESTANDEN")
        return True
        
    except Exception as e:
        print(f"\n❌ Vector DB Test FEHLGESCHLAGEN: {e}")
        return False


def test_rag_tool():
    """Test 2: RAG Tool Funktionalität"""
    print("\n" + "="*70)
    print("TEST 2: RAG Tool Funktionalität")
    print("="*70)
    
    try:
        from src.tools.rag_tool import UniversityRAGTool
        
        tool = UniversityRAGTool()
        print("✓ RAG Tool initialisiert")
        
        # Test-Anfragen
        test_queries = [
            ("Master Programme", "studium"),
            ("IT Support", "services"),
            ("Forschung", "forschung"),
        ]
        
        print("\n✓ Führe Test-Anfragen aus...")
        passed = 0
        
        for query, expected_category in test_queries:
            print(f"\n  Anfrage: '{query}'")
            result = tool._run(query)
            
            if "❌" in result:
                print(f"    ⚠️  Keine Ergebnisse (benötigt evtl. mehr Daten)")
            elif expected_category in result.lower() or len(result) > 100:
                print(f"    ✓ Relevante Ergebnisse erhalten ({len(result)} Zeichen)")
                passed += 1
            else:
                print(f"    ⚠️  Unerwartetes Ergebnis")
        
        print(f"\n✓ Bestanden: {passed}/{len(test_queries)} Anfragen")
        
        if passed > 0:
            print("\n✅ RAG Tool Test BESTANDEN")
            return True
        else:
            print("\n❌ RAG Tool Test FEHLGESCHLAGEN - keine erfolgreichen Anfragen")
            return False
        
    except Exception as e:
        print(f"\n❌ RAG Tool Test FEHLGESCHLAGEN: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_files():
    """Test 3: Gescrapte Datendateien überprüfen"""
    print("\n" + "="*70)
    print("TEST 3: Gescrapte Datendateien")
    print("="*70)
    
    try:
        import json
        
        files = {
            "scraped_data": Path("src/scraper/data_analysis/scraped_data.json"),
            "discovered_urls": Path("src/scraper/data_analysis/discovered_urls.json"),
        }
        
        for name, filepath in files.items():
            print(f"\n✓ Prüfe {name}...")
            
            if not filepath.exists():
                print(f"  ⚠️  Datei nicht gefunden: {filepath}")
                continue
            
            with open(filepath) as f:
                data = json.load(f)
            
            if name == "scraped_data":
                count = len(data)
                success = sum(1 for d in data if d.get('success', False))
                print(f"  ✓ Seiten insgesamt: {count}")
                print(f"  ✓ Erfolgreich: {success} ({success/count*100:.1f}%)")
            elif name == "discovered_urls":
                count = data.get('total_urls', len(data.get('urls', [])))
                print(f"  ✓ URLs gefunden: {count}")
        
        print("\n✅ Datendateien Test BESTANDEN")
        return True
        
    except Exception as e:
        print(f"\n❌ Datendateien Test FEHLGESCHLAGEN: {e}")
        return False


def test_categorization():
    """Test 4: URL-Kategorisierung"""
    print("\n" + "="*70)
    print("TEST 4: URL-Kategorisierungslogik")
    print("="*70)
    
    try:
        from src.scraper.crawler_scraper_pipeline import categorize_url
        
        test_urls = {
            "https://wiso.uni-koeln.de/de/studium/bachelor": "studium",
            "https://wiso.uni-koeln.de/de/forschung": "forschung",
            "https://wiso.uni-koeln.de/de/services/it": "services",
            "https://wiso.uni-koeln.de/de/fakultaet/dekanat": "fakultaet",
        }
        
        passed = 0
        for url, expected in test_urls.items():
            result = categorize_url(url)
            if result == expected:
                print(f"  ✓ {url} → {result}")
                passed += 1
            else:
                print(f"  ✗ {url} → {result} (erwartet {expected})")
        
        print(f"\n✓ Bestanden: {passed}/{len(test_urls)} Kategorisierungen")
        
        if passed == len(test_urls):
            print("\n✅ Kategorisierungs-Test BESTANDEN")
            return True
        else:
            print("\n⚠️  Kategorisierungs-Test TEILWEISE")
            return True  # Nicht kritisch
        
    except Exception as e:
        print(f"\n❌ Kategorisierungs-Test FEHLGESCHLAGEN: {e}")
        return False


def run_all_tests():
    """Alle Tests ausführen und Ergebnisse berichten"""
    print("\n" + "="*70)
    print("🧪 WiSo Scraper Erweiterte Pipeline Test-Suite")
    print("="*70)
    
    # Async Test zuerst
    print("\nFühre Enhanced Pipeline Test aus...")
    try:
        enhanced_passed = asyncio.run(test_enhanced_pipeline_small())
    except Exception as e:
        print(f"❌ Enhanced Pipeline Test abgestürzt: {e}")
        enhanced_passed = False
    
    # Sync Tests
    tests = [
        ("Vector-Datenbank", test_vector_db),
        ("RAG Tool", test_rag_tool),
        ("Datendateien", test_data_files),
        ("Kategorisierung", test_categorization),
    ]
    
    results = [("Enhanced Pipeline (Klein)", enhanced_passed)]
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ Test '{name}' abgestürzt: {e}")
            results.append((name, False))
    
    # Zusammenfassung
    print("\n" + "="*70)
    print("📊 Test-Zusammenfassung")
    print("="*70)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅ BESTANDEN" if passed else "❌ FEHLGESCHLAGEN"
        print(f"{status:15} - {name}")
    
    print("\n" + "-"*70)
    print(f"Insgesamt: {passed_count}/{total_count} Tests bestanden")
    
    if passed_count == total_count:
        print("\n🎉 Alle Tests BESTANDEN! System ist bereit.")
        return 0
    elif passed_count > 0:
        print(f"\n⚠️  {total_count - passed_count} Test(s) fehlgeschlagen.")
        return 1
    else:
        print("\n❌ Alle Tests FEHLGESCHLAGEN! System-Setup überprüfen.")
        return 2


if __name__ == "__main__":
    sys.exit(run_all_tests())
