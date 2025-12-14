"""
Content Deduplication für Web Scraping
======================================

Entfernt near-duplicate Dokumente mithilfe von MinHash und Simhash.

Enthält:
- normalize_text(): Text-Normalisierung für Exact-Deduplication
- ContentDeduplicator: Near-Duplicate-Erkennung via Shingling/Jaccard
"""

import hashlib
import re
import unicodedata
from typing import List, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
import logging

# Excel-Formatierung
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

logger = logging.getLogger(__name__)


# ============================================================================
# TEXT-NORMALISIERUNG FÜR EXACT-DEDUPLICATION
# ============================================================================

def normalize_text(text: str) -> str:
    """
    Normalisiere Text für Exact-Deduplication (Hashing).
    
    Diese Funktion bereitet Text so auf, dass Dokumente als gleich erkannt werden,
    wenn sie sich nur in Typografie, Groß-/Kleinschreibung, Whitespace und 
    Aufzählungsmarkern unterscheiden.
    
    Normalisierungsschritte:
    1. Lowercasing
    2. Unicode-Normalisierung (NFKC)
    3. Typografische Vereinheitlichung (Anführungszeichen, Bindestriche, NBSP)
    4. Entfernung von Aufzählungsmarkern am Zeilenanfang
    5. Entfernung dekorativer Sequenzen (----, ====, etc.)
    6. Whitespace-Normalisierung
    
    Was NICHT gemacht wird:
    - Keine Entfernung/Vereinheitlichung von Zahlen und Datumsangaben
    - Kein Stemming oder Lemmatizing
    - Umlaute (ä, ö, ü) und ß bleiben erhalten
    
    Args:
        text: Eingabetext (kann None oder leer sein)
        
    Returns:
        Normalisierter Text für Hashing
    """
    # Robuste Behandlung von None/leerem Input
    if not text:
        return ""
    
    if not isinstance(text, str):
        text = str(text)
    
    # 1. Lowercasing
    text = text.lower()
    
    # 2. Unicode-Normalisierung (NFKC)
    # - Vereinheitlicht Kompatibilitätszeichen (z.B. ﬁ → fi)
    # - Kombiniert diakritische Zeichen
    text = unicodedata.normalize('NFKC', text)
    
    # 3. Typografische Vereinheitlichung
    # 3a. Anführungszeichen → einfaches "
    quote_chars = [
        '"', '"',  # Typografische doppelte Anführungszeichen
        '„', '‟',  # Deutsche Anführungszeichen
        ''', ''',  # Typografische einfache Anführungszeichen
        '‚', '‛',  # Weitere einfache Anführungszeichen
        '«', '»',  # Guillemets
        '‹', '›',  # Einfache Guillemets
    ]
    for char in quote_chars:
        text = text.replace(char, '"')
    
    # 3b. Bindestrich-Varianten → normaler Bindestrich
    dash_chars = [
        '–',  # En-Dash
        '—',  # Em-Dash
        '―',  # Horizontal Bar
        '‐',  # Hyphen
        '‑',  # Non-Breaking Hyphen
        '⁃',  # Hyphen Bullet
    ]
    for char in dash_chars:
        text = text.replace(char, '-')
    
    # 3c. Geschützte/spezielle Leerzeichen → normales Space
    space_chars = [
        '\u00A0',  # Non-Breaking Space
        '\u2007',  # Figure Space
        '\u2008',  # Punctuation Space
        '\u2009',  # Thin Space
        '\u200A',  # Hair Space
        '\u200B',  # Zero-Width Space
        '\u202F',  # Narrow No-Break Space
        '\u205F',  # Medium Mathematical Space
        '\u3000',  # Ideographic Space
    ]
    for char in space_chars:
        text = text.replace(char, ' ')
    
    # 4. Entfernung von Aufzählungsmarkern am Zeilenanfang
    # Arbeite zeilenweise, falls noch Zeilenumbrüche vorhanden sind
    lines = text.split('\n')
    normalized_lines = []
    
    for line in lines:
        # Entferne führende Whitespaces für Pattern-Matching
        stripped = line.lstrip()
        
        # Pattern für Aufzählungsmarker am Zeilenanfang
        # Bullets: -, *, •, +, >, #
        # Nummerierung: 1., 2., 3., ...
        # Buchstaben: a), b), c), ... oder a., b., c., ...
        
        # Bullet-Marker entfernen
        bullet_pattern = r'^[\-\*\•\+\>\#]\s+'
        stripped = re.sub(bullet_pattern, '', stripped)
        
        # Nummerierte Listen: 1. , 2. , etc.
        number_pattern = r'^\d+[\.\)]\s+'
        stripped = re.sub(number_pattern, '', stripped)
        
        # Buchstaben-Listen: a), b), a., b., etc.
        letter_pattern = r'^[a-z][\.\)]\s+'
        stripped = re.sub(letter_pattern, '', stripped)
        
        # Markdown-Überschriften: #, ##, ###, etc.
        heading_pattern = r'^#{1,6}\s+'
        stripped = re.sub(heading_pattern, '', stripped)
        
        normalized_lines.append(stripped)
    
    text = '\n'.join(normalized_lines)
    
    # 5. Entfernung dekorativer Sequenzen
    # Linien aus wiederholten Zeichen: ----, ====, ****, ~~~~, etc.
    decorative_pattern = r'[\-=\*~_]{3,}'
    text = re.sub(decorative_pattern, '', text)
    
    # 6. Whitespace-Normalisierung
    # Alle Whitespace-Arten (Space, Tab, Newline, etc.) auf einzelnes Space
    text = re.sub(r'\s+', ' ', text)
    
    # Führende und trailing Whitespaces entfernen
    text = text.strip()
    
    return text


