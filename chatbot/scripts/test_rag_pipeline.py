#!/usr/bin/env python3
"""
RAG Pipeline Test Script

Tests the advanced RAG pipeline with sample queries
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from chatbot.rag.retriever import get_advanced_retriever
from chatbot.rag.retrieval.query_engine import RAGQueryEngine
from chatbot.rag.config import MARKDOWN_DIR, PDF_DIR
from chatbot.llm import llm


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_retriever():
    """Test the retriever"""
    logger.info("=" * 70)
    logger.info("Testing Advanced Retriever")
    logger.info("=" * 70)
    
    # Get retriever
    retriever = get_advanced_retriever()
    
    # Check if index is loaded
    if not retriever.semantic_retriever:
        logger.error("❌ No index available. Run ingestion first:")
        logger.error(f"   python chatbot/scripts/ingest_documents.py")
        return False
    
    logger.info("✓ Retriever initialized")
    
    # Test query
    test_query = "Which drugs treat heart failure?"
    logger.info(f"\nTest query: {test_query}")
    
    results = retriever.search(test_query, top_k=3)
    
    if not results:
        logger.warning("❌ No results found")
        return False
    
    logger.info(f"✓ Found {len(results)} results\n")
    
    for i, result in enumerate(results, 1):
        logger.info(f"Result {i}:")
        logger.info(f"  Source: {result['source']}")
        logger.info(f"  Type: {result['chunk_type']}")
        logger.info(f"  Score: {result['score']:.4f}")
        logger.info(f"  Content preview: {result['content'][:150]}...")
        logger.info()
    
    return True


def test_query_engine():
    """Test the query engine"""
    logger.info("=" * 70)
    logger.info("Testing Query Engine")
    logger.info("=" * 70)
    
    retriever = get_advanced_retriever()
    
    if not retriever.semantic_retriever:
        logger.error("❌ No index available")
        return False
    
    # Create query engine
    query_engine = RAGQueryEngine(
        retriever=retriever.semantic_retriever,
        llm=llm,
    )
    
    # Test query
    test_query = "What are symptoms of heart failure in dogs?"
    logger.info(f"\nTest query: {test_query}\n")
    
    # Get retrieval explanation
    explanation = query_engine.explain_retrieval(test_query, top_k=3)
    
    logger.info("Retrieved documents:")
    for result in explanation["results"]:
        logger.info(f"\n  Rank {result['rank']}: {result['source']} (score: {result['score']:.4f})")
        logger.info(f"    Type: {result['chunk_type']}")
        logger.info(f"    Preview: {result['content_preview']}")
    
    return True


def test_collection_stats():
    """Test collection statistics"""
    logger.info("=" * 70)
    logger.info("Collection Statistics")
    logger.info("=" * 70)
    
    retriever = get_advanced_retriever()
    stats = retriever.vector_store_manager.get_collection_stats()
    
    if stats:
        for key, value in stats.items():
            logger.info(f"{key}: {value}")
    else:
        logger.warning("No documents indexed yet")


def main():
    """Run all tests"""
    logger.info("\n")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + " " * 15 + "Advanced RAG Pipeline Tests" + " " * 27 + "║")
    logger.info("╚" + "=" * 68 + "╝")
    
    # Check if directories exist and have content
    logger.info(f"\nChecking directories:")
    logger.info(f"  PDF directory: {PDF_DIR} (exists: {PDF_DIR.exists()})")
    logger.info(f"  Markdown directory: {MARKDOWN_DIR} (exists: {MARKDOWN_DIR.exists()})")
    
    if MARKDOWN_DIR.exists():
        md_count = len(list(MARKDOWN_DIR.glob("*.txt")))
        logger.info(f"    Markdown files: {md_count}")
    
    if PDF_DIR.exists():
        pdf_count = len(list(PDF_DIR.glob("*.pdf")))
        logger.info(f"    PDF files: {pdf_count}")
    
    # Test collection stats
    test_collection_stats()
    
    # Test retriever
    if not test_retriever():
        logger.error("\nTests failed - No index available")
        logger.error("Run ingestion first: python chatbot/scripts/ingest_documents.py")
        return 1
    
    # Test query engine
    test_query_engine()
    
    logger.info("\n" + "=" * 70)
    logger.info("✓ All tests completed")
    logger.info("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
