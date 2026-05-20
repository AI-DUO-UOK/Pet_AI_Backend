"""
LlamaIndex Node Builder

Converts chunks and serialized content into LlamaIndex TextNodes
with rich metadata and semantic structure
"""

import logging
from typing import List, Union, Dict, Any

from llama_index.core.schema import TextNode

from .chunking import MarkdownChunk
from .serialization import AdvancedSerializer
from .metadata import MetadataBuilder


logger = logging.getLogger(__name__)


class NodeBuilder:
    """
    Builds LlamaIndex TextNodes from chunks
    
    Creates nodes with:
    - Semantic serialized text
    - Rich metadata
    - Heading context
    - Source tracking
    - Chunk relationships
    """
    
    def __init__(self):
        self.serializer = AdvancedSerializer()
        self.metadata_builder = MetadataBuilder()
    
    def build_nodes_from_pdf_chunks(
        self,
        chunks: List[Any],
        source_file: str,
    ) -> List[TextNode]:
        """
        Build LlamaIndex nodes from PDF chunks
        
        Args:
            chunks: List of DocChunk from Docling
            source_file: Source PDF filename
            
        Returns:
            List of TextNode objects
        """
        nodes = []
        
        for idx, chunk in enumerate(chunks):
            # Detect chunk type
            chunk_type = self._detect_pdf_chunk_type(chunk)
            
            # Serialize based on type
            serialized_text = self._serialize_pdf_chunk(chunk, chunk_type)
            
            # Build metadata
            metadata = self.metadata_builder.build_pdf_metadata(
                source_file=source_file,
                chunk_index=idx,
                chunk_type=chunk_type,
            )
            
            # Create TextNode
            node = TextNode(
                text=serialized_text,
                metadata=metadata,
            )
            
            nodes.append(node)
        
        logger.info(f"Built {len(nodes)} nodes from PDF: {source_file}")
        return nodes
    
    def build_nodes_from_markdown_chunks(
        self,
        chunks: List[MarkdownChunk],
        source_file: str,
    ) -> List[TextNode]:
        """
        Build LlamaIndex nodes from markdown chunks
        
        Args:
            chunks: List of MarkdownChunk
            source_file: Source markdown filename
            
        Returns:
            List of TextNode objects
        """
        nodes = []
        
        # Extract URL from filename if possible
        url = self.metadata_builder.extract_url_from_markdown_filename(source_file)
        
        for chunk in chunks:
            # Extract section info from hierarchy
            section, subsection = self.metadata_builder.extract_section_from_hierarchy(
                chunk.heading_hierarchy
            )
            
            # Serialize text with context
            serialized_text = self.serializer.serialize_text_chunk(
                text=chunk.text,
                headings=chunk.headings,
                heading_hierarchy=chunk.heading_hierarchy,
                section=section,
            )
            
            # Build metadata
            metadata = self.metadata_builder.build_markdown_metadata(
                source_file=source_file,
                chunk_index=chunk.id,
                section=section,
                subsection=subsection,
                heading_hierarchy=chunk.heading_hierarchy,
                url=url,
            )
            
            # Create TextNode
            node = TextNode(
                text=serialized_text,
                metadata=metadata,
            )
            
            nodes.append(node)
        
        logger.info(f"Built {len(nodes)} nodes from markdown: {source_file}")
        return nodes
    
    def _detect_pdf_chunk_type(self, chunk: Any) -> str:
        """
        Detect chunk type from Docling DocChunk
        
        Args:
            chunk: Docling DocChunk
            
        Returns:
            Chunk type (text, table, etc)
        """
        chunk_text = str(chunk.text).lower()
        
        # Check for table indicators
        if "|" in chunk_text and "\n" in chunk_text:
            pipe_count = chunk_text.count("|")
            newline_count = chunk_text.count("\n")
            
            if pipe_count > 2 and newline_count > 2:
                return "table"
        
        return "text"
    
    def _serialize_pdf_chunk(self, chunk: Any, chunk_type: str) -> str:
        """
        Serialize PDF chunk based on type
        
        Args:
            chunk: Docling DocChunk
            chunk_type: Type of chunk
            
        Returns:
            Serialized text
        """
        if chunk_type == "table":
            return self._serialize_pdf_table_chunk(chunk)
        else:
            return self._serialize_pdf_text_chunk(chunk)
    
    def _serialize_pdf_text_chunk(self, chunk: Any) -> str:
        """
        Serialize regular text chunk from PDF
        
        Args:
            chunk: Docling DocChunk
            
        Returns:
            Serialized text
        """
        headings = []
        
        # Extract heading information if available
        if hasattr(chunk, "meta") and hasattr(chunk.meta, "headings"):
            headings = chunk.meta.headings
        
        return self.serializer.serialize_text_chunk(
            text=chunk.text,
            headings=headings,
        )
    
    def _serialize_pdf_table_chunk(self, chunk: Any) -> str:
        """
        Serialize table chunk from PDF
        
        Args:
            chunk: Docling DocChunk containing table
            
        Returns:
            Serialized table
        """
        lines = chunk.text.splitlines()
        
        # Extract table lines (containing pipes)
        table_lines = [
            line for line in lines
            if "|" in line
        ]
        
        if len(table_lines) < 2:
            # Not a proper table, return as-is
            return chunk.text
        
        # Extract headers (first line)
        headers = [
            h.strip() for h in table_lines[0].split("|")
            if h.strip()
        ]
        
        # Extract rows (skip separator at line 1)
        rows = []
        for line in table_lines[2:]:
            cells = [
                c.strip() for c in line.split("|")
                if c.strip()
            ]
            
            if len(cells) == len(headers):
                rows.append(cells)
        
        # Serialize
        serialized_rows = self.serializer.serialize_table(
            headers=headers,
            rows=rows,
        )
        
        return "\n".join(serialized_rows)
    
    def merge_node_metadata(
        self,
        node: TextNode,
        additional_metadata: Dict[str, Any],
    ) -> TextNode:
        """
        Merge additional metadata into a node
        
        Args:
            node: TextNode to update
            additional_metadata: Metadata to add
            
        Returns:
            Updated TextNode
        """
        node.metadata.update(additional_metadata)
        return node
