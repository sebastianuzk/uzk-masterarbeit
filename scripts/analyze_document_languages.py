"""
Sprachanalyse-Skript für Dokumente in der Vektordatenbank

Analysiert die Sprache aller Dokumente und erstellt eine Statistik.
Nutzt die langdetect-Bibliothek für zuverlässige Spracherkennung.

Verwendung:
    python scripts/analyze_document_languages.py
    python scripts/analyze_document_languages.py --sample 100
    python scripts/analyze_document_languages.py --export results.csv
"""

import sys
import os
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional
import random

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import RANDOM_SEED

# Seed für Reproduzierbarkeit
random.seed(RANDOM_SEED)

def detect_language_safe(text: str) -> Tuple[str, float]:
    """
    Erkennt die Sprache eines Textes mit Fehlerbehandlung.
    
    Args:
        text: Der zu analysierende Text
        
    Returns:
        Tuple aus (Sprachcode, Konfidenz)
    """
    from langdetect import detect_langs, DetectorFactory
    
    # Seed für deterministische Ergebnisse
    DetectorFactory.seed = RANDOM_SEED
    
    if not text or len(text.strip()) < 20:
        return ("unknown", 0.0)
    
    try:
        results = detect_langs(text[:5000])  # Nur erste 5000 Zeichen für Performance
        if results:
            top_result = results[0]
            return (top_result.lang, top_result.prob)
        return ("unknown", 0.0)
    except Exception:
        return ("unknown", 0.0)


def get_language_name(code: str) -> str:
    """Konvertiert Sprachcode zu lesbarem Namen."""
    language_names = {
        "de": "Deutsch",
        "en": "Englisch",
        "fr": "Französisch",
        "es": "Spanisch",
        "it": "Italienisch",
        "nl": "Niederländisch",
        "pt": "Portugiesisch",
        "pl": "Polnisch",
        "ru": "Russisch",
        "zh-cn": "Chinesisch (vereinfacht)",
        "zh-tw": "Chinesisch (traditionell)",
        "ja": "Japanisch",
        "ko": "Koreanisch",
        "ar": "Arabisch",
        "tr": "Türkisch",
        "unknown": "Unbekannt",
    }
    return language_names.get(code, code.upper())


def load_documents_from_chroma(db_path: str) -> List[Dict]:
    """
    Lädt alle Dokumente aus der ChromaDB.
    
    Args:
        db_path: Pfad zur ChromaDB
        
    Returns:
        Liste von Dokumenten mit content und metadata
    """
    import chromadb
    
    print(f"📂 Lade Dokumente aus: {db_path}")
    
    client = chromadb.PersistentClient(path=db_path)
    
    # Alle Collections auflisten
    collections = client.list_collections()
    
    if not collections:
        print("❌ Keine Collections in der Datenbank gefunden!")
        return []
    
    all_docs = []
    
    for collection in collections:
        print(f"   📁 Collection: {collection.name}")
        
        # Alle Dokumente aus der Collection laden
        results = collection.get(include=["documents", "metadatas"])
        
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        ids = results.get("ids", [])
        
        for i, (doc_id, doc, meta) in enumerate(zip(ids, documents, metadatas)):
            if doc:
                all_docs.append({
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta or {},
                    "collection": collection.name
                })
    
    print(f"   ✅ {len(all_docs)} Dokumente geladen\n")
    return all_docs


def load_documents_from_sqlite(db_path: str) -> List[Dict]:
    """
    Lädt Dokumente aus der SQLite Content-Datenbank.
    
    Args:
        db_path: Pfad zur SQLite-Datenbank
        
    Returns:
        Liste von Dokumenten
    """
    import sqlite3
    
    print(f"📂 Lade Dokumente aus SQLite: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tabellen auflisten
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"   📋 Tabellen: {[t[0] for t in tables]}")
    
    all_docs = []
    
    # Versuche gängige Tabellennamen
    for table_name in ["documents", "content", "pages", "chunks"]:
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            columns = [description[0] for description in cursor.description]
            
            # Finde content-ähnliche Spalte
            content_col = None
            for col in ["content", "text", "page_content", "body", "document"]:
                if col in columns:
                    content_col = col
                    break
            
            if content_col:
                cursor.execute(f"SELECT rowid, {content_col} FROM {table_name}")
                rows = cursor.fetchall()
                
                for row_id, content in rows:
                    if content:
                        all_docs.append({
                            "id": f"{table_name}_{row_id}",
                            "content": content,
                            "metadata": {"table": table_name},
                            "collection": table_name
                        })
                
                print(f"   ✅ {len(rows)} Dokumente aus '{table_name}' geladen")
        except sqlite3.OperationalError:
            continue
    
    conn.close()
    print(f"   ✅ Gesamt: {len(all_docs)} Dokumente\n")
    return all_docs


