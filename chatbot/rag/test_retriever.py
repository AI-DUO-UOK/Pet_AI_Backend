import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from chatbot.rag.retriever import get_advanced_retriever

retriever = get_advanced_retriever()

queries = [
    "Dog is vomiting"
]

for q in queries:
    print("\n" + "="*50)
    print("QUERY:", q)

    # Use the advanced retriever's search method
    results = retriever.search(q, top_k=3)
    
    if not results:
        print("No results found")
    else:
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results):
            print(f"\n--- Result {i+1} ---")
            print(f"Score: {result.get('score', 'N/A'):.4f}")
            print(f"Type: {result.get('chunk_type', 'text')}")
            print(f"Source: {result.get('source', 'Unknown')}")
            print(f"\nContent:")
            print(result.get('content', 'No content')[:1000])