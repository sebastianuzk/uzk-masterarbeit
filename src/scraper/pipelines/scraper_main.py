"""
Main CLI Interface for Web Scraper RAG System
=============================================

This script provides a command-line interface for running the complete
web scraping and vector storage pipeline for RAG data preparation.

Usage:
    python scraper_main.py scrape --urls url1 url2 --output data.json
    python scraper_main.py vectorize --input data.json --backend chromadb
    python scraper_main.py analyze --collection my_collection
    python scraper_main.py pipeline --urls url1 url2 --collection my_collection
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional
import logging
from datetime import datetime

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from src.scraper.core.batch_scraper import BatchScraper, ScrapingConfig, ScrapedContent
from src.scraper.core.vector_store import VectorStore, VectorStoreConfig
from src.scraper.data_analysis.data_structure_analyzer import DataStructureAnalyzer


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def progress_callback(url: str, success: bool, error: Optional[str]) -> None:
    """Progress callback for scraping operations."""
    status = "✓" if success else "✗"
    print(f"{status} {url}")
    if error:
        print(f"  Error: {error}")


async def scrape_command(args) -> None:
    """Execute the scrape command."""
    print(f"Starting scraping of {len(args.urls)} URLs...")
    
    config = ScrapingConfig(
        max_concurrent_requests=args.concurrent,
        request_delay=args.delay,
        timeout=args.timeout,
        retry_attempts=args.retries
    )
    
    scraper = BatchScraper(config)
    results = await scraper.scrape_urls(args.urls, progress_callback)
    
    # Save results
    scraper.save_results(args.output, args.format)
    
    # Print statistics
    stats = scraper.get_statistics()
    print(f"\nScraping completed:")
    print(f"  Successful: {stats['successful']}/{stats['total_urls']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Total words: {stats['total_words']:,}")
    print(f"  Unique domains: {stats['unique_domains']}")
    print(f"  Results saved to: {args.output}")


def vectorize_command(args) -> None:
    """Execute the vectorize command."""
    print(f"Loading scraped data from {args.input}...")
    
    # Load scraped content
    with open(args.input, 'r', encoding='utf-8') as f:
        if args.input.endswith('.jsonl'):
            scraped_data = []
            for line in f:
                scraped_data.append(json.loads(line))
        else:
            scraped_data = json.load(f)
    
    # Convert to ScrapedContent objects
    scraped_content = [ScrapedContent(**data) for data in scraped_data]
    successful_content = [content for content in scraped_content if content.success]
    
    print(f"Loaded {len(successful_content)} successful documents")
    
    # Configure vector store
    config = VectorStoreConfig(
        backend=args.backend,
        collection_name=args.collection,
        persist_directory=args.persist_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        embedding_model=args.embedding_model,
        embedding_provider=args.embedding_provider
    )
    
    # Create vector store and add content
    print("Initializing vector store...")
    vector_store = VectorStore(config)
    
    print("Adding content to vector store...")
    vector_store.add_scraped_content(successful_content)
    
    # Print statistics
    stats = vector_store.get_statistics()
    print(f"\nVectorization completed:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Backend: {stats['backend']}")
    print(f"  Embedding model: {stats['embedding_model']}")
    print(f"  Collection: {stats['collection_name']}")


def analyze_command(args) -> None:
    """Execute the analyze command."""
    print(f"Analyzing data structure for collection '{args.collection}'...")
    
    # Configure vector store
    config = VectorStoreConfig(
        backend=args.backend,
        collection_name=args.collection,
        persist_directory=args.persist_dir
    )
    
    vector_store = VectorStore(config)
    analyzer = DataStructureAnalyzer(vector_store)
    
    # Run analysis
    report = analyzer.analyze_structure(sample_size=args.sample_size)
    
    # Print summary
    print(f"\nData Structure Analysis:")
    print(f"  Total documents: {report.total_documents:,}")
    print(f"  Total fields: {len(report.fields)}")
    print(f"  Average completeness: {report.data_quality_metrics['avg_completeness']:.1%}")
    print(f"  Average text length: {report.data_quality_metrics['avg_text_length']:.0f} chars")
    print(f"  Unique sources: {report.data_quality_metrics['unique_sources']}")
    
    # Print field summary
    print(f"\nTop 10 Fields by Presence:")
    for field in report.fields[:10]:
        print(f"  {field.field_name}: {field.presence_rate:.1%} ({field.data_type})")
    
    # Print suggestions
    if report.optimization_suggestions:
        print(f"\nOptimization Suggestions:")
        for i, suggestion in enumerate(report.optimization_suggestions, 1):
            print(f"  {i}. {suggestion}")
    
    # Export reports if requested
    if args.export:
        for format_type in args.export:
            output_file = f"src/scraper/output/data_structure_report.{format_type}"
            analyzer.export_report(report, output_file, format_type)
            print(f"  Report exported to: {output_file}")


async def pipeline_command(args) -> None:
    """Execute the complete pipeline command."""
    print("Starting complete scraping and vectorization pipeline...")
    
    # Step 1: Scraping
    print("\n=== STEP 1: SCRAPING ===")
    scraping_config = ScrapingConfig(
        max_concurrent_requests=args.concurrent,
        request_delay=args.delay,
        timeout=args.timeout,
        retry_attempts=args.retries
    )
    
    scraper = BatchScraper(scraping_config)
    scraped_content = await scraper.scrape_urls(args.urls, progress_callback)
    
    scraping_stats = scraper.get_statistics()
    print(f"Scraping completed: {scraping_stats['successful']}/{scraping_stats['total_urls']} successful")
    
    # Step 2: Vectorization
    print("\n=== STEP 2: VECTORIZATION ===")
    vector_config = VectorStoreConfig(
        backend=args.backend,
        collection_name=args.collection,
        persist_directory=args.persist_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        embedding_model=args.embedding_model,
        embedding_provider=args.embedding_provider
    )
    
    vector_store = VectorStore(vector_config)
    successful_content = [content for content in scraped_content if content.success]
    
    if successful_content:
        vector_store.add_scraped_content(successful_content)
        vector_stats = vector_store.get_statistics()
        print(f"Vectorization completed: {vector_stats['total_documents']} documents stored")
    else:
        print("No successful content to vectorize")
        return
    
    # Step 3: Analysis
    print("\n=== STEP 3: ANALYSIS ===")
    analyzer = DataStructureAnalyzer(vector_store)
    report = analyzer.analyze_structure()
    
    print(f"Analysis completed:")
    print(f"  Total documents: {report.total_documents:,}")
    print(f"  Average completeness: {report.data_quality_metrics['avg_completeness']:.1%}")
    
    # Export analysis report
    analyzer.export_report(report, "src/scraper/data_analysis/pipeline_analysis_report.json", "json")
    analyzer.export_report(report, "src/scraper/data_analysis/pipeline_analysis_report.md", "markdown")
    print("Analysis reports exported")
    
    # Save scraped data if requested
    #if args.save_scraped:
    scraper.save_results("src/scraper/data_analysis/scraped_data.json", "json")
    print("Scraped data saved to src/scraper/data_analysis/scraped_data.json")
    
    print("\n=== PIPELINE COMPLETED SUCCESSFULLY ===")


def chunks_command(args) -> None:
    """Execute the chunks command - lightweight version without embeddings."""
    print(f"Retrieving chunks from collection '{args.collection}'...")
    
    try:
        # Direct access to ChromaDB without vector operations
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Import ChromaDB directly if available in environment
        try:
            import chromadb
            client = chromadb.PersistentClient(path=args.persist_dir)
            collection = client.get_collection(name=args.collection)
            
            # Get all documents
            result = collection.get()
            
            if not result['ids']:
                print("No chunks found in the vector store.")
                return
            
            # Combine data
            chunks_data = []
            for i in range(len(result['ids'])):
                chunk_data = {
                    'id': result['ids'][i],
                    'text': result['documents'][i],
                    'metadata': result['metadatas'][i] if result['metadatas'] else {}
                }
                chunks_data.append(chunk_data)
            
            # Sort by source URL and chunk index for logical order
            chunks_data.sort(key=lambda x: (
                x['metadata'].get('source_url', ''),
                x['metadata'].get('chunk_index', 0)
            ))
            
            # Apply limit if specified
            if args.limit:
                chunks_data = chunks_data[:args.limit]
            
            print(f"\nFound {len(chunks_data)} chunks:\n")
            
            # Display chunks
            for i, chunk in enumerate(chunks_data, 1):
                metadata = chunk['metadata']
                print(f"=== CHUNK {i} ===")
                print(f"ID: {chunk['id']}")
                print(f"Source: {metadata.get('source_url', 'Unknown')}")
                print(f"Chunk: {metadata.get('chunk_index', 0) + 1}/{metadata.get('total_chunks', '?')}")
                print(f"Length: {len(chunk['text'])} characters")
                print(f"Title: {metadata.get('title', 'N/A')}")
                print(f"Content Preview:")
                print("-" * 50)
                # Show first 300 characters for preview
                content = chunk['text']
                if len(content) > 300:
                    print(content[:300] + "...")
                else:
                    print(content)
                print("-" * 50)
                print("\n")
            
            # Export if requested
            if args.export:
                export_chunks_direct(chunks_data, args.export, args.collection)
                
        except ImportError:
            print("ChromaDB not available. Please install with: pip install chromadb")
        except Exception as e:
            print(f"Error accessing ChromaDB: {e}")
            
    except Exception as e:
        print(f"Error retrieving chunks: {e}")
        print("Make sure the collection exists and ChromaDB is available.")


def export_chunks_direct(chunks_data, format_type, collection_name):
    """Export chunks to file using direct data."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format_type == 'json':
        filename = f"src/scraper/data_analysis/chunks_{collection_name}_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
    
    elif format_type == 'txt':
        filename = f"src/scraper/output/chunks_{collection_name}_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for i, chunk in enumerate(chunks_data, 1):
                metadata = chunk['metadata']
                f.write(f"=== CHUNK {i} ===\n")
                f.write(f"ID: {chunk['id']}\n")
                f.write(f"Source: {metadata.get('source_url', 'Unknown')}\n")
                f.write(f"Chunk: {metadata.get('chunk_index', 0) + 1}/{metadata.get('total_chunks', '?')}\n")
                f.write(f"Length: {len(chunk['text'])} characters\n")
                f.write(f"Title: {metadata.get('title', 'N/A')}\n")
                f.write(f"Content:\n")
                f.write("-" * 50 + "\n")
                f.write(chunk['text'])
                f.write("\n" + "-" * 50 + "\n")
                f.write(f"Metadata: {metadata}\n")
                f.write("\n\n")
    
    print(f"Chunks exported to: {filename}")


