"""
Document Loaders for PDF and Markdown Files

Provides unified loading interface for:
- PDF documents (via Docling)
- Markdown text files (crawled web content)
"""

from pathlib import Path
from typing import Union, Optional, Any
import logging

from docling.document_converter import DocumentConverter


logger = logging.getLogger(__name__)


class PDFLoader:
    """
    PDF document loader using Docling
    
    Extracts:
    - Structured text
    - Tables
    - Figures
    - Hierarchical layout information
    - Formatting metadata
    """
    
    def __init__(self):
        self.converter = DocumentConverter()
        logger.info("Initialized PDFLoader with Docling")
    
    def load_pdf(self, pdf_path: Union[str, Path]) -> Any:
        """
        Load and parse a PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Structured DoclingDocument
            
        Raises:
            FileNotFoundError: If PDF doesn't exist
            ValueError: If PDF parsing fails
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        if not pdf_path.suffix.lower() == ".pdf":
            raise ValueError(f"File must be PDF: {pdf_path}")
        
        try:
            logger.info(f"Loading PDF: {pdf_path.name}")
            result = self.converter.convert(str(pdf_path))
            logger.info(f"Successfully parsed PDF: {pdf_path.name}")
            return result.document
            
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path.name}: {e}")
            raise ValueError(f"PDF parsing failed: {e}") from e


class MarkdownLoader:
    """
    Markdown document loader for crawled web content
    
    Handles:
    - Markdown formatted text files
    - Heading hierarchies
    - Lists and tables
    - Link preservation
    - Cleaned HTML-to-markdown conversions
    
    Used for content from rag_output_cleaned/
    """
    
    def load_markdown(self, md_path: Union[str, Path]) -> str:
        """
        Load markdown content from text file
        
        Args:
            md_path: Path to markdown/text file
            
        Returns:
            Raw markdown content
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        md_path = Path(md_path)
        
        if not md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")
        
        try:
            logger.info(f"Loading markdown: {md_path.name}")
            content = md_path.read_text(encoding="utf-8")
            logger.info(f"Successfully loaded: {md_path.name} ({len(content)} chars)")
            return content
            
        except Exception as e:
            logger.error(f"Error loading markdown {md_path.name}: {e}")
            raise ValueError(f"Markdown loading failed: {e}") from e
    
    def extract_frontmatter(self, content: str) -> tuple[dict, str]:
        """
        Extract YAML frontmatter from markdown if present
        
        Args:
            content: Raw markdown content
            
        Returns:
            Tuple of (metadata_dict, content_without_frontmatter)
        """
        if not content.startswith("---"):
            return {}, content
        
        try:
            import yaml
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1]) or {}
                clean_content = parts[2].strip()
                return metadata, clean_content
        except Exception as e:
            logger.warning(f"Failed to parse frontmatter: {e}")
        
        return {}, content


class DocumentLoader:
    """
    Unified document loader for both PDFs and markdown files
    
    Automatically detects file type and uses appropriate loader
    """
    
    def __init__(self):
        self.pdf_loader = PDFLoader()
        self.markdown_loader = MarkdownLoader()
    
    def load(self, file_path: Union[str, Path]) -> Union[Any, str]:
        """
        Load document (PDF or Markdown) automatically
        
        Args:
            file_path: Path to document
            
        Returns:
            DoclingDocument for PDFs, str content for markdown
            
        Raises:
            ValueError: If file format not supported
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        if extension == ".pdf":
            return self.pdf_loader.load_pdf(file_path)
        
        elif extension in [".txt", ".md"]:
            return self.markdown_loader.load_markdown(file_path)
        
        else:
            raise ValueError(
                f"Unsupported file format: {extension}. "
                f"Supported: .pdf, .txt, .md"
            )
    
    def load_directory(
        self, 
        directory: Union[str, Path],
        pattern: Optional[str] = None
    ) -> dict[str, Union[Any, str]]:
        """
        Load all documents from a directory
        
        Args:
            directory: Path to directory
            pattern: Glob pattern (default: all supported files)
            
        Returns:
            Dictionary of {file_name: document}
        """
        directory = Path(directory)
        
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        documents = {}
        
        # Default pattern matches PDFs and markdown files
        if pattern is None:
            patterns = ["*.pdf", "*.txt", "*.md"]
        else:
            patterns = [pattern]
        
        file_count = 0
        for pattern in patterns:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    try:
                        documents[file_path.name] = self.load(file_path)
                        file_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to load {file_path.name}: {e}")
        
        logger.info(f"Loaded {file_count} documents from {directory.name}")
        return documents
