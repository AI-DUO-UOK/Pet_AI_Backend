#!/usr/bin/env python3
"""
Advanced RAG Document Ingestion Script

Usage:
    python chatbot/scripts/ingest_documents.py            # Ingest all
    python chatbot/scripts/ingest_documents.py --pdfs     # PDFs only
    python chatbot/scripts/ingest_documents.py --markdown # Markdown only
    python chatbot/scripts/ingest_documents.py --stats    # Show stats
"""

import logging
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from chatbot.rag.ingestion.pipeline import UnifiedRAGPipeline
from chatbot.rag.config import PDF_DIR, MARKDOWN_DIR


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Advanced RAG Document Ingestion"
    )
    parser.add_argument(
        "--pdfs",
        action="store_true",
        help="Ingest PDFs only"
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Ingest markdown files only"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show collection statistics"
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=PDF_DIR,
        help="PDF directory"
    )
    parser.add_argument(
        "--markdown-dir",
        type=Path,
        default=MARKDOWN_DIR,
        help="Markdown directory"
    )
    
    args = parser.parse_args()
    
    try:
        logger.info("=" * 70)
        logger.info("Advanced RAG Document Ingestion Pipeline")
        logger.info("=" * 70)
        
        # Initialize pipeline
        pipeline = UnifiedRAGPipeline()
        
        # Handle stats request
        if args.stats:
            stats = pipeline.get_collection_stats()
            logger.info("Collection Statistics:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")
            return 0
        
        # Determine what to ingest
        if args.pdfs and not args.markdown:
            logger.info(f"Ingesting PDFs from {args.pdf_dir}")
            count = pipeline.ingest_pdfs(args.pdf_dir)
            logger.info(f"✓ Ingested {count} PDF nodes")
        
        elif args.markdown and not args.pdfs:
            logger.info(f"Ingesting markdown from {args.markdown_dir}")
            count = pipeline.ingest_markdown(args.markdown_dir)
            logger.info(f"✓ Ingested {count} markdown nodes")
        
        else:  # Default: ingest all
            logger.info("Ingesting all documents...")
            stats = pipeline.ingest_all(
                pdf_dir=args.pdf_dir,
                markdown_dir=args.markdown_dir,
            )
            logger.info("=" * 70)
            logger.info("Ingestion Complete!")
            logger.info(f"  PDFs:     {stats['pdf_nodes']} nodes")
            logger.info(f"  Markdown: {stats['markdown_nodes']} nodes")
            logger.info(f"  Total:    {stats['total_nodes']} nodes")
            logger.info("=" * 70)
            
            # Show collection stats
            collection_stats = pipeline.get_collection_stats()
            if collection_stats:
                logger.info("\nCollection Statistics:")
                for key, value in collection_stats.items():
                    logger.info(f"  {key}: {value}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
