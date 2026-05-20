"""
Advanced RAG Pipeline Configuration
Configures embedding models, chunk sizes, storage paths, and other RAG parameters
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────────
# Path Configuration
# ─────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

# Input directories
PDF_DIR = BASE_DIR / "raw_pdfs"  # Create this directory and place PDFs here
MARKDOWN_DIR = BASE_DIR / "rag_output_cleaned"  # Existing cleaned content

# Vector store directory (ChromaDB)
# Uses existing db structure, but in a separate collection
CHROMA_DB_DIR = BASE_DIR / "db"
COLLECTION_NAME = "pet_health_rag_v2"

# Ensure directories exist
PDF_DIR.mkdir(parents=True, exist_ok=True)
MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────
# Embedding Model Configuration
# ─────────────────────────────────────────────────────────────────

# High-quality embedding model
# BAAI/bge-small-en-v1.5 - good balance of quality and speed
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Alternative models (for future reference):
# - BAAI/bge-base-en-v1.5 (higher quality, slower)
# - nomic-ai/nomic-embed-text-v1 (good for medical/technical)
# - intfloat/e5-base-v2 (versatile)

EMBEDDING_DIMENSION = 384  # For BAAI/bge-small-en-v1.5


# ─────────────────────────────────────────────────────────────────
# Chunking Configuration
# ─────────────────────────────────────────────────────────────────

# HybridChunker settings
MAX_TOKENS = 512  # Max tokens per chunk
MIN_TOKENS = 100  # Minimum tokens per chunk
MERGE_PEERS = True  # Merge small adjacent chunks

# Chunk overlap (for context preservation)
CHUNK_OVERLAP = 50

# Table-specific settings
TABLE_ROW_GROUP_SIZE = 5  # Group rows for serialization


# ─────────────────────────────────────────────────────────────────
# Document Processing
# ─────────────────────────────────────────────────────────────────

# Supported file types
SUPPORTED_FORMATS = {
    "pdf": [".pdf"],
    "markdown": [".txt", ".md"],  # Markdown files from crawler
}

# Docling PDF parsing settings
DOCLING_TIMEOUT = 300  # Timeout for PDF processing (seconds)


# ─────────────────────────────────────────────────────────────────
# Retrieval Configuration
# ─────────────────────────────────────────────────────────────────

# Semantic retrieval settings
SIMILARITY_TOP_K = 3  # Number of top results to return
RETRIEVAL_BATCH_SIZE = 1000  # Batch size for indexing


# ─────────────────────────────────────────────────────────────────
# Metadata Configuration
# ─────────────────────────────────────────────────────────────────

# Metadata fields to preserve
METADATA_FIELDS = [
    "source",
    "chunk_id",
    "chunk_index",
    "chunk_type",
    "section",
    "subsection",
    "page",
    "document_type",
    "heading_hierarchy",
]


# ─────────────────────────────────────────────────────────────────
# Processing Settings
# ─────────────────────────────────────────────────────────────────

# Batch processing
BATCH_SIZE = 32
PROCESSING_TIMEOUT = 300  # Timeout per document (seconds)

# Logging
LOG_LEVEL = "INFO"
VERBOSE = True
