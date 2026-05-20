# Advanced RAG Pipeline - Quick Reference Guide

## 🚀 5-Minute Quick Start

### 1. Install & Setup
```bash
cd /path/to/Pet_AI_Backend
pip install -r requirements.txt
```

### 2. Ingest Your Documents
```bash
# Ingest all documents
python chatbot/scripts/ingest_documents.py

# Show what was indexed
python chatbot/scripts/ingest_documents.py --stats
```

### 3. Test It Works
```bash
python chatbot/scripts/test_rag_pipeline.py
```

### 4. Use in Your Code
```python
from chatbot.rag.qa import ask_rag

answer = ask_rag("Which drugs treat heart failure?")
print(answer)
```

---

## 📚 Common Use Cases

### Basic Question Answering
```python
from chatbot.rag.qa import ask_rag

answer = ask_rag("What are symptoms of diabetes in dogs?")
print(answer)
```

### Advanced Retrieval with Context
```python
from chatbot.rag.retriever import get_advanced_retriever

retriever = get_advanced_retriever()

# Search for relevant documents
results = retriever.search("heart failure treatment", top_k=5)

for result in results:
    print(f"Source: {result['source']}")
    print(f"Score: {result['score']:.4f}")
    print(f"Content: {result['content'][:200]}...")
    print()
```

### Query with Explanation
```python
from chatbot.rag.retrieval.query_engine import RAGQueryEngine
from chatbot.rag.retriever import get_advanced_retriever
from chatbot.llm import llm

retriever = get_advanced_retriever()
engine = RAGQueryEngine(retriever.semantic_retriever, llm=llm)

# Get query explanation
explanation = engine.explain_retrieval("heart failure symptoms")

for result in explanation["results"]:
    print(f"Rank {result['rank']}: {result['source']}")
    print(f"  Score: {result['score']:.4f}")
    print()

# Get answer
response = engine.query("heart failure symptoms", use_llm=True)
print(f"Answer: {response['answer']}")
```

### Filtered Search by Source
```python
retriever = get_advanced_retriever()

# Search only in specific file
results = retriever.search_by_source(
    "heart failure treatment",
    source_file="www.msdvetmanual.com__cardiology.txt"
)
```

### Search by Content Type
```python
# Find table data specifically
table_results = retriever.search_by_chunk_type(
    "drug dosage",
    chunk_type="table"
)

# Find text sections
text_results = retriever.search_by_chunk_type(
    "treatment guidelines",
    chunk_type="text"
)
```

---

## ⚙️ Configuration Quick Tips

### Change Embedding Model (Faster)
In `chatbot/rag/config.py`:
```python
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"  # Faster, less accurate
```

### Change Chunk Size
```python
MAX_TOKENS = 256        # Smaller chunks, more granular
MAX_TOKENS = 1024       # Larger chunks, broader context
```

### Change Retrieval Results
```python
SIMILARITY_TOP_K = 3    # Fewer, faster results
SIMILARITY_TOP_K = 10   # More comprehensive
```

---

## 🧪 Testing & Debugging

### View Collection Statistics
```bash
python chatbot/scripts/ingest_documents.py --stats
```

### Test Retriever
```bash
python chatbot/scripts/test_rag_pipeline.py
```

### Manual Test in Python
```python
from chatbot.rag.retriever import get_advanced_retriever

retriever = get_advanced_retriever()

# Check if index loaded
if retriever.semantic_retriever:
    print("✓ Index loaded")
    results = retriever.search("test query")
    print(f"✓ Found {len(results)} results")
else:
    print("✗ No index available")
    print("  Run: python chatbot/scripts/ingest_documents.py")
```

---

## 🔄 Ingestion Tips

### Add New PDFs
1. Place PDF files in `chatbot/raw_pdfs/`
2. Run: `python chatbot/scripts/ingest_documents.py --pdfs`

### Reindex Everything
```bash
# Clear old index
python -c "
from chatbot.rag.retriever import get_advanced_retriever
r = get_advanced_retriever()
r.vector_store_manager.clear_collection()
"

# Rebuild
python chatbot/scripts/ingest_documents.py
```

### Check Ingestion Progress
```bash
# Monitor while running
python chatbot/scripts/ingest_documents.py --markdown
```

---

## 📊 Understanding Results

### Result Structure
```python
{
    "content": "The actual chunk text...",
    "score": 0.85,                          # 0-1, higher is better
    "source": "filename.txt",               # Where it came from
    "chunk_id": "uuid-string",              # Unique ID
    "chunk_type": "text|table|code",        # What kind of content
    "metadata": {                           # Rich metadata
        "section": "Cardiology",
        "heading_hierarchy": "H1 > H2 > H3",
        "url": "https://example.com/page"
    }
}
```

