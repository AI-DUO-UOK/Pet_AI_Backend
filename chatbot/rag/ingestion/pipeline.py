"""
Unified RAG Ingestion Pipeline

Orchestrates:
- Document loading
- Advanced chunking
- Semantic serialization
- Node building
- Vector indexing

Supports both PDFs and markdown files
"""

import logging
from pathlib import Path
from typing import List, Union, Optional

from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from .loaders import DocumentLoader, PDFLoader, MarkdownLoader
from .chunking import AdvancedChunker
from .node_builder import NodeBuilder
from .metadata import MetadataBuilder
from ..vectorstore import ChromaStore
from ..config import (
    PDF_DIR,
    MARKDOWN_DIR,
    EMBED_MODEL_NAME,
    BATCH_SIZE,
)


logger = logging.getLogger(__name__)


class UnifiedRAGPipeline:
    """
    Complete end-to-end RAG ingestion pipeline
    
    Workflow:
    1. Load documents (PDF or markdown)
    2. Advanced semantic chunking
    3. Chunk serialization
    4. Metadata extraction
    5. Node building
    6. Embedding generation
    7. Vector storage
    """
    
    def __init__(
        self,
        embed_model_name: str = EMBED_MODEL_NAME,
    ):
        """
        Initialize the pipeline
        
        Args:
            embed_model_name: Name of embedding model
        """
        self.document_loader = DocumentLoader()
        self.chunker = AdvancedChunker()
        self.node_builder = NodeBuilder()
        self.metadata_builder = MetadataBuilder()
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {embed_model_name}")
        self.embed_model = HuggingFaceEmbedding(
            model_name=embed_model_name
        )
        
        # Initialize vector store
        self.vector_store_manager = ChromaStore()
        
        logger.info("UnifiedRAGPipeline initialized")
    
    def ingest_pdfs(
        self,
        pdf_dir: Union[str, Path] = PDF_DIR,
        pattern: str = "*.pdf",
    ) -> int:
        """
        Ingest all PDFs from directory
        
        Args:
            pdf_dir: Directory containing PDFs
            pattern: Glob pattern for PDF files
            
        Returns:
            Number of documents ingested
        """
        pdf_dir = Path(pdf_dir)
        
        if not pdf_dir.exists():
            logger.warning(f"PDF directory not found: {pdf_dir}")
            return 0
        
        logger.info(f"Ingesting PDFs from {pdf_dir}")
        
        pdf_files = list(pdf_dir.glob(pattern))
        logger.info(f"Found {len(pdf_files)} PDFs")
        
        total_nodes = 0
        
        for pdf_file in pdf_files:
            try:
                nodes = self._ingest_single_pdf(pdf_file)
                total_nodes += len(nodes)
            except Exception as e:
                logger.error(f"Failed to ingest {pdf_file.name}: {e}")
        
        return total_nodes
    
    def ingest_markdown(
        self,
        markdown_dir: Union[str, Path] = MARKDOWN_DIR,
        pattern: str = "*.txt",
    ) -> int:
        """
        Ingest all markdown files from directory
        
        Args:
            markdown_dir: Directory containing markdown files
            pattern: Glob pattern for files
            
        Returns:
            Number of documents ingested
        """
        markdown_dir = Path(markdown_dir)
        
        if not markdown_dir.exists():
            logger.warning(f"Markdown directory not found: {markdown_dir}")
            return 0
        
        logger.info(f"Ingesting markdown from {markdown_dir}")
        
        markdown_files = list(markdown_dir.glob(pattern))
        logger.info(f"Found {len(markdown_files)} markdown files")
        
        total_nodes = 0
        
        for md_file in markdown_files:
            try:
                nodes = self._ingest_single_markdown(md_file)
                total_nodes += len(nodes)
            except Exception as e:
                logger.error(f"Failed to ingest {md_file.name}: {e}")
        
        return total_nodes
    
    def ingest_all(
        self,
        pdf_dir: Union[str, Path] = PDF_DIR,
        markdown_dir: Union[str, Path] = MARKDOWN_DIR,
    ) -> dict:
        """
        Ingest all documents (PDFs and markdown)
        
        Args:
            pdf_dir: PDF directory
            markdown_dir: Markdown directory
            
        Returns:
            Dictionary with ingestion stats
        """
        logger.info("Starting unified document ingestion...")
        
        # Ingest PDFs
        pdf_count = self.ingest_pdfs(pdf_dir)
        
        # Ingest markdown
        markdown_count = self.ingest_markdown(markdown_dir)
        
        total = pdf_count + markdown_count
        
        logger.info(f"Ingestion complete: {total} nodes indexed")
        
        return {
            "pdf_nodes": pdf_count,
            "markdown_nodes": markdown_count,
            "total_nodes": total,
        }
    
    def _ingest_single_pdf(self, pdf_path: Path) -> List:
        """
        Ingest a single PDF file
        
        Args:
            pdf_path: Path to PDF
            
        Returns:
            List of created nodes
        """
        logger.info(f"Processing PDF: {pdf_path.name}")
        
        # Load PDF
        pdf_loader = PDFLoader()
        doc = pdf_loader.load_pdf(pdf_path)
        
        # Chunk document
        chunks = self.chunker.chunk_pdf(doc)
        logger.info(f"  Created {len(chunks)} chunks")
        
        # Build nodes
        nodes = self.node_builder.build_nodes_from_pdf_chunks(
            chunks=chunks,
            source_file=pdf_path.name,
        )
        
        # Index nodes
        self._index_nodes(nodes)
        
        return nodes
    
    def _ingest_single_markdown(self, md_path: Path) -> List:
        """
        Ingest a single markdown file
        
        Args:
            md_path: Path to markdown file
            
        Returns:
            List of created nodes
        """
        logger.info(f"Processing markdown: {md_path.name}")
        
        # Load markdown
        markdown_loader = MarkdownLoader()
        content = markdown_loader.load_markdown(md_path)
        
        # Extract frontmatter if present
        frontmatter, content = markdown_loader.extract_frontmatter(content)
        
        # Chunk markdown
        chunks = self.chunker.chunk_markdown(content)
        logger.info(f"  Created {len(chunks)} chunks")
        
        # Build nodes
        nodes = self.node_builder.build_nodes_from_markdown_chunks(
            chunks=chunks,
            source_file=md_path.name,
        )
        
        # Add frontmatter data to metadata if present
        if frontmatter:
            for node in nodes:
                node.metadata.update(frontmatter)
        
        # Index nodes
        self._index_nodes(nodes)
        
        return nodes
    
    def _index_nodes(self, nodes: List) -> bool:
        """
        Index nodes into vector store
        
        Args:
            nodes: List of TextNode objects
            
        Returns:
            True if successful
        """
        try:
            if not nodes:
                return True
            
            logger.info(f"Indexing {len(nodes)} nodes...")
            
            # Create or update index
            index = VectorStoreIndex(
                nodes=nodes,
                storage_context=self.vector_store_manager.get_storage_context(),
                embed_model=self.embed_model,
                show_progress=True,
            )
            
            # Persist
            self.vector_store_manager.persist()
            
            logger.info(f"✓ Successfully indexed {len(nodes)} nodes")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing nodes: {e}")
            raise
    
    def get_index(self) -> VectorStoreIndex:
        """
        Get the current vector index for retrieval
        
        Returns:
            VectorStoreIndex
        """
        try:
            index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store_manager.get_vector_store(),
                embed_model=self.embed_model,
            )
            return index
        except Exception as e:
            logger.error(f"Error getting index: {e}")
            raise
    
    def get_collection_stats(self) -> dict:
        """
        Get statistics about indexed documents
        
        Returns:
            Statistics dictionary
        """
        return self.vector_store_manager.get_collection_stats()
