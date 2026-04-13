"""
Multi-Dokument Chunking-Analyse — wtpsplit Sentence Splitter
=============================================================
Identisch zu temp_multi_doc_analysis.py, aber der Sentence Splitter wird
durch wtpsplit (SaT, Modell: sat-3l) ersetzt.

Ausgetauscht:
    base_chunker._split_into_sentences(text)
    → sat.split(text)  [wtpsplit SaT sat-3l]

Alles andere (Embeddings, Similarities, Breakpoints, Chunking, Excel-Export)
bleibt unverändert und nutzt ausschließlich den produktiven SemanticChunker-Code.
"""

import sqlite3
import gzip
import random
import numpy as np
import pandas as pd
from pathlib import Path
from wtpsplit import SaT

# ============================================================================
# PRODUKTIVER CODE - IMPORTS
# ============================================================================
from src.scraper.run_production_scraper import naive_extract_text_from_html
from src.advanced_rag.pre_retrieval.chunking import SemanticChunker
from src.advanced_rag.rag_config import RAGConfig

# Lade RAG Config
rag_config = RAGConfig.load_from_env()
STATIC_THRESHOLD = rag_config.semantic_chunking_similarity_threshold
PERCENTILE = rag_config.semantic_chunking_percentile

print(f"📊 Parameter aus rag.env:")
print(f"   Static Threshold: {STATIC_THRESHOLD}")
print(f"   Percentile: {PERCENTILE}th")
print(f"   Max Size: {rag_config.semantic_chunking_max_size}")
print(f"   Min Size: {rag_config.semantic_chunking_min_size}")
print(f"   Overlap: {rag_config.semantic_chunking_overlap}")

# ============================================================================
# DOKUMENTE DEFINIEREN (2 HTML, 2 PDF) - zufällig per seed=42
# ============================================================================
random.seed(42)

conn_seed = sqlite3.connect('data/content_database.db')
cursor_seed = conn_seed.cursor()
cursor_seed.execute("SELECT id, url, title, content_type FROM documents WHERE content_type = 'html'")
_html_docs = cursor_seed.fetchall()
cursor_seed.execute("SELECT id, url, title, content_type FROM documents WHERE content_type = 'pdf'")
_pdf_docs = cursor_seed.fetchall()
conn_seed.close()

_sel_html = random.sample(_html_docs, 2)
_sel_pdf = random.sample(_pdf_docs, 2)

TEST_DOCUMENTS = [
    # HTML Dokumente (seed=42)
    {"id": _sel_html[0][0], "type": "HTML", "name": _sel_html[0][2][:30].replace(" ", "_")},
    {"id": _sel_html[1][0], "type": "HTML", "name": _sel_html[1][2][:30].replace(" ", "_")},
    # PDF Dokumente (seed=42)
    {"id": _sel_pdf[0][0], "type": "PDF", "name": _sel_pdf[0][2][:30].replace(" ", "_")},
    {"id": _sel_pdf[1][0], "type": "PDF", "name": _sel_pdf[1][2][:30].replace(" ", "_")},
]

print("\n📋 Ausgewählte Dokumente (seed=42):")
for d in TEST_DOCUMENTS:
    print(f"   [{d['type']}] ID {d['id']}: {d['name']}")

# ============================================================================
# WTPSPLIT: SaT sat-3l laden (ersetzt _split_into_sentences)
# ============================================================================
print("\n✂️ Lade wtpsplit SaT-Modell (sat-3l)...")
sat = SaT("sat-3l")
print("✅ wtpsplit sat-3l geladen")


def split_sentences_wtpsplit(text: str) -> list[str]:
    """
    Ersetzt SemanticChunker._split_into_sentences mit wtpsplit sat-3l.

    wtpsplit respektiert Input-Zeilenumbrüche (split_on_input_newlines=True
    ist der Standard), d.h. Absätze werden nie zusammengemischt.
    Die Ausgabe von sat.split() sind Strings, die ggf. trailing whitespace
    enthalten — dieser wird per strip() bereinigt.
    """
    # sat.split gibt bei einem einzelnen String eine Liste von Strings zurück
    raw_sentences = sat.split(text)
    # Leere Strings und reinen Whitespace herausfiltern, trailing spaces trimmen
    sentences = [s.strip() for s in raw_sentences if s and s.strip()]
    return sentences


