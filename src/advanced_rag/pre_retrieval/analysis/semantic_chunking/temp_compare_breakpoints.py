"""
Vergleich: Static Threshold vs Percentile Breakpoint-Methoden
==============================================================
Analysiert ein Dokument und zeigt für jeden Satzübergang:
- Similarity-Wert
- Ob Static Threshold einen Breakpoint setzen würde
- Ob Percentile-Methode einen Breakpoint setzen würde

WICHTIG: Nutzt ausschließlich den produktiven Code!
- Text-Extraktion: naive_extract_text_from_html aus run_production_scraper.py
- Chunking-Logik: SemanticChunker aus chunking.py
"""

import sqlite3
import gzip
import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================================
# PRODUKTIVER CODE - IMPORTS
# ============================================================================
from src.scraper.run_production_scraper import naive_extract_text_from_html
from src.advanced_rag.pre_retrieval.chunking import SemanticChunker
from src.advanced_rag.rag_config import RAGConfig

# Lade RAG Config für Parameter
rag_config = RAGConfig.load_from_env()
STATIC_THRESHOLD = rag_config.semantic_chunking_similarity_threshold
PERCENTILE = rag_config.semantic_chunking_percentile

print(f"📊 Parameter aus rag.env:")
print(f"   Static Threshold: {STATIC_THRESHOLD}")
print(f"   Percentile: {PERCENTILE}th")

# ============================================================================
# PRODUKTIVER SEMANTIC CHUNKER - Instanziierung
# ============================================================================
# Wir nutzen den produktiven SemanticChunker für alle Berechnungen
chunker = SemanticChunker(
    max_chunk_size=rag_config.semantic_chunking_max_size,
    min_chunk_size=rag_config.semantic_chunking_min_size,
    overlap=rag_config.semantic_chunking_overlap,
    similarity_threshold=STATIC_THRESHOLD,
    use_percentile=False,  # Wir testen beide Methoden manuell
    percentile=PERCENTILE,
    embedding_model=None,  # Wird lazy geladen
    debug_overlap=False
)

print(f"✅ SemanticChunker instanziiert mit produktiven Parametern")

# ============================================================================
# DOKUMENT LADEN
# ============================================================================
print("\n📄 Lade Dokument aus Datenbank...")

# Spezifische URL für Analyse
TARGET_URL = "https://wiso.uni-koeln.de/de/studium/bewerbung/studium-an-der-wiso-fakultaet"

conn = sqlite3.connect('data/content_database.db')
cursor = conn.cursor()
cursor.execute("""
    SELECT id, url, title, content, content_type 
    FROM documents 
    WHERE url = ?
""", (TARGET_URL,))
row = cursor.fetchone()

if not row:
    print(f"❌ Dokument nicht gefunden: {TARGET_URL}")
    conn.close()
    exit(1)

doc_id, url, title, content, content_type = row
print(f"   ID: {doc_id}")
print(f"   Title: {title}")
print(f"   URL: {url}")

# ============================================================================
# TEXT-EXTRAKTION - PRODUKTIVER CODE
# ============================================================================
print("\n📝 Extrahiere Text (produktiver Code: naive_extract_text_from_html)...")
html = gzip.decompress(content).decode('utf-8')
text = naive_extract_text_from_html(html)
print(f"   Text-Länge: {len(text):,} Zeichen")

conn.close()

# ============================================================================
# SATZ-SPLITTING - PRODUKTIVER CODE
# ============================================================================
print("\n✂️ Teile in Sätze (produktiver Code: SemanticChunker._split_into_sentences)...")
sentences = chunker._split_into_sentences(text)
print(f"   Anzahl Sätze: {len(sentences)}")

if len(sentences) < 2:
    print("❌ Zu wenig Sätze für Analyse")
    exit(1)

# ============================================================================
# EMBEDDINGS - PRODUKTIVER CODE
# ============================================================================
print("\n🧮 Berechne Embeddings (produktiver Code: SemanticChunker._compute_embeddings)...")
embeddings = chunker._compute_embeddings(sentences)
print(f"   Embedding-Shape: {embeddings.shape}")