def compute_normalized_hash(text: str) -> str:
    """
    Berechne Hash für normalisierten Text (für Exact-Dedup).
    
    Kombiniert normalize_text() mit SHA256-Hashing.
    
    Args:
        text: Eingabetext
        
    Returns:
        SHA256-Hash des normalisierten Textes
    """
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def demo_normalization():
    """
    Demonstriert die Normalisierung mit Beispieltexten.
    
    Zeigt Original und normalisierten Text für verschiedene Fälle.
    """
    test_cases = [
        # Typografische Varianten
        ('Anführungszeichen', 
         '„Dies ist ein Test" und «noch einer»'),
        
        # Bindestriche
        ('Bindestriche', 
         'Hin- und Herfahrt – mit Em-Dash — und mehr'),
        
        # Aufzählungen
        ('Bullet-Liste', 
         '- Punkt 1\n* Punkt 2\n• Punkt 3\n+ Punkt 4'),
        
        # Nummerierte Liste
        ('Nummerierte Liste', 
         '1. Erster Punkt\n2. Zweiter Punkt\na) Unterpunkt\nb) Noch einer'),
        
        # Markdown-Überschriften
        ('Markdown-Headings', 
         '# Überschrift 1\n## Überschrift 2\n### Überschrift 3'),
        
        # Dekorative Linien
        ('Dekorative Linien', 
         'Text davor\n--------------------\nText danach\n====================\nEnde'),
        
        # Geschützte Leerzeichen
        ('Geschützte Leerzeichen', 
         'Wort\u00A0mit\u00A0NBSP\u00A0Zeichen'),
        
        # Gemischter Fall
        ('Gemischter Fall', 
         '## „Studienordnung" 2024\n- Punkt 1: Hin- und Rückfahrt\n- Punkt 2: 30 LP erforderlich\n----\nWeiterer Text'),
    ]
    
    print("=" * 80)
    print("DEMO: Text-Normalisierung für Exact-Deduplication")
    print("=" * 80)
    
    for name, original in test_cases:
        normalized = normalize_text(original)
        print(f"\n📝 {name}:")
        print(f"   Original:    {repr(original)}")
        print(f"   Normalisiert: {repr(normalized)}")
    
    print("\n" + "=" * 80)
    print("✅ Demo abgeschlossen")
    print("=" * 80)


# ============================================================================
# EXACT-DEDUPLICATION AUF DOKUMENT-EBENE
# ============================================================================