def analyze_languages(
    documents: List[Dict],
    sample_size: Optional[int] = None,
    show_examples: bool = True
) -> Dict:
    """
    Analysiert die Sprachen aller Dokumente.
    
    Args:
        documents: Liste der Dokumente
        sample_size: Optional - nur Stichprobe analysieren
        show_examples: Beispiele pro Sprache anzeigen
        
    Returns:
        Analyse-Ergebnisse als Dictionary
    """
    from tqdm import tqdm
    
    if sample_size and sample_size < len(documents):
        print(f"🎲 Stichprobe: {sample_size} von {len(documents)} Dokumenten (Seed: {RANDOM_SEED})")
        documents = random.sample(documents, sample_size)
    
    print(f"🔍 Analysiere {len(documents)} Dokumente...\n")
    
    # Ergebnisse sammeln
    language_counts = Counter()
    language_docs = defaultdict(list)
    confidence_scores = defaultdict(list)
    low_confidence = []
    
    for doc in tqdm(documents, desc="Sprachanalyse"):
        lang, confidence = detect_language_safe(doc["content"])
        
        language_counts[lang] += 1
        confidence_scores[lang].append(confidence)
        
        # Beispiele speichern (max 3 pro Sprache)
        if len(language_docs[lang]) < 3:
            language_docs[lang].append({
                "id": doc["id"],
                "preview": doc["content"][:200].replace("\n", " "),
                "confidence": confidence,
                "source": doc.get("metadata", {}).get("source", "unbekannt")
            })
        
        # Niedrige Konfidenz tracken
        if confidence < 0.8 and lang != "unknown":
            low_confidence.append({
                "id": doc["id"],
                "lang": lang,
                "confidence": confidence,
                "preview": doc["content"][:100].replace("\n", " ")
            })
    
    # Statistiken berechnen
    total = sum(language_counts.values())
    
    results = {
        "total_documents": total,
        "language_distribution": {},
        "examples": language_docs,
        "low_confidence_samples": low_confidence[:10],
        "seed": RANDOM_SEED
    }
    
    print("\n" + "=" * 70)
    print("📊 SPRACHVERTEILUNG")
    print("=" * 70)
    
    # Sortiert nach Häufigkeit
    for lang, count in language_counts.most_common():
        percentage = (count / total) * 100
        avg_confidence = sum(confidence_scores[lang]) / len(confidence_scores[lang])
        lang_name = get_language_name(lang)
        
        results["language_distribution"][lang] = {
            "name": lang_name,
            "count": count,
            "percentage": round(percentage, 2),
            "avg_confidence": round(avg_confidence, 3)
        }
        
        # Balkendiagramm
        bar_length = int(percentage / 2)
        bar = "█" * bar_length
        
        print(f"{lang_name:20} │ {bar:50} │ {count:5} ({percentage:5.1f}%) │ Konfidenz: {avg_confidence:.2f}")
    
    print("=" * 70)
    
    # Beispiele anzeigen
    if show_examples:
        print("\n📝 BEISPIELE PRO SPRACHE")
        print("-" * 70)
        
        for lang in list(language_counts.keys())[:5]:  # Top 5 Sprachen
            lang_name = get_language_name(lang)
            print(f"\n🏷️  {lang_name} ({lang}):")
            
            for i, example in enumerate(language_docs[lang][:2], 1):
                print(f"   [{i}] {example['preview'][:80]}...")
                print(f"       Konfidenz: {example['confidence']:.2f} | Quelle: {example['source']}")
    
    # Warnungen bei niedrigen Konfidenzen
    if low_confidence:
        print("\n⚠️  DOKUMENTE MIT NIEDRIGER KONFIDENZ (<0.8)")
        print("-" * 70)
        for item in low_confidence[:5]:
            print(f"   ID: {item['id']}")
            print(f"   Sprache: {get_language_name(item['lang'])} ({item['confidence']:.2f})")
            print(f"   Preview: {item['preview']}...")
            print()
    
    return results