# ============================================================================
# CHUNKER INSTANZIIEREN (Embedding-Modell wird geteilt)
# ============================================================================
print("\n🤖 Lade Embedding-Modell...")
base_chunker = SemanticChunker(
    max_chunk_size=rag_config.semantic_chunking_max_size,
    min_chunk_size=rag_config.semantic_chunking_min_size,
    overlap=rag_config.semantic_chunking_overlap,
    similarity_threshold=STATIC_THRESHOLD,
    use_percentile=False,
    percentile=PERCENTILE,
    embedding_model=None,
    debug_overlap=False
)
# Trigger lazy loading
_ = base_chunker.embedding_model
print("✅ Embedding-Modell geladen")

# Static Threshold Chunker
chunker_static = SemanticChunker(
    max_chunk_size=rag_config.semantic_chunking_max_size,
    min_chunk_size=rag_config.semantic_chunking_min_size,
    overlap=rag_config.semantic_chunking_overlap,
    similarity_threshold=STATIC_THRESHOLD,
    use_percentile=False,
    percentile=PERCENTILE,
    embedding_model=base_chunker.embedding_model,
    debug_overlap=False
)

# Percentile Chunker
chunker_percentile = SemanticChunker(
    max_chunk_size=rag_config.semantic_chunking_max_size,
    min_chunk_size=rag_config.semantic_chunking_min_size,
    overlap=rag_config.semantic_chunking_overlap,
    similarity_threshold=STATIC_THRESHOLD,
    use_percentile=True,
    percentile=PERCENTILE,
    embedding_model=base_chunker.embedding_model,
    debug_overlap=False
)

# ============================================================================
# DOKUMENTE LADEN UND ANALYSIEREN
# ============================================================================
conn = sqlite3.connect('data/content_database.db')
cursor = conn.cursor()

all_results = []
all_chunks_static = {}
all_chunks_percentile = {}
all_sentences = {}

for doc_info in TEST_DOCUMENTS:
    doc_id = doc_info["id"]
    doc_type = doc_info["type"]
    doc_name = doc_info["name"]

    print(f"\n{'='*60}")
    print(f"📄 Dokument: {doc_name} (ID: {doc_id}, Typ: {doc_type})")
    print('='*60)

    cursor.execute("""
        SELECT id, url, title, content, content_type
        FROM documents
        WHERE id = ?
    """, (doc_id,))
    row = cursor.fetchone()

    if not row:
        print(f"   ❌ Dokument nicht gefunden!")
        continue

    _, url, title, content, content_type = row
    print(f"   Title: {title[:50]}...")
    print(f"   URL: {url[:60]}...")

    # Text extrahieren
    if content_type == 'html':
        html = gzip.decompress(content).decode('utf-8')
        text = naive_extract_text_from_html(html)
    else:  # PDF
        text = gzip.decompress(content).decode('utf-8')

    print(f"   Text-Länge: {len(text):,} Zeichen")

    # -----------------------------------------------------------------------
    # SENTENCE SPLITTING — wtpsplit statt base_chunker._split_into_sentences
    # -----------------------------------------------------------------------
    sentences = split_sentences_wtpsplit(text)
    print(f"   Anzahl Sätze (wtpsplit sat-3l): {len(sentences)}")

    if len(sentences) < 2:
        print("   ⚠️ Zu wenig Sätze für Analyse")
        continue

    # Rest der Pipeline: produktiver SemanticChunker-Code
    embeddings = base_chunker._compute_embeddings(sentences)
    similarities = base_chunker._compute_all_similarities(embeddings)

    # Breakpoints
    static_breakpoints = base_chunker._find_breakpoints_static_threshold(similarities)
    percentile_breakpoints = base_chunker._find_breakpoints_percentile(similarities)
    percentile_threshold = np.percentile(similarities, PERCENTILE) if similarities else 0

    print(f"   Static Breakpoints: {len(static_breakpoints)}")
    print(f"   Percentile Breakpoints: {len(percentile_breakpoints)} (threshold: {percentile_threshold:.4f})")

    # Chunks erstellen — chunk_by_paragraphs nutzt intern ebenfalls _split_into_sentences,
    # daher patchen wir die Methode auf dem Chunker-Objekt für diesen Lauf.
    def _wtpsplit_sentences(self_inner, t):
        return split_sentences_wtpsplit(t)

    import types
    chunker_static._split_into_sentences = types.MethodType(_wtpsplit_sentences, chunker_static)
    chunker_percentile._split_into_sentences = types.MethodType(_wtpsplit_sentences, chunker_percentile)

    static_chunks = chunker_static.chunk_by_paragraphs(text)
    percentile_chunks = chunker_percentile.chunk_by_paragraphs(text)

    print(f"   Static Chunks: {len(static_chunks)}")
    print(f"   Percentile Chunks: {len(percentile_chunks)}")

    # Ergebnisse sammeln
    result = {
        'Dokument': doc_name,
        'Typ': doc_type,
        'ID': doc_id,
        'URL': url,
        'Title': title,
        'Text_Länge': len(text),
        'Anzahl_Sätze': len(sentences),
        'Min_Similarity': round(min(similarities), 4) if similarities else None,
        'Max_Similarity': round(max(similarities), 4) if similarities else None,
        'Mean_Similarity': round(np.mean(similarities), 4) if similarities else None,
        'Median_Similarity': round(np.median(similarities), 4) if similarities else None,
        'Static_Threshold': STATIC_THRESHOLD,
        'Percentile_Threshold': round(percentile_threshold, 4),
        'Static_Breakpoints': len(static_breakpoints),
        'Percentile_Breakpoints': len(percentile_breakpoints),
        'Static_Chunks': len(static_chunks),
        'Percentile_Chunks': len(percentile_chunks),
    }
    all_results.append(result)

    # Chunks für separate Sheets
    all_chunks_static[doc_name] = [
        {'Chunk_Index': i+1, 'Chunk_Länge': len(c), 'Chunk_Text': c}
        for i, c in enumerate(static_chunks)
    ]
    all_chunks_percentile[doc_name] = [
        {'Chunk_Index': i+1, 'Chunk_Länge': len(c), 'Chunk_Text': c}
        for i, c in enumerate(percentile_chunks)
    ]

    # Satz-Analyse mit Breakpoint-Markierungen
    sentences_data = []
    for i in range(len(sentences)):
        row_data = {
            'Satz_Index': i + 1,
            'Satz_Text': sentences[i],
            'Satz_Länge': len(sentences[i]),
        }

        if i < len(similarities):
            sim = similarities[i]
            row_data['Similarity_zum_nächsten'] = round(sim, 4)
            row_data['Static_Breakpoint'] = 'JA' if (i + 1) in static_breakpoints else 'NEIN'
            row_data['Percentile_Breakpoint'] = 'JA' if (i + 1) in percentile_breakpoints else 'NEIN'
        else:
            row_data['Similarity_zum_nächsten'] = None
            row_data['Static_Breakpoint'] = '-'
            row_data['Percentile_Breakpoint'] = '-'

        sentences_data.append(row_data)

    all_sentences[doc_name] = sentences_data

