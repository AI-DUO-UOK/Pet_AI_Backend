"""
Advanced Semantic Chunking using HybridChunker

Provides intelligent, structure-aware chunking for:
- PDFs with layout preservation
- Markdown documents with heading hierarchy
- Tables with row-level granularity
- Code blocks and examples
- Mathematical content
"""

import logging
from typing import List, Union, Any
from pathlib import Path

from docling.chunking import HybridChunker
from transformers import AutoTokenizer

from ..config import EMBED_MODEL_NAME, MAX_TOKENS, MERGE_PEERS


logger = logging.getLogger(__name__)


class AdvancedChunker:
    """
    Advanced hybrid chunker combining:
    - Token-aware chunking
    - Structure preservation
    - Semantic boundaries
    - Table-aware splitting
    - Heading hierarchy preservation
    """
    
    def __init__(self, max_tokens: int = MAX_TOKENS):
        """
        Initialize chunker with HybridChunker
        
        Args:
            max_tokens: Maximum tokens per chunk
        """
        self.max_tokens = max_tokens
        self.tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_NAME)
        
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
            max_tokens=max_tokens,
            merge_peers=MERGE_PEERS,
        )
        
        logger.info(
            f"Initialized AdvancedChunker with max_tokens={max_tokens}, "
            f"merge_peers={MERGE_PEERS}"
        )
    
    def chunk_pdf(self, doc: Any) -> List[Any]:
        """
        Chunk a Docling PDF document
        
        Args:
            doc: Parsed DoclingDocument from Docling
            
        Returns:
            List of semantic chunks
        """
        try:
            logger.info(f"Chunking PDF document with {len(doc.pages)} pages")
            chunks = list(self.chunker.chunk(doc))
            logger.info(f"Created {len(chunks)} chunks from PDF")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking PDF: {e}")
            raise
    
    def chunk_markdown(self, content: str) -> List["MarkdownChunk"]:
        """
        Intelligent chunking for markdown content
        
        Preserves:
        - Heading hierarchy
        - Semantic sections
        - List structures
        - Table integrity
        
        Args:
            content: Raw markdown content
            
        Returns:
            List of markdown chunks
        """
        try:
            logger.info(f"Chunking markdown content ({len(content)} chars)")
            chunks = self._split_by_heading_hierarchy(content)
            logger.info(f"Created {len(chunks)} chunks from markdown")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking markdown: {e}")
            raise
    
    def _split_by_heading_hierarchy(self, content: str) -> List["MarkdownChunk"]:
        """
        Split markdown by heading hierarchy
        
        Preserves semantic structure while keeping chunks at optimal size
        
        Args:
            content: Raw markdown content
            
        Returns:
            List of MarkdownChunk objects
        """
        chunks = []
        lines = content.split("\n")
        
        current_chunk = []
        current_headings = []
        current_tokens = 0
        chunk_id = 0
        
        for line in lines:
            # Detect heading level
            heading_level = self._get_heading_level(line)
            
            # Check if we should start a new chunk
            if heading_level == 1 and current_chunk:
                # H1 always starts new chunk
                chunk_text = "\n".join(current_chunk).strip()
                if chunk_text:
                    chunks.append(MarkdownChunk(
                        id=chunk_id,
                        text=chunk_text,
                        headings=current_headings.copy(),
                        heading_hierarchy=self._build_hierarchy(current_headings),
                    ))
                    chunk_id += 1
                
                current_chunk = [line]
                current_headings = [line] if heading_level > 0 else []
                current_tokens = len(self.tokenizer.encode(line))
            
            elif heading_level in [2, 3] and current_tokens > self.max_tokens * 0.7:
                # H2/H3 can start new chunk if current is large
                chunk_text = "\n".join(current_chunk).strip()
                if chunk_text:
                    chunks.append(MarkdownChunk(
                        id=chunk_id,
                        text=chunk_text,
                        headings=current_headings.copy(),
                        heading_hierarchy=self._build_hierarchy(current_headings),
                    ))
                    chunk_id += 1
                
                current_chunk = [line]
                if heading_level > 0:
                    current_headings = [line]
                current_tokens = len(self.tokenizer.encode(line))
            
            else:
                # Add to current chunk
                current_chunk.append(line)
                line_tokens = len(self.tokenizer.encode(line))
                current_tokens += line_tokens
                
                # Track headings for context
                if heading_level > 0:
                    current_headings = current_headings[:heading_level-1] + [line]
                
                # Split if too large
                if current_tokens > self.max_tokens:
                    chunk_text = "\n".join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(MarkdownChunk(
                            id=chunk_id,
                            text=chunk_text,
                            headings=current_headings.copy(),
                            heading_hierarchy=self._build_hierarchy(current_headings),
                        ))
                        chunk_id += 1
                    
                    current_chunk = []
                    current_tokens = 0
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text:
                chunks.append(MarkdownChunk(
                    id=chunk_id,
                    text=chunk_text,
                    headings=current_headings.copy(),
                    heading_hierarchy=self._build_hierarchy(current_headings),
                ))
        
        return chunks
    
    def _get_heading_level(self, line: str) -> int:
        """
        Extract markdown heading level (1-6) or 0 if not a heading
        
        Args:
            line: Text line
            
        Returns:
            Heading level (0-6)
        """
        line = line.strip()
        
        for level in range(1, 7):
            if line.startswith("#" * level + " "):
                return level
        
        return 0
    
    def _build_hierarchy(self, headings: List[str]) -> str:
        """
        Build heading hierarchy path
        
        Args:
            headings: List of heading lines in order
            
        Returns:
            Hierarchy string like "H1 > H2 > H3"
        """
        hierarchy = []
        
        for heading in headings:
            # Remove markdown syntax and clean
            clean = heading.lstrip("#").strip()
            if clean:
                hierarchy.append(clean)
        
        return " > ".join(hierarchy)


class MarkdownChunk:
    """
    Represents a semantic chunk from markdown content
    
    Preserves heading context and hierarchy information
    """
    
    def __init__(
        self,
        id: int,
        text: str,
        headings: List[str] = None,
        heading_hierarchy: str = "",
    ):
        self.id = id
        self.text = text
        self.headings = headings or []
        self.heading_hierarchy = heading_hierarchy
    
    def __repr__(self) -> str:
        return f"MarkdownChunk(id={self.id}, text_len={len(self.text)})"
