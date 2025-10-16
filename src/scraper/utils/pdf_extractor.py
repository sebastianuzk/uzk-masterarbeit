"""
PDF Content Extractor
====================

This module handles PDF download and text extraction for the scraper pipeline.
"""

import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import hashlib
from datetime import datetime

try:
    import PyPDF2
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PDF libraries not installed. PDF extraction will be disabled.")

logger = logging.getLogger(__name__)


@dataclass
class PDFContent:
    """Extracted PDF content and metadata."""
    url: str
    title: str
    text: str
    num_pages: int
    file_size: int
    metadata: Dict[str, Any]
    extraction_method: str
    success: bool
    error: Optional[str] = None


class PDFExtractor:
    """Handles PDF download and text extraction."""
    
    def __init__(self, download_dir: str = "data/pdfs"):
        """
        Initialize PDF extractor.
        
        Args:
            download_dir: Directory to store downloaded PDFs
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_pdf_filename(self, url: str) -> str:
        """Generate unique filename for PDF based on URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        original_name = url.split('/')[-1].replace('.pdf', '')
        return f"{original_name}_{url_hash}.pdf"
    
    async def download_pdf(self, session: aiohttp.ClientSession, url: str) -> Optional[Path]:
        """
        Download PDF from URL.
        
        Args:
            session: aiohttp session
            url: PDF URL
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status != 200:
                    logger.warning(f"Failed to download PDF {url}: Status {response.status}")
                    return None
                
                content = await response.read()
                
                # Save PDF
                filename = self._get_pdf_filename(url)
                filepath = self.download_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                logger.info(f"Downloaded PDF: {url} -> {filename}")
                return filepath
                
        except Exception as e:
            logger.error(f"Error downloading PDF {url}: {e}")
            return None
    
    def extract_text_pypdf2(self, pdf_path: Path) -> tuple[str, Dict[str, Any]]:
        """
        Extract text using PyPDF2.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, metadata)
        """
        text_parts = []
        metadata = {}
        
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Extract metadata
                if pdf_reader.metadata:
                    metadata = {
                        'title': pdf_reader.metadata.get('/Title', ''),
                        'author': pdf_reader.metadata.get('/Author', ''),
                        'subject': pdf_reader.metadata.get('/Subject', ''),
                        'creator': pdf_reader.metadata.get('/Creator', ''),
                        'producer': pdf_reader.metadata.get('/Producer', ''),
                        'creation_date': pdf_reader.metadata.get('/CreationDate', ''),
                    }
                
                metadata['num_pages'] = len(pdf_reader.pages)
                
                # Extract text from all pages
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num}: {e}")
                        continue
                
        except Exception as e:
            logger.error(f"Error reading PDF with PyPDF2: {e}")
            return "", metadata
        
        return "\n\n".join(text_parts), metadata
    
    def extract_text_pdfplumber(self, pdf_path: Path) -> tuple[str, Dict[str, Any]]:
        """
        Extract text using pdfplumber (better for complex layouts).
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (extracted_text, metadata)
        """
        text_parts = []
        metadata = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                metadata['num_pages'] = len(pdf.pages)
                metadata['pdf_metadata'] = pdf.metadata if hasattr(pdf, 'metadata') else {}
                
                # Extract text from all pages
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                        
                        # Also try to extract tables
                        tables = page.extract_tables()
                        if tables:
                            for table_idx, table in enumerate(tables, 1):
                                table_text = "\n".join(["\t".join(str(cell) for cell in row) for row in table])
                                text_parts.append(f"\n[Table {table_idx}]\n{table_text}")
                                
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading PDF with pdfplumber: {e}")
            return "", metadata
        
        return "\n\n".join(text_parts), metadata
    
    def extract_metadata_from_url(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from URL path (study program, type, etc.).
        
        Args:
            url: PDF URL
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'url': url,
            'filename': url.split('/')[-1],
        }
        
        url_lower = url.lower()
        
        # Detect study program
        programs = {
            'bwl': 'Betriebswirtschaftslehre',
            'vwl': 'Volkswirtschaftslehre',
            'winfo': 'Wirtschaftsinformatik',
            'sowi': 'Sozialwissenschaften',
            'gesundheitsoekonomie': 'Gesundheitsökonomie',
            'wirtschaftspaedagogik': 'Wirtschaftspädagogik',
        }
        
        for key, program in programs.items():
            if key in url_lower:
                metadata['study_program'] = program
                break
        
        # Detect document type
        if 'pruefungsordnung' in url_lower or 'po-' in url_lower or 'po_' in url_lower:
            metadata['document_type'] = 'Prüfungsordnung'
        elif 'modulhandbuch' in url_lower:
            metadata['document_type'] = 'Modulhandbuch'
        elif 'studienordnung' in url_lower:
            metadata['document_type'] = 'Studienordnung'
        elif 'verlaufsplan' in url_lower:
            metadata['document_type'] = 'Verlaufsplan'
        
        # Detect degree
        if 'bachelor' in url_lower:
            metadata['degree'] = 'Bachelor'
        elif 'master' in url_lower:
            metadata['degree'] = 'Master'
        
        return metadata
    
    async def extract_from_url(self, session: aiohttp.ClientSession, url: str) -> PDFContent:
        """
        Download and extract content from PDF URL.
        
        Args:
            session: aiohttp session
            url: PDF URL
            
        Returns:
            PDFContent object with extracted content
        """
        if not PDF_SUPPORT:
            return PDFContent(
                url=url,
                title=url.split('/')[-1],
                text="",
                num_pages=0,
                file_size=0,
                metadata={},
                extraction_method="none",
                success=False,
                error="PDF libraries not installed"
            )
        
        # Download PDF
        pdf_path = await self.download_pdf(session, url)
        if not pdf_path:
            return PDFContent(
                url=url,
                title=url.split('/')[-1],
                text="",
                num_pages=0,
                file_size=0,
                metadata={},
                extraction_method="none",
                success=False,
                error="Download failed"
            )
        
        # Extract URL metadata
        url_metadata = self.extract_metadata_from_url(url)
        
        # Try pdfplumber first (better for complex PDFs)
        text, pdf_metadata = self.extract_text_pdfplumber(pdf_path)
        extraction_method = "pdfplumber"
        
        # Fallback to PyPDF2 if pdfplumber failed
        if not text or len(text) < 100:
            text, pdf_metadata = self.extract_text_pypdf2(pdf_path)
            extraction_method = "pypdf2"
        
        # Combine metadata
        combined_metadata = {**url_metadata, **pdf_metadata}
        
        # Determine title
        title = (
            combined_metadata.get('title') or
            combined_metadata.get('filename', '').replace('.pdf', '') or
            url.split('/')[-1]
        )
        
        file_size = pdf_path.stat().st_size
        num_pages = combined_metadata.get('num_pages', 0)
        
        success = len(text) > 0
        error = None if success else "No text extracted"
        
        logger.info(
            f"Extracted PDF: {title} | Pages: {num_pages} | "
            f"Size: {file_size} bytes | Method: {extraction_method}"
        )
        
        return PDFContent(
            url=url,
            title=title,
            text=text,
            num_pages=num_pages,
            file_size=file_size,
            metadata=combined_metadata,
            extraction_method=extraction_method,
            success=success,
            error=error
        )