conn.close()

# ============================================================================
# EXCEL EXPORT
# ============================================================================
print("\n📊 Erstelle Excel-Export...")

output_path = Path('src/evaluation/data/multi_doc_chunking_analysis_wtpsplit.xlsx')
output_path.parent.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    # Übersicht
    df_overview = pd.DataFrame(all_results)
    df_overview.to_excel(writer, sheet_name='Übersicht', index=False)

    # Chunks und Sätze pro Dokument
    for doc_name in all_chunks_static.keys():
        # Satz-Analyse mit Breakpoints
        df_sentences = pd.DataFrame(all_sentences[doc_name])
        sheet_name_sentences = f'{doc_name[:18]}_Sätze'
        df_sentences.to_excel(writer, sheet_name=sheet_name_sentences, index=False)

        # Static Chunks
        df_static = pd.DataFrame(all_chunks_static[doc_name])
        sheet_name_static = f'{doc_name[:18]}_Static'
        df_static.to_excel(writer, sheet_name=sheet_name_static, index=False)

        # Percentile Chunks
        df_percentile = pd.DataFrame(all_chunks_percentile[doc_name])
        sheet_name_percentile = f'{doc_name[:18]}_Percent'
        df_percentile.to_excel(writer, sheet_name=sheet_name_percentile, index=False)

print(f"\n✅ Excel exportiert: {output_path}")

# ============================================================================
# ZUSAMMENFASSUNG
# ============================================================================
print("\n" + "="*60)
print("📊 ZUSAMMENFASSUNG (wtpsplit sat-3l)")
print("="*60)
print(f"{'Dokument':<25} {'Typ':<5} {'Sätze':>6} {'Static':>8} {'Percent':>8}")
print("-"*60)
for r in all_results:
    print(f"{r['Dokument']:<25} {r['Typ']:<5} {r['Anzahl_Sätze']:>6} {r['Static_Chunks']:>8} {r['Percentile_Chunks']:>8}")