def export_results(results: Dict, output_path: str):
    """Exportiert Ergebnisse als CSV."""
    import csv
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Sprache", "Code", "Anzahl", "Prozent", "Durchschnittliche Konfidenz"])
        
        for code, data in results["language_distribution"].items():
            writer.writerow([
                data["name"],
                code,
                data["count"],
                f"{data['percentage']:.2f}%",
                f"{data['avg_confidence']:.3f}"
            ])
    
    print(f"\n💾 Ergebnisse exportiert nach: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analysiert die Sprache von Dokumenten in der Vektordatenbank",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python analyze_document_languages.py                    # Alle Dokumente analysieren
  python analyze_document_languages.py --sample 500       # Stichprobe von 500 Dokumenten
  python analyze_document_languages.py --export out.csv   # Ergebnisse exportieren
  python analyze_document_languages.py --db-path ./data/vector_db  # Spezifischer Pfad
        """
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default="./data/vector_db",
        help="Pfad zur ChromaDB Vektordatenbank (Standard: ./data/vector_db)"
    )
    
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=None,
        help="Pfad zur SQLite Content-Datenbank (optional)"
    )
    
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Nur eine Stichprobe von N Dokumenten analysieren"
    )
    
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Ergebnisse als CSV exportieren"
    )
    
    parser.add_argument(
        "--no-examples",
        action="store_true",
        help="Keine Beispiele anzeigen"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🌍 DOKUMENTEN-SPRACHANALYSE")
    print("=" * 70)
    print(f"   Seed: {RANDOM_SEED} (für Reproduzierbarkeit)")
    print()
    
    # Dokumente laden
    documents = []
    
    # ChromaDB
    if os.path.exists(args.db_path):
        documents.extend(load_documents_from_chroma(args.db_path))
    else:
        print(f"⚠️  ChromaDB nicht gefunden: {args.db_path}")
    
    # SQLite (optional)
    if args.sqlite_path and os.path.exists(args.sqlite_path):
        documents.extend(load_documents_from_sqlite(args.sqlite_path))
    
    if not documents:
        print("❌ Keine Dokumente gefunden!")
        print("\nMögliche Lösungen:")
        print("  1. Prüfen Sie den Pfad zur Datenbank")
        print("  2. Führen Sie zuerst das Crawling/Indexing aus")
        print("  3. Nutzen Sie --db-path oder --sqlite-path")
        sys.exit(1)
    
    # Analyse durchführen
    results = analyze_languages(
        documents,
        sample_size=args.sample,
        show_examples=not args.no_examples
    )
    
    # Export
    if args.export:
        export_results(results, args.export)
    
    # Zusammenfassung
    print("\n" + "=" * 70)
    print("📈 ZUSAMMENFASSUNG")
    print("=" * 70)
    
    dist = results["language_distribution"]
    
    # Hauptsprache
    if dist:
        main_lang = max(dist.items(), key=lambda x: x[1]["count"])
        print(f"   Hauptsprache: {main_lang[1]['name']} ({main_lang[1]['percentage']:.1f}%)")
    
    # Mehrsprachigkeit
    multi_lang = [k for k, v in dist.items() if v["percentage"] > 1.0 and k != "unknown"]
    if len(multi_lang) > 1:
        print(f"   Mehrsprachig: Ja ({len(multi_lang)} Sprachen mit >1%)")
    else:
        print(f"   Mehrsprachig: Nein (hauptsächlich einsprachig)")
    
    # Unbekannte
    unknown_pct = dist.get("unknown", {}).get("percentage", 0)
    if unknown_pct > 5:
        print(f"   ⚠️  Hoher Anteil unerkannter Dokumente: {unknown_pct:.1f}%")
    
    print("=" * 70)


if __name__ == "__main__":
    # Abhängigkeiten prüfen
    try:
        import langdetect
        import tqdm
        import chromadb
    except ImportError as e:
        print(f"❌ Fehlende Abhängigkeit: {e}")
        print("\nBitte installieren Sie:")
        print("  pip install langdetect tqdm chromadb")
        sys.exit(1)
    
    main()