def deduplicate_documents_exact(
    documents: list[dict],
    text_key: str = 'text',
    id_key: str = 'doc_id'
) -> tuple[list[dict], list[dict], dict]:
    """
    Exact-Deduplication auf Dokument-Ebene (VOR Chunking).
    
    Findet Dokumente mit identischem Inhalt nach Normalisierung und
    entfernt Duplikate. Behält jeweils das erste Dokument einer Gruppe.
    
    Args:
        documents: Liste von Dokumenten als Dictionaries
                   Erwartet mindestens: {text_key: "...", id_key: "..."}
        text_key: Schlüssel für den Textinhalt (default: 'text')
        id_key: Schlüssel für die Dokument-ID (default: 'doc_id')
    
    Returns:
        Tuple von:
        - unique_documents: Liste der behaltenen Dokumente
        - removed_documents: Liste der entfernten Duplikate
        - stats: Dictionary mit Statistiken
    
    Example:
        >>> docs = [
        ...     {"doc_id": "1", "text": "Hello World", "url": "a.html"},
        ...     {"doc_id": "2", "text": "hello world", "url": "b.html"},  # Duplikat!
        ...     {"doc_id": "3", "text": "Different text", "url": "c.html"},
        ... ]
        >>> unique, removed, stats = deduplicate_documents_exact(docs)
        >>> len(unique)
        2
        >>> stats['duplicates_removed']
        1
    """
    from collections import defaultdict
    
    if not documents:
        return [], [], {"total": 0, "unique": 0, "duplicates_removed": 0, "duplicate_groups": 0}
    
    # Hash-Berechnung mit Gruppierung
    hash_to_docs = defaultdict(list)
    
    for doc in documents:
        text = doc.get(text_key, '')
        doc_hash = compute_normalized_hash(text)
        # Speichere Hash im Dokument für spätere Referenz
        doc['_normalized_hash'] = doc_hash
        hash_to_docs[doc_hash].append(doc)
    
    # Trenne unique von Duplikaten
    unique_documents = []
    removed_documents = []
    duplicate_groups = {}
    
    for doc_hash, docs in hash_to_docs.items():
        # Erstes Dokument behalten
        unique_documents.append(docs[0])
        
        # Rest sind Duplikate
        if len(docs) > 1:
            duplicate_groups[doc_hash] = docs
            for dup_doc in docs[1:]:
                dup_doc['_kept_doc_id'] = docs[0].get(id_key, 'unknown')
                removed_documents.append(dup_doc)
    
    stats = {
        "total": len(documents),
        "unique": len(unique_documents),
        "duplicates_removed": len(removed_documents),
        "duplicate_groups": len(duplicate_groups),
        "reduction_percent": (len(removed_documents) / len(documents) * 100) if documents else 0
    }
    
    logger.info(
        f"Exact-Dedup: {stats['total']} → {stats['unique']} Dokumente "
        f"({stats['duplicates_removed']} entfernt, {stats['reduction_percent']:.1f}%)"
    )
    
    return unique_documents, removed_documents, stats