def export_chunks(chunks, format_type, collection_name):
    """Export chunks to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format_type == 'json':
        filename = f"src/scraper/data_analysis/chunks_{collection_name}_{timestamp}.json"
        chunks_data = []
        for doc, score in chunks:
            chunk_data = {
                'id': doc.id,
                'source_url': doc.source_url,
                'chunk_index': doc.chunk_index,
                'total_chunks': doc.total_chunks,
                'text': doc.text,
                'metadata': doc.metadata,
                'search_score': score
            }
            chunks_data.append(chunk_data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
    
    elif format_type == 'txt':
        filename = f"src/scraper/output/chunks_{collection_name}_{timestamp}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for i, (doc, score) in enumerate(chunks, 1):
                f.write(f"=== CHUNK {i} ===\n")
                f.write(f"ID: {doc.id}\n")
                f.write(f"Source: {doc.source_url}\n")
                f.write(f"Chunk: {doc.chunk_index + 1}/{doc.total_chunks}\n")
                f.write(f"Length: {len(doc.text)} characters\n")
                f.write(f"Content:\n")
                f.write("-" * 50 + "\n")
                f.write(doc.text)
                f.write("\n" + "-" * 50 + "\n")
                f.write(f"Metadata: {doc.metadata}\n")
                f.write("\n\n")
    
    print(f"Chunks exported to: {filename}")


def search_command(args) -> None:
    """Execute the search command."""
    # Configure vector store
    config = VectorStoreConfig(
        backend=args.backend,
        collection_name=args.collection,
        persist_directory=args.persist_dir
    )
    
    vector_store = VectorStore(config)
    
    # Perform search
    print(f"Searching for: '{args.query}'")
    results = vector_store.search(args.query, k=args.results)
    
    if not results:
        print("No results found.")
        return
    
    print(f"\nFound {len(results)} results:")
    for i, (doc, score) in enumerate(results, 1):
        print(f"\n{i}. Score: {score:.3f}")
        print(f"   Source: {doc.source_url}")
        print(f"   Text: {doc.text[:200]}...")
        if doc.metadata.get('title'):
            print(f"   Title: {doc.metadata['title']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Web Scraper RAG System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape URLs and save to file
  python scraper_main.py scrape --urls https://example.com --output data.json
  
  # Vectorize scraped data
  python scraper_main.py vectorize --input data.json --collection my_docs
  
  # Analyze data structure
  python scraper_main.py analyze --collection my_docs --export json md
  
  # Run complete pipeline
  python scraper_main.py pipeline --urls https://example.com --collection my_docs
  
  # Search the vector store
  python scraper_main.py search --query "machine learning" --collection my_docs
        """
    )
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape URLs')
    scrape_parser.add_argument('--urls', nargs='+', required=True,
                              help='URLs to scrape')
    scrape_parser.add_argument('--output', '-o', default='src/scraper/output/scraped_data.json',
                              help='Output file path')
    scrape_parser.add_argument('--format', choices=['json', 'jsonl'], default='json',
                              help='Output format')
    scrape_parser.add_argument('--concurrent', '-c', type=int, default=10,
                              help='Max concurrent requests')
    scrape_parser.add_argument('--delay', '-d', type=float, default=1.0,
                              help='Delay between requests')
    scrape_parser.add_argument('--timeout', type=int, default=30,
                              help='Request timeout in seconds')
    scrape_parser.add_argument('--retries', type=int, default=3,
                              help='Number of retry attempts')
    
    # Vectorize command
    vectorize_parser = subparsers.add_parser('vectorize', help='Vectorize scraped data')
    vectorize_parser.add_argument('--input', '-i', required=True,
                                 help='Input file with scraped data')
    vectorize_parser.add_argument('--backend', choices=['chromadb', 'faiss'], default='chromadb',
                                 help='Vector database backend')
    vectorize_parser.add_argument('--collection', default='scraped_content',
                                 help='Collection name')
    vectorize_parser.add_argument('--persist-dir', default='src/scraper/vector_db',
                                 help='Persistence directory')
    vectorize_parser.add_argument('--chunk-size', type=int, default=1000,
                                 help='Text chunk size')
    vectorize_parser.add_argument('--chunk-overlap', type=int, default=200,
                                 help='Text chunk overlap')
    vectorize_parser.add_argument('--embedding-model', default='all-MiniLM-L6-v2',
                                 help='Embedding model name')
    vectorize_parser.add_argument('--embedding-provider', choices=['sentence_transformers'],
                                 default='sentence_transformers', help='Embedding provider (open source only)')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze data structure')
    analyze_parser.add_argument('--collection', default='scraped_content',
                               help='Collection name')
    analyze_parser.add_argument('--backend', choices=['chromadb', 'faiss'], default='chromadb',
                               help='Vector database backend')
    analyze_parser.add_argument('--persist-dir', default='src/scraper/vector_db',
                               help='Persistence directory')
    analyze_parser.add_argument('--sample-size', type=int,
                               help='Sample size for analysis')
    analyze_parser.add_argument('--export', nargs='+', choices=['json', 'markdown', 'html'],
                               help='Export formats')
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete pipeline')
    pipeline_parser.add_argument('--urls', nargs='+', required=True,
                                help='URLs to scrape')
    pipeline_parser.add_argument('--collection', default='scraped_content',
                                help='Collection name')
    pipeline_parser.add_argument('--backend', choices=['chromadb', 'faiss'], default='chromadb',
                                help='Vector database backend')
    pipeline_parser.add_argument('--persist-dir', default='src/scraper/vector_db',
                                help='Persistence directory')
    pipeline_parser.add_argument('--concurrent', '-c', type=int, default=10,
                                help='Max concurrent requests')
    pipeline_parser.add_argument('--delay', '-d', type=float, default=1.0,
                                help='Delay between requests')
    pipeline_parser.add_argument('--timeout', type=int, default=30,
                                help='Request timeout in seconds')
    pipeline_parser.add_argument('--retries', type=int, default=3,
                                help='Number of retry attempts')
    pipeline_parser.add_argument('--chunk-size', type=int, default=1000,
                                help='Text chunk size')
    pipeline_parser.add_argument('--chunk-overlap', type=int, default=200,
                                help='Text chunk overlap')
    pipeline_parser.add_argument('--embedding-model', default='all-MiniLM-L6-v2',
                                help='Embedding model name')
    pipeline_parser.add_argument('--embedding-provider', choices=['sentence_transformers'],
                                default='sentence_transformers', help='Embedding provider (open source only)')
    pipeline_parser.add_argument('--save-scraped', action='store_true',
                                help='Save scraped data to file')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search vector store')
    search_parser.add_argument('--query', required=True,
                              help='Search query')
    search_parser.add_argument('--collection', default='scraped_content',
                              help='Collection name')
    search_parser.add_argument('--backend', choices=['chromadb', 'faiss'], default='chromadb',
                              help='Vector database backend')
    search_parser.add_argument('--persist-dir', default='src/scraper/vector_db',
                              help='Persistence directory')
    search_parser.add_argument('--results', '-k', type=int, default=5,
                              help='Number of results to return')
    
    # Chunks command - NEW!
    chunks_parser = subparsers.add_parser('chunks', help='Show all chunks in vector store')
    chunks_parser.add_argument('--collection', default='scraped_content',
                              help='Collection name')
    chunks_parser.add_argument('--backend', choices=['chromadb', 'faiss'], default='chromadb',
                              help='Vector database backend')
    chunks_parser.add_argument('--persist-dir', default='src/scraper/vector_db',
                              help='Persistence directory')
    chunks_parser.add_argument('--limit', type=int, default=None,
                              help='Limit number of chunks to show')
    chunks_parser.add_argument('--export', choices=['json', 'txt'], default=None,
                              help='Export chunks to file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)
    
    # Execute command
    try:
        if args.command == 'scrape':
            asyncio.run(scrape_command(args))
        elif args.command == 'vectorize':
            vectorize_command(args)
        elif args.command == 'analyze':
            analyze_command(args)
        elif args.command == 'pipeline':
            asyncio.run(pipeline_command(args))
        elif args.command == 'search':
            search_command(args)
        elif args.command == 'chunks':
            chunks_command(args)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()