#!/usr/bin/env python3
"""
Test Full RAG Pipeline with Answer Generation

Demonstrates:
1. Retrieval with confidence scores
2. Filtering by confidence threshold
3. Answer generation with LLM
4. Fallback to general knowledge
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from chatbot.rag.qa import ask_rag

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_rag_pipeline():
    """Test full RAG pipeline with various queries"""
    
    test_queries = [
        "What causes dermatitis in dogs?",
        "How to treat vomiting in cats?",
        "What is hypermagnesemia in pets?",
        "Causes of diarrhea in dogs",
    ]
    
    logger.info("=" * 70)
    logger.info("FULL RAG PIPELINE TEST")
    logger.info("=" * 70)
    
    for i, query in enumerate(test_queries, 1):
        print("\n" + "=" * 70)
        print(f"QUERY {i}: {query}")
        print("=" * 70)
        
        # Call the full RAG pipeline
        answer = ask_rag(query, confidence_threshold=0.65)
        
        print(f"\nANSWER:\n{answer}")
        print("\n" + "-" * 70)


if __name__ == "__main__":
    try:
        test_rag_pipeline()
        logger.info("\n✓ RAG pipeline test completed successfully")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