# ============================================================================
# SIMILARITY-BERECHNUNG - PRODUKTIVER CODE
# ============================================================================
print("\n📐 Berechne Similarities (produktiver Code: SemanticChunker._compute_all_similarities)...")
similarities = chunker._compute_all_similarities(embeddings)
print(f"   Anzahl Similarity-Werte: {len(similarities)}")

# ============================================================================
# BREAKPOINTS - PRODUKTIVER CODE
# ============================================================================
print("\n🔍 Berechne Breakpoints (produktiver Code)...")

# Static Threshold
static_breakpoints = chunker._find_breakpoints_static_threshold(similarities)
print(f"   Static Threshold ({STATIC_THRESHOLD}): {len(static_breakpoints)} Breakpoints")

# Percentile
percentile_breakpoints = chunker._find_breakpoints_percentile(similarities)
percentile_threshold = np.percentile(similarities, PERCENTILE)
print(f"   Percentile ({PERCENTILE}th = {percentile_threshold:.4f}): {len(percentile_breakpoints)} Breakpoints")

# ============================================================================
# CHUNKS ERSTELLEN - PRODUKTIVER CODE
# ============================================================================
print("\n🔨 Erstelle Chunks mit produktivem SemanticChunker...")

# Static Threshold Chunks
chunker_static = SemanticChunker(
    max_chunk_size=rag_config.semantic_chunking_max_size,
    min_chunk_size=rag_config.semantic_chunking_min_size,
    overlap=rag_config.semantic_chunking_overlap,
    similarity_threshold=STATIC_THRESHOLD,
    use_percentile=False,
    percentile=PERCENTILE,
    embedding_model=chunker.embedding_model,  # Wiederverwende geladenes Modell
    debug_overlap=False
)
static_chunks = chunker_static.chunk_by_paragraphs(text)
print(f"   Static Threshold: {len(static_chunks)} Chunks")

# Percentile Chunks
chunker_percentile = SemanticChunker(
    max_chunk_size=rag_config.semantic_chunking_max_size,
    min_chunk_size=rag_config.semantic_chunking_min_size,
    overlap=rag_config.semantic_chunking_overlap,
    similarity_threshold=STATIC_THRESHOLD,
    use_percentile=True,
    percentile=PERCENTILE,
    embedding_model=chunker.embedding_model,  # Wiederverwende geladenes Modell
    debug_overlap=False
)
percentile_chunks = chunker_percentile.chunk_by_paragraphs(text)
print(f"   Percentile ({PERCENTILE}th): {len(percentile_chunks)} Chunks")

# ============================================================================
# STATISTIKEN
# ============================================================================
print("\n📈 Similarity-Statistiken:")
print(f"   Min: {min(similarities):.4f}")
print(f"   Max: {max(similarities):.4f}")
print(f"   Mean: {np.mean(similarities):.4f}")
print(f"   Median: {np.median(similarities):.4f}")
print(f"   {PERCENTILE}th Percentile: {percentile_threshold:.4f}")

# ============================================================================
# EXCEL EXPORT - INDIVIDUELL FÜR ANALYSE
# ============================================================================
print("\n📊 Erstelle Excel-Export...")

# Sheet 1: Satz-Analyse
data = []
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
    
    data.append(row_data)

df_sentences = pd.DataFrame(data)