def create_dedup_excel(unique_docs: list, removed_docs: list, dedup_stats: dict, 
                       output_path: str = None) -> str:
    """
    Erstelle Excel-Übersicht für Exact-Deduplication.
    
    Formatierung entspricht der Vorlage aus deduplication_overview - Kopie.xlsx:
    - Übersicht: Header mit Stage-Tabelle und Content-Type-Statistik
    - Duplikat-Gruppen: Kompakte Darstellung mit Doc IDs als Liste
    - Entfernte Dokumente: Alle entfernten Docs mit Stichproben-Markierung
    - Stichprobe: Nur entfernte Docs zur manuellen Prüfung
    
    Args:
        unique_docs: Liste der behaltenen Dokumente
        removed_docs: Liste der entfernten Duplikate
        dedup_stats: Statistiken aus deduplicate_documents_exact()
        output_path: Optional: Pfad für Excel-Datei
    
    Returns:
        Pfad zur erstellten Excel-Datei
    """
    import pandas as pd
    from pathlib import Path
    from datetime import datetime
    import random
    
    if output_path is None:
        excel_path = Path("src/advanced_rag/data/deduplication_overview.xlsx")
    else:
        excel_path = Path(output_path)
    
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n   📊 Erstelle Deduplication Excel: {excel_path}")
    
    all_docs = unique_docs + removed_docs
    
    # Berechne Content-Type Statistiken
    html_original = sum(1 for d in all_docs if d.get('content_type') == 'html')
    html_unique = sum(1 for d in unique_docs if d.get('content_type') == 'html')
    html_removed = html_original - html_unique
    pdf_original = sum(1 for d in all_docs if d.get('content_type') == 'pdf')
    pdf_unique = sum(1 for d in unique_docs if d.get('content_type') == 'pdf')
    pdf_removed = pdf_original - pdf_unique
    
    # Baue Hash-Gruppen auf
    hash_to_docs = defaultdict(list)
    for doc in all_docs:
        doc_hash = doc.get('_normalized_hash', 'unknown')
        hash_to_docs[doc_hash].append(doc)
    duplicate_groups = {h: docs for h, docs in hash_to_docs.items() if len(docs) > 1}
    sorted_groups = sorted(duplicate_groups.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Mapping: doc_id -> (group_index, kept_doc)
    doc_to_group = {}
    for group_idx, (hash_val, docs) in enumerate(sorted_groups, 1):
        kept_doc = docs[0]  # Erstes Dokument wird behalten
        for doc in docs:
            doc_to_group[doc.get('doc_id')] = (group_idx, kept_doc)
    
    # ================================================================
    # Sheet 1: Übersicht (mit Header und Formatierung)
    # ================================================================
    overview_rows = [
        ['🔍 Deduplication Pipeline - Übersicht', '', '', '', '', '', ''],
        [f'Erstellt am: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', '', '', '', '', '', ''],
        ['', '', '', '', '', '', ''],
        ['Stage', 'Name', 'Input', 'Output', 'Entfernt', 'Reduktion %', 'Duplikat-Gruppen'],
        [1, 'Exact-Deduplication', dedup_stats['total'], dedup_stats['unique'], 
         dedup_stats['duplicates_removed'], f"{dedup_stats['reduction_percent']:.1f}%", 
         dedup_stats['duplicate_groups']],
        ['GESAMT', 'Alle 1 Stages', dedup_stats['total'], dedup_stats['unique'],
         dedup_stats['duplicates_removed'], f"{dedup_stats['reduction_percent']:.1f}%",
         dedup_stats['duplicate_groups']],
        ['', '', '', '', '', '', ''],
        ['', '', '', '', '', '', ''],
        ['📁 Statistik nach Content-Type', '', '', '', '', '', ''],
        ['Content-Type', 'Original', 'Nach Dedup', 'Entfernt', 'Reduktion %', '', ''],
        ['HTML', html_original, html_unique, html_removed, 
         f"{html_removed/html_original*100:.1f}%" if html_original > 0 else '0%', '', ''],
        ['PDF', pdf_original, pdf_unique, pdf_removed,
         f"{pdf_removed/pdf_original*100:.1f}%" if pdf_original > 0 else '0%', '', ''],
    ]
    df_overview = pd.DataFrame(overview_rows)
    
    # ================================================================
    # Sheet 2: Duplikat-Gruppen (kompakte Darstellung)
    # ================================================================
    groups_rows = [
        ['🔗 Exakte Duplikat-Gruppen (Stage 1)', '', '', '', '', ''],
        [f'Gesamt: {len(duplicate_groups)} Gruppen mit {len(removed_docs)} Duplikaten', '', '', '', '', ''],
        ['', '', '', '', '', ''],
        ['Gruppe', 'Hash (kurz)', 'Anzahl Docs', 'Doc IDs', 'URLs', 'Content-Types'],
    ]
    
    for group_idx, (hash_val, docs) in enumerate(sorted_groups, 1):
        doc_ids = ', '.join(str(d.get('doc_id', '?')) for d in docs)
        urls = '\n'.join(d.get('url', '')[:80] + ('...' if len(d.get('url', '')) > 80 else '') for d in docs[:5])
        if len(docs) > 5:
            urls += f'\n... +{len(docs) - 5} weitere'
        content_types = ', '.join(set(d.get('content_type', '').upper() for d in docs))
        
        groups_rows.append([
            group_idx, 
            hash_val[:16] + '...', 
            len(docs), 
            doc_ids, 
            urls, 
            content_types
        ])
    
    df_groups = pd.DataFrame(groups_rows)
    
    # ================================================================
    # Sheet 3: Entfernte Dokumente (mit Stichproben-Markierung)
    # ================================================================
    # WICHTIG: Die entfernten Dokumente müssen in derselben Reihenfolge wie in
    # deduplication_implementation.py sein: Sortiert nach Duplikat-Gruppen (größte zuerst),
    # innerhalb jeder Gruppe ab dem zweiten Dokument.
    
    # Baue sortierte Liste der entfernten Dokumente (wie in deduplication_implementation.py)
    all_removed_sorted = []
    for group_idx, (hash_val, docs) in enumerate(sorted_groups, 1):
        kept_doc = docs[0]  # Erstes Dokument wird behalten
        for doc in docs[1:]:  # Rest sind Duplikate
            all_removed_sorted.append({
                'doc': doc,
                'group_idx': group_idx,
                'kept_doc': kept_doc
            })
    
    # Stichprobe bestimmen - WICHTIG: Algorithmus muss exakt deduplication_implementation.py entsprechen!
    # 1. Erst 20 aus ALLEN entfernten Dokumenten ziehen (nicht getrennt nach Typ!)
    # 2. Dann zusätzlich 2 PDFs, die noch nicht in der Stichprobe sind
    random.seed(42)
    
    # Index-Listen für PDF-Tracking (basierend auf sortierter Liste!)
    pdf_indices = {i for i, item in enumerate(all_removed_sorted) if item['doc'].get('content_type') == 'pdf'}
    
    # Schritt 1: Ziehe 20 Dokumente aus allen (reproduziert alte Stichprobe)
    base_sample_size = min(20, len(all_removed_sorted))
    base_sample_indices = set(random.sample(range(len(all_removed_sorted)), base_sample_size)) if all_removed_sorted else set()
    
    # Schritt 2: Ziehe zusätzlich 2 PDFs (die noch nicht in der Stichprobe sind)
    pdf_not_in_sample = [i for i in pdf_indices if i not in base_sample_indices]
    additional_pdf_sample = set()
    if pdf_not_in_sample:
        pdf_sample_size = min(2, len(pdf_not_in_sample))
        additional_pdf_sample = set(random.sample(pdf_not_in_sample, pdf_sample_size))
    
    sample_indices = base_sample_indices | additional_pdf_sample
    sample_doc_ids = {all_removed_sorted[i]['doc'].get('doc_id') for i in sample_indices}
    
    removed_rows = [
        ['🗑️ Alle entfernten Dokumente', '', '', '', '', '', '', '', ''],
        [f'Stichprobe: {len([i for i in sample_indices if all_removed_sorted[i]["doc"].get("content_type") == "html"])} HTML + {len([i for i in sample_indices if all_removed_sorted[i]["doc"].get("content_type") == "pdf"])} PDF (Seed: 42)', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', ''],
        ['Stichprobe', 'Stage', 'Gruppe', 'Doc ID', 'Content-Type', 'Entfernte URL', 'Titel', 'Zeichen', 'Ersetzt durch URL'],
    ]
    
    for idx, item in enumerate(all_removed_sorted):
        doc = item['doc']
        doc_id = doc.get('doc_id')
        group_idx = item['group_idx']
        kept_doc = item['kept_doc']
        is_sample = idx in sample_indices
        
        removed_rows.append([
            '✓ PRÜFEN' if is_sample else '',
            'Exact-Deduplication',
            group_idx,
            doc_id,
            doc.get('content_type', '').upper(),
            doc.get('url', ''),
            (doc.get('title', '') or '')[:60],
            len(doc.get('text', '')),
            kept_doc.get('url', '') if kept_doc else ''
        ])
    
    df_removed = pd.DataFrame(removed_rows)
    
    # ================================================================
    # Sheet 4: Stichprobe (nur entfernte Docs zur manuellen Prüfung)
    # ================================================================
    # Sample-Docs aus der sortierten Liste extrahieren
    sample_items = [all_removed_sorted[i] for i in sorted(sample_indices)]
    sample_count_html = len([item for item in sample_items if item['doc'].get('content_type') == 'html'])
    sample_count_pdf = len([item for item in sample_items if item['doc'].get('content_type') == 'pdf'])
    
    sample_rows = [
        ['🔍 Stichprobe zur manuellen Überprüfung', '', '', '', '', ''],
        [f'Seed: 42 | Stichprobe: {sample_count_html} HTML + {sample_count_pdf} PDF = {len(sample_items)} von {len(all_removed_sorted)} Dokumenten', '', '', '', '', ''],
        ['Bitte überprüfen Sie, ob die entfernten Dokumente tatsächlich Duplikate der Ersatz-Dokumente sind.', '', '', '', '', ''],
        ['', '', '', '', '', ''],
        ['#', 'Typ', 'Doc ID', 'Entfernte URL', 'Ersetzt durch URL', 'Korrekt? (J/N)', 'Anmerkung'],
    ]
    
    for i, item in enumerate(sample_items, 1):
        doc = item['doc']
        kept_doc = item['kept_doc']
        
        sample_rows.append([
            i,
            doc.get('content_type', '').upper(),
            doc.get('doc_id', ''),
            doc.get('url', ''),
            kept_doc.get('url', '') if kept_doc else '',
            '',  # Korrekt? (J/N) - leer für manuelle Eingabe
            ''   # Anmerkung - leer für manuelle Eingabe
        ])
    
    df_sample = pd.DataFrame(sample_rows)
    
    # Speichere Excel
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_overview.to_excel(writer, sheet_name='Übersicht', index=False, header=False)
        df_groups.to_excel(writer, sheet_name='Duplikat-Gruppen', index=False, header=False)
        df_removed.to_excel(writer, sheet_name='Entfernte Dokumente', index=False, header=False)
        df_sample.to_excel(writer, sheet_name='Stichprobe', index=False, header=False)
        
        # ================================================================
        # Formatierungen anwenden (wie im Template)
        # ================================================================
        wb = writer.book
        
        # Farben definieren (wie im Template)
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')  # Dunkelblau
        total_fill = PatternFill(start_color='8FAADC', end_color='8FAADC', fill_type='solid')   # Hellblau
        sample_fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')  # Gelb
        header_font = Font(bold=True, color='FFFFFF')  # Weiß
        total_font = Font(bold=True)
        
        # --- Sheet 1: Übersicht ---
        ws_overview = wb['Übersicht']
        # Zeile 1: Titel (Bold)
        ws_overview.cell(row=1, column=1).font = Font(bold=True)
        # Zeile 4: Header (Stage, Name, Input, Output, Entfernt, ...)
        for col in range(1, 8):
            cell = ws_overview.cell(row=4, column=col)
            cell.fill = header_fill
            cell.font = header_font
        # Zeile 6: GESAMT
        for col in range(1, 8):
            cell = ws_overview.cell(row=6, column=col)
            cell.fill = total_fill
            cell.font = total_font
        # Zeile 9: Statistik-Titel (Bold)
        ws_overview.cell(row=9, column=1).font = Font(bold=True)
        # Zeile 10: Content-Type Header
        for col in range(1, 6):
            cell = ws_overview.cell(row=10, column=col)
            cell.fill = header_fill
            cell.font = header_font
        
        # --- Sheet 2: Duplikat-Gruppen ---
        ws_groups = wb['Duplikat-Gruppen']
        # Zeile 4: Header
        for col in range(1, 7):
            cell = ws_groups.cell(row=4, column=col)
            cell.fill = header_fill
            cell.font = header_font
        # Zeile 1: Titel (Bold)
        ws_groups.cell(row=1, column=1).font = Font(bold=True)
        
        # --- Sheet 3: Entfernte Dokumente ---
        ws_removed = wb['Entfernte Dokumente']
        # Zeile 4: Header
        for col in range(1, 10):
            cell = ws_removed.cell(row=4, column=col)
            cell.fill = header_fill
            cell.font = header_font
        # Zeile 1: Titel (Bold)
        ws_removed.cell(row=1, column=1).font = Font(bold=True)
        # Gelbe Markierung für Stichproben-Zeilen
        for row_idx in range(5, ws_removed.max_row + 1):
            if ws_removed.cell(row=row_idx, column=1).value == '✓ PRÜFEN':
                for col in range(1, 10):
                    ws_removed.cell(row=row_idx, column=col).fill = sample_fill
        
        # --- Sheet 4: Stichprobe ---
        ws_sample = wb['Stichprobe']
        # Zeile 5: Header
        for col in range(1, 8):
            cell = ws_sample.cell(row=5, column=col)
            cell.fill = header_fill
            cell.font = header_font
        # Zeile 1: Titel (Bold)
        ws_sample.cell(row=1, column=1).font = Font(bold=True)
        # Hellgrüne Eingabefelder für Spalten 6-7 (Korrekt? und Anmerkung)
        input_fill = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
        for row_idx in range(6, ws_sample.max_row + 1):
            if ws_sample.cell(row=row_idx, column=1).value:  # Nur Datenzeilen
                ws_sample.cell(row=row_idx, column=6).fill = input_fill
                ws_sample.cell(row=row_idx, column=7).fill = input_fill
    
    print(f"   ✅ Excel erstellt: {len(duplicate_groups)} Gruppen, {len(all_removed_sorted)} entfernt, {len(sample_items)} in Stichprobe")
    
    return str(excel_path)


@dataclass
class ContentFingerprint:
    """Fingerprint eines Dokuments für Deduplication"""
    url: str
    content_hash: str
    shingles_hash: str
    word_count: int


class ContentDeduplicator:
    """
    Dedupliziert Inhalte basierend auf Similarity-Hashing.
    
    Verwendet Shingling und MinHash für effiziente near-duplicate Erkennung.
    """
    
    def __init__(self, similarity_threshold: float = 0.85, shingle_size: int = 3):
        """
        Initialisiere den Deduplicator.
        
        Args:
            similarity_threshold: Schwellwert für Ähnlichkeit (0.0-1.0)
            shingle_size: Größe der Shingles für Vergleich
        """
        self.similarity_threshold = similarity_threshold
        self.shingle_size = shingle_size
        self.seen_fingerprints: Set[str] = set()
        self.url_to_fingerprint: dict = {}
        
        # Quick-Win Optimierungen
        self.shingle_cache: dict = {}  # Cache für Shingles
        self.chunks_by_size: dict = defaultdict(list)  # Size-Bucketing
        
    def create_shingles(self, text: str) -> Set[str]:
        """
        Erstelle Shingles (n-grams) aus Text mit Caching.
        
        Args:
            text: Eingabetext
            
        Returns:
            Set von Shingles
        """
        # Quick-Win 1: Shingle-Cache
        text_hash = hash(text)
        if text_hash in self.shingle_cache:
            return self.shingle_cache[text_hash]
        
        # Normalisiere Text
        text = text.lower().strip()
        words = text.split()
        
        # Erstelle Wort-Shingles
        shingles = set()
        for i in range(len(words) - self.shingle_size + 1):
            shingle = " ".join(words[i:i + self.shingle_size])
            shingles.add(shingle)
        
        # Cache speichern
        self.shingle_cache[text_hash] = shingles
        return shingles
    
    def compute_content_hash(self, text: str, use_full_normalization: bool = True) -> str:
        """
        Berechne eindeutigen Hash für Inhalt.
        
        Args:
            text: Eingabetext
            use_full_normalization: Wenn True, nutze normalize_text() für robuste Normalisierung.
                                    Wenn False, nur lower().strip() (Legacy-Verhalten).
            
        Returns:
            SHA256-Hash als Hex-String
        """
        if use_full_normalization:
            normalized = normalize_text(text)
        else:
            normalized = text.lower().strip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def compute_shingles_hash(self, shingles: Set[str]) -> str:
        """
        Berechne Hash für Shingles-Set.
        
        Args:
            shingles: Set von Shingles
            
        Returns:
            Hash-Repräsentation
        """
        # Sortiere für konsistenten Hash
        sorted_shingles = sorted(shingles)
        combined = "".join(sorted_shingles)
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """
        Berechne Jaccard-Ähnlichkeit zwischen zwei Sets mit Early Exit.
        
        Args:
            set1: Erstes Set
            set2: Zweites Set
            
        Returns:
            Ähnlichkeit zwischen 0.0 und 1.0
        """
        if not set1 and not set2:
            return 1.0
        
        # Quick-Win 2: Early Exit - prüfe maximale mögliche Similarity
        min_size = min(len(set1), len(set2))
        max_size = max(len(set1), len(set2))
        
        if max_size > 0:
            max_possible_similarity = min_size / max_size
            if max_possible_similarity < self.similarity_threshold:
                return 0.0  # Kann nie Threshold erreichen
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def is_duplicate(self, text: str, url: str) -> Tuple[bool, str]:
        """
        Prüfe ob Text ein Duplikat ist mit Size-Bucketing.
        
        Args:
            text: Zu prüfender Text
            url: URL des Dokuments
            
        Returns:
            Tuple von (ist_duplikat, grund)
        """
        # Exakte Duplikate
        content_hash = self.compute_content_hash(text)
        if content_hash in self.seen_fingerprints:
            return True, "exact_duplicate"
        
        # Quick-Win 3: Size-Bucketing - nur ähnlich große Texte vergleichen
        text_size = len(text)
        size_bucket = text_size // 500  # Buckets von 500 Zeichen
        
        # Kandidaten: Aktueller Bucket ± 1
        candidates = []
        for bucket in [size_bucket - 1, size_bucket, size_bucket + 1]:
            candidates.extend(self.chunks_by_size.get(bucket, []))
        
        # Near-duplicates - nur gegen Kandidaten
        shingles = self.create_shingles(text)
        
        for candidate_url in candidates:
            if candidate_url not in self.url_to_fingerprint:
                continue
                
            candidate_text = self.url_to_fingerprint[candidate_url].get('text', '')
            seen_shingles = self.create_shingles(candidate_text)
            
            similarity = self.jaccard_similarity(shingles, seen_shingles)
            
            if similarity >= self.similarity_threshold:
                logger.info(
                    f"Near-duplicate gefunden: {url} ähnlich zu {candidate_url} "
                    f"(Similarity: {similarity:.2f})"
                )
                return True, f"near_duplicate_{similarity:.2f}"
        
        # Kein Duplikat - speichere Fingerprint UND Size-Bucket
        self.seen_fingerprints.add(content_hash)
        self.url_to_fingerprint[url] = {
            'content_hash': content_hash,
            'shingles_hash': self.compute_shingles_hash(shingles),
            'text': text[:5000],
            'word_count': len(text.split())
        }
        self.chunks_by_size[size_bucket].append(url)
        
        return False, "unique"
    
    def deduplicate_batch(self, documents: List[dict]) -> Tuple[List[dict], List[dict]]:
        """
        Dedupliziere eine Batch von Dokumenten.
        
        Args:
            documents: Liste von Dokumenten mit 'url' und 'content' Keys
            
        Returns:
            Tuple von (unique_documents, duplicate_documents)
        """
        unique = []
        duplicates = []
        
        for doc in documents:
            url = doc.get('url', '')
            content = doc.get('content', '')
            
            is_dup, reason = self.is_duplicate(content, url)
            
            if is_dup:
                doc['duplicate_reason'] = reason
                duplicates.append(doc)
            else:
                unique.append(doc)
        
        logger.info(
            f"Deduplication: {len(unique)} unique, {len(duplicates)} duplicates "
            f"von {len(documents)} gesamt"
        )
        
        return unique, duplicates
    
    def get_statistics(self) -> dict:
        """
        Erhalte Statistiken über gesehene Dokumente.
        
        Returns:
            Dictionary mit Statistiken
        """
        return {
            'total_seen': len(self.seen_fingerprints),
            'unique_urls': len(self.url_to_fingerprint),
            'similarity_threshold': self.similarity_threshold,
            'shingle_size': self.shingle_size
        }


# ============================================================================
# ENTRY POINT FÜR DEMO
# ============================================================================

if __name__ == "__main__":
    demo_normalization()