#!/usr/bin/env python
"""Quick test to verify agentic RAG imports and basic functionality"""

try:
    print("Testing imports...")
    from chatbot.rag.agentic_rag import query_agentic_rag, create_agentic_rag_agent
    print("✅ Successfully imported agentic RAG modules")
    
    print("\nCreating agentic RAG agent...")
    agent = create_agentic_rag_agent()
    print("✅ Successfully created agentic RAG agent")
    
    print("\n✅ All checks passed! Agentic RAG system is ready.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
