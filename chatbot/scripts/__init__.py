"""
Unified Document Ingestion Script

Ingests both PDFs and markdown files into the advanced RAG pipeline
"""

import logging
import sys
from pathlib import Path

from chatbot.rag.ingestion.pipeline import UnifiedRAGPipeline
from chatbot.rag.config import PDF_DIR, MARKDOWN_DIR


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """
    Run unified ingestion pipeline
    """
    try:
        logger.info("=" * 60)
        logger.info("Advanced RAG Ingestion Pipeline")
        logger.info("=" * 60)
        
        # Initialize pipeline
        pipeline = UnifiedRAGPipeline()
        
        # Ingest all documents
        stats = pipeline.ingest_all(
            pdf_dir=PDF_DIR,
            markdown_dir=MARKDOWN_DIR,
        )
        
        # Print summary
        logger.info("=" * 60)
        logger.info("Ingestion Complete!")
        logger.info(f"  PDFs ingested: {stats['pdf_nodes']} nodes")
        logger.info(f"  Markdown ingested: {stats['markdown_nodes']} nodes")
        logger.info(f"  Total: {stats['total_nodes']} nodes")
        logger.info("=" * 60)
        
        # Print collection stats
        collection_stats = pipeline.get_collection_stats()
        if collection_stats:
            logger.info("Collection Statistics:")
            for key, value in collection_stats.items():
                logger.info(f"  {key}: {value}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
