#!/usr/bin/env python
"""Test agentic RAG import"""

import sys
sys.path.insert(0, '/Users/akilafernando/Documents/GitHub/Pet_AI_Backend')

try:
    print("Testing agentic RAG imports...")
    from chatbot.rag.agentic_rag import query_agentic_rag, search_veterinary_knowledge_base
    print("✅ Successfully imported agentic RAG functions")
    
    print("\n✅ All imports successful! Ready to use.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
