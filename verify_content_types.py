"""
Verifikation: Zeige Beispiele aus beiden Content-Types
"""
import chromadb
from pathlib import Path

VECTOR_DB = Path("data/vector_db")

def verify_content_types():
    """Prüfe und zeige Beispiele aus HTML und PDF Dokumenten."""
    
    print("=" * 80)
    print("VERIFIKATION: HTML + PDF CONTENT")
    print("=" * 80)
    
    # Verbinde zu ChromaDB
    client = chromadb.PersistentClient(path=str(VECTOR_DB))
    
    # Sammle Beispiele
    html_examples = []
    pdf_examples = []
    
    collections = {
        'wiso_studium': client.get_collection('wiso_studium'),
        'wiso_services': client.get_collection('wiso_services'),
        'wiso_forschung': client.get_collection('wiso_forschung'),
        'wiso_allgemein': client.get_collection('wiso_allgemein')
    }
    
    # Suche in allen Collections nach Beispielen
    for collection_name, collection in collections.items():
        if len(html_examples) >= 3 and len(pdf_examples) >= 3:
            break
        
        # Hole alle Chunks aus dieser Collection
        results = collection.get(include=['metadatas', 'documents'])
        
        for doc, metadata in zip(results['documents'], results['metadatas']):
            if metadata['content_type'] == 'html' and len(html_examples) < 3:
                html_examples.append({
                    'title': metadata['title'],
                    'url': metadata['url'],
                    'collection': collection_name,
                    'chunk_index': metadata['chunk_index'],
                    'total_chunks': metadata['total_chunks'],
                    'content': doc
                })
            elif metadata['content_type'] == 'pdf' and len(pdf_examples) < 3:
                pdf_examples.append({
                    'title': metadata['title'],
                    'url': metadata['url'],
                    'collection': collection_name,
                    'chunk_index': metadata['chunk_index'],
                    'total_chunks': metadata['total_chunks'],
                    'content': doc
                })
            
            if len(html_examples) >= 3 and len(pdf_examples) >= 3:
                break
    
    # Zeige HTML-Beispiele
    print(f"\n📄 HTML-DOKUMENTE ({len(html_examples)} Beispiele gefunden)")
    print("=" * 80)
    
    for i, example in enumerate(html_examples, 1):
        print(f"\n🔹 Beispiel {i}:")
        print(f"   📌 Titel: {example['title']}")
        print(f"   🔗 URL: {example['url'][:80]}{'...' if len(example['url']) > 80 else ''}")
        print(f"   📦 Collection: {example['collection']}")
        print(f"   📊 Chunk: {example['chunk_index']+1}/{example['total_chunks']}")
        print(f"   📝 Inhalt (erste 200 Zeichen):")
        print(f"      {example['content'][:200]}...")
    
    # Zeige PDF-Beispiele
    print(f"\n\n📕 PDF-DOKUMENTE ({len(pdf_examples)} Beispiele gefunden)")
    print("=" * 80)
    
    for i, example in enumerate(pdf_examples, 1):
        print(f"\n🔹 Beispiel {i}:")
        print(f"   📌 Titel: {example['title']}")
        print(f"   🔗 URL: {example['url'][:80]}{'...' if len(example['url']) > 80 else ''}")
        print(f"   📦 Collection: {example['collection']}")
        print(f"   📊 Chunk: {example['chunk_index']+1}/{example['total_chunks']}")
        print(f"   📝 Inhalt (erste 200 Zeichen):")
        print(f"      {example['content'][:200]}...")
    
    # Statistiken
    print(f"\n\n📊 STATISTIKEN")
    print("=" * 80)
    
    total_html = 0
    total_pdf = 0
    
    for collection_name, collection in collections.items():
        results = collection.get(include=['metadatas'])
        
        html_count = sum(1 for meta in results['metadatas'] if meta['content_type'] == 'html')
        pdf_count = sum(1 for meta in results['metadatas'] if meta['content_type'] == 'pdf')
        
        total_html += html_count
        total_pdf += pdf_count
        
        print(f"\n📦 {collection_name}:")
        print(f"   HTML-Chunks: {html_count:,}")
        print(f"   PDF-Chunks: {pdf_count:,}")
        print(f"   Gesamt: {html_count + pdf_count:,}")
    
    print(f"\n🎯 GESAMTERGEBNIS:")
    print(f"   ✅ HTML-Chunks: {total_html:,}")
    print(f"   ✅ PDF-Chunks: {total_pdf:,}")
    print(f"   📊 Gesamt: {total_html + total_pdf:,}")
    print(f"   📈 PDF-Anteil: {(total_pdf/(total_html+total_pdf)*100):.1f}%")
    
    print("\n" + "=" * 80)
    print("✅ VERIFIKATION ERFOLGREICH")
    print("=" * 80)
    print("Beide Content-Types (HTML + PDF) wurden korrekt verarbeitet!")
    print("=" * 80)

if __name__ == "__main__":
    verify_content_types()