### Interpreting Scores
- **0.9+** - Excellent match
- **0.8-0.9** - Very good match
- **0.7-0.8** - Good match
- **0.6-0.7** - Decent match
- **<0.6** - Weak match

---

## 🐛 Troubleshooting

### "No index available"
```bash
# Solution: Ingest documents first
python chatbot/scripts/ingest_documents.py
```

### "Slow queries"
```python
# Solution: Reduce top_k
results = retriever.search(query, top_k=3)  # Instead of 5

# Or use metadata filters to narrow search
results = retriever.search_by_source(query, source_file="specific.txt")
```

### "Out of memory"
```python
# Solution: Reduce BATCH_SIZE in config.py
BATCH_SIZE = 16  # Instead of 32
```

### "Missing documents after ingestion"
```bash
# Check stats
python chatbot/scripts/ingest_documents.py --stats

# Verify directories exist
ls chatbot/raw_pdfs/         # PDFs here
ls chatbot/rag_output_cleaned/  # Markdown here
```

---

## 🎯 Advanced Features

### Explain Why Documents Were Retrieved
```python
query_engine = RAGQueryEngine(retriever.semantic_retriever, llm=llm)
explanation = query_engine.explain_retrieval("your query")

# Shows rank, score, source, content preview, metadata for each result
```

### Get Context Only (Without LLM)
```python
retriever = get_advanced_retriever()
context = retriever.get_context("your query", top_k=5)
# Returns combined text of top 5 chunks
```

### Search with Multiple Metadata Filters
```python
results = retriever.search_with_metadata(
    "heart failure",
    filters={
        "source_type": "markdown",
        "chunk_type": "table"
    },
    top_k=5
)
```

---

## 📁 Key Files to Know

| File | Purpose | When to Edit |
|------|---------|--------------|
| `config.py` | Settings | Embedding model, chunk size, paths |
| `ingestion/pipeline.py` | Main pipeline | Add new document types |
| `retrieval/retriever.py` | Search logic | Add new search modes |
| `qa.py` | QA integration | Add preprocessing/postprocessing |

---

## 🚀 Performance Notes

### Embedding Speed
- ~200 embeddings/second (GPU)
- ~20 embeddings/second (CPU)

### Search Speed
- ~100-200ms per query (index of 1000+ chunks)
- Faster with smaller `top_k`
- Faster with metadata filters

### Storage
- ~2GB for 10,000 chunks with BAAI/bge-small
- ~3-4GB with larger embedding model

---

## 🔗 Integration Points

### With FastAPI
```python
from fastapi import FastAPI
from chatbot.rag.qa import ask_rag

app = FastAPI()

@app.post("/ask")
async def ask(question: str):
    answer = ask_rag(question)
    return {"answer": answer}
```

### With Chatbot Agent
```python
from chatbot.rag.retriever import get_advanced_retriever

retriever = get_advanced_retriever()

def get_context(query):
    results = retriever.search(query, top_k=5)
    return "\n".join([r["content"] for r in results])

# Use in your agent tools
```

### With Existing Code
```python
# Your existing code - no changes needed!
from chatbot.rag.qa import ask_rag

answer = ask_rag("question")  # Uses new pipeline if available
```

---

## ✨ Tips & Tricks

### Test Different Queries
```python
test_queries = [
    "heart disease symptoms",
    "drug treatment options",
    "surgical procedures",
]

for query in test_queries:
    results = retriever.search(query, top_k=3)
    print(f"Query: {query}")
    print(f"Found: {len(results)} results")
    print()
```

### Monitor Retrieval Quality
```python
# Track average scores
results = retriever.search(query, top_k=10)
avg_score = sum(r["score"] for r in results) / len(results)
print(f"Average relevance: {avg_score:.4f}")

# Look for document diversity
sources = set(r["source"] for r in results)
print(f"Sources used: {len(sources)}")
```

### Debug Metadata
```python
results = retriever.search(query, top_k=1)
import json
print(json.dumps(results[0]["metadata"], indent=2))
```

---

## 📚 Learn More

- Full guide: `ADVANCED_RAG_PIPELINE.md`
- Implementation details: `IMPLEMENTATION_SUMMARY.md`
- API reference: See docstrings in source files
- Examples: `chatbot/scripts/test_rag_pipeline.py`

---

## 🎉 You're Ready!

Start using the advanced RAG pipeline:
```bash
python chatbot/scripts/ingest_documents.py
python chatbot/scripts/test_rag_pipeline.py
```

Then integrate into your application and enjoy production-level semantic retrieval! 🚀
