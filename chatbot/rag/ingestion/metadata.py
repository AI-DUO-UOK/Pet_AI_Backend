"""
Metadata Extraction and Building

Extracts and builds rich metadata for chunks to enable:
- Better retrieval filtering
- Source tracking
- Document structure preservation
- Semantic context
"""

import logging
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import uuid


logger = logging.getLogger(__name__)


class MetadataBuilder:
    """
    Builds rich metadata for document chunks
    
    Preserves:
    - Document source and type
    - Chunk position and relationships
    - Semantic structure (headings, sections)
    - Content type (text, table, code)
    - Processing information
    """
    
    def __init__(self):
        self.creation_timestamp = datetime.utcnow().isoformat()
    
    def build_pdf_metadata(
        self,
        source_file: str,
        chunk_index: int,
        chunk_type: str = "text",
        page_number: Optional[int] = None,
        section: Optional[str] = None,
        heading_hierarchy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build metadata for PDF chunk
        
        Args:
            source_file: PDF filename
            chunk_index: Index of chunk in document
            chunk_type: Type of chunk (text, table, figure, etc)
            page_number: Page number where chunk appears
            section: Section name
            heading_hierarchy: Heading context
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "chunk_id": str(uuid.uuid4()),
            "source": source_file,
            "source_type": "pdf",
            "document_type": "pdf",
            "chunk_index": chunk_index,
            "chunk_type": chunk_type,
            "created_at": self.creation_timestamp,
        }
        
        if page_number is not None:
            metadata["page"] = page_number
        
        if section:
            metadata["section"] = section
        
        if heading_hierarchy:
            metadata["heading_hierarchy"] = heading_hierarchy
        
        return metadata
    
    def build_markdown_metadata(
        self,
        source_file: str,
        chunk_index: int,
        chunk_type: str = "text",
        section: Optional[str] = None,
        subsection: Optional[str] = None,
        heading_hierarchy: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build metadata for markdown chunk (crawled content)
        
        Args:
            source_file: Markdown filename
            chunk_index: Index of chunk
            chunk_type: Type of chunk
            section: Main section name
            subsection: Subsection name
            heading_hierarchy: Full heading path
            url: Original URL (if from crawler)
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "chunk_id": str(uuid.uuid4()),
            "source": source_file,
            "source_type": "markdown",
            "document_type": "markdown",
            "chunk_index": chunk_index,
            "chunk_type": chunk_type,
            "created_at": self.creation_timestamp,
        }
        
        if section:
            metadata["section"] = section
        
        if subsection:
            metadata["subsection"] = subsection
        
        if heading_hierarchy:
            metadata["heading_hierarchy"] = heading_hierarchy
        
        if url:
            metadata["url"] = url
            # Extract domain from URL for better filtering
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                metadata["domain"] = domain
            except Exception:
                pass
        
        return metadata
    
    def extract_section_from_hierarchy(self, hierarchy: str) -> tuple[str, str]:
        """
        Extract main section and subsection from hierarchy
        
        Args:
            hierarchy: Heading hierarchy like "H1 > H2 > H3"
            
        Returns:
            Tuple of (section, subsection)
        """
        parts = [p.strip() for p in hierarchy.split(">")]
        
        section = parts[0] if len(parts) > 0 else ""
        subsection = parts[1] if len(parts) > 1 else ""
        
        return section, subsection
    
    def extract_url_from_markdown_filename(self, filename: str) -> Optional[str]:
        """
        Try to reconstruct URL from markdown filename
        
        Filenames from crawler are like:
        www.example.com__path__to__page.txt
        
        Args:
            filename: Markdown filename
            
        Returns:
            Reconstructed URL or None
        """
        try:
            # Remove .txt extension
            name = filename.replace(".txt", "")
            
            # Check if it looks like a crawler filename
            if "__" not in name:
                return None
            
            # Replace __ with / and dots appropriately
            # www.example.com__path__to__page -> www.example.com/path/to/page
            parts = name.split("__")
            
            # First part is domain
            if parts[0].startswith("www."):
                domain = parts[0]
                path_parts = parts[1:]
                url = f"https://{domain}/{'/'.join(path_parts)}"
                return url
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract URL from {filename}: {e}")
            return None
    
    def detect_chunk_type(self, chunk_text: str) -> str:
        """
        Detect chunk type from content
        
        Args:
            chunk_text: Chunk text
            
        Returns:
            Chunk type (text, table, code, list, etc)
        """
        # Table detection
        if self._has_table_markers(chunk_text):
            return "table"
        
        # Code block detection
        if self._has_code_markers(chunk_text):
            return "code"
        
        # List detection
        if self._is_mostly_list(chunk_text):
            return "list"
        
        # Default
        return "text"
    
    @staticmethod
    def _has_table_markers(text: str) -> bool:
        """Check if text contains table markers"""
        # Markdown table pipes
        pipe_lines = [line for line in text.split("\n") if "|" in line]
        
        if len(pipe_lines) < 2:
            return False
        
        # Check if multiple lines have pipes (indicates table)
        return len(pipe_lines) > 2
    
    @staticmethod
    def _has_code_markers(text: str) -> bool:
        """Check if text contains code markers"""
        return "```" in text or "    " * 4 in text
    
    @staticmethod
    def _is_mostly_list(text: str) -> bool:
        """Check if text is mostly list items"""
        lines = text.split("\n")
        list_markers = sum(
            1 for line in lines
            if line.strip().startswith(("-", "*", "+", "•"))
            or re.match(r"^\s*\d+\.", line)
        )
        
        return list_markers > len(lines) * 0.5
    
    def add_retrieval_metadata(
        self,
        metadata: Dict[str, Any],
        keyword_tags: List[str] = None,
        entity_tags: List[str] = None,
        importance_score: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Add retrieval-specific metadata
        
        Args:
            metadata: Base metadata
            keyword_tags: Extracted keywords
            entity_tags: Named entities
            importance_score: Importance for ranking
            
        Returns:
            Enhanced metadata
        """
        enhanced = metadata.copy()
        
        if keyword_tags:
            enhanced["keywords"] = keyword_tags
        
        if entity_tags:
            enhanced["entities"] = entity_tags
        
        enhanced["importance_score"] = importance_score
        
        return enhanced