# Sheet 2: Statistiken
stats_data = {
    'Metrik': [
        'Dokument URL',
        'Dokument Titel',
        'Text-Länge (Zeichen)',
        'Anzahl Sätze',
        'Anzahl Satzübergänge',
        '',
        'Min Similarity',
        'Max Similarity',
        'Mean Similarity',
        'Median Similarity',
        'Std Similarity',
        '',
        'Static Threshold (aus rag.env)',
        f'{PERCENTILE}th Percentile Threshold (berechnet)',
        '',
        'Static Breakpoints',
        'Percentile Breakpoints',
        '',
        'Static → Chunks (tatsächlich)',
        'Percentile → Chunks (tatsächlich)',
    ],
    'Wert': [
        url,
        title,
        len(text),
        len(sentences),
        len(similarities),
        '',
        round(min(similarities), 4),
        round(max(similarities), 4),
        round(np.mean(similarities), 4),
        round(np.median(similarities), 4),
        round(np.std(similarities), 4),
        '',
        STATIC_THRESHOLD,
        round(percentile_threshold, 4),
        '',
        len(static_breakpoints),
        len(percentile_breakpoints),
        '',
        len(static_chunks),
        len(percentile_chunks),
    ]
}
df_stats = pd.DataFrame(stats_data)

# Sheet 3: Similarity-Verteilung
bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
hist, _ = np.histogram(similarities, bins=bins)
distribution_data = {
    'Similarity_Bereich': [f'{bins[i]:.1f} - {bins[i+1]:.1f}' for i in range(len(bins)-1)],
    'Anzahl': hist.tolist(),
    'Anteil_%': [round(h / len(similarities) * 100, 1) for h in hist]
}
df_distribution = pd.DataFrame(distribution_data)

# Sheet 4: Static Threshold Chunks
static_chunks_data = []
for i, chunk in enumerate(static_chunks):
    static_chunks_data.append({
        'Chunk_Index': i + 1,
        'Chunk_Länge': len(chunk),
        'Chunk_Text': chunk
    })
df_static_chunks = pd.DataFrame(static_chunks_data)

# Sheet 5: Percentile Chunks
percentile_chunks_data = []
for i, chunk in enumerate(percentile_chunks):
    percentile_chunks_data.append({
        'Chunk_Index': i + 1,
        'Chunk_Länge': len(chunk),
        'Chunk_Text': chunk
    })
df_percentile_chunks = pd.DataFrame(percentile_chunks_data)

# Speichere Excel
output_path = Path('src/evaluation/data/breakpoint_comparison.xlsx')
output_path.parent.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df_stats.to_excel(writer, sheet_name='Statistiken', index=False)
    df_distribution.to_excel(writer, sheet_name='Similarity-Verteilung', index=False)
    df_sentences.to_excel(writer, sheet_name='Satz-Analyse', index=False)
    df_static_chunks.to_excel(writer, sheet_name='Chunks_Static', index=False)
    df_percentile_chunks.to_excel(writer, sheet_name='Chunks_Percentile', index=False)

print(f"\n✅ Excel exportiert: {output_path}")

# ============================================================================
# ZUSAMMENFASSUNG
# ============================================================================
print(f"\n📊 Zusammenfassung:")
print(f"   Static Threshold ({STATIC_THRESHOLD}): {len(static_breakpoints)} Breakpoints → {len(static_chunks)} Chunks (tatsächlich)")
print(f"   Percentile ({PERCENTILE}th = {percentile_threshold:.4f}): {len(percentile_breakpoints)} Breakpoints → {len(percentile_chunks)} Chunks (tatsächlich)")

# Zeige Beispiel-Breakpoints
print(f"\n📋 Beispiel-Breakpoints (erste 5):")
all_bp_indices = sorted(set(static_breakpoints) | set(percentile_breakpoints))
bp_shown = 0
for bp_idx in all_bp_indices:
    if bp_shown >= 5:
        break
    # bp_idx ist der Index des ersten Satzes im neuen Chunk
    # Similarity liegt zwischen Satz bp_idx-1 und bp_idx
    sim_idx = bp_idx - 1
    if sim_idx < len(similarities):
        sim = similarities[sim_idx]
        static_marker = "✓" if bp_idx in static_breakpoints else " "
        percentile_marker = "✓" if bp_idx in percentile_breakpoints else " "
        print(f"   Satz {sim_idx+1}→{bp_idx+1}: sim={sim:.4f} | Static: {static_marker} | Percentile: {percentile_marker}")
        print(f"      → '{sentences[sim_idx][:60]}...'")
        bp_shown += 1
