# Full RAG Pipeline Implementation

## Overview

We have successfully implemented a **complete Retrieval-Augmented Generation (RAG) pipeline** that:

1. **Retrieves** semantically relevant chunks from vector database
2. **Filters** by confidence threshold for quality control
3. **Augments** the prompt with retrieved context
4. **Generates** answers using an LLM with knowledge grounding
5. **Falls back** gracefully to general knowledge when needed

## Architecture

```
User Query
    ↓
[Step 1] Semantic Retrieval
    ├─ Advanced retriever searches vector DB
    ├─ Returns top-k chunks with similarity scores (0-1)
    └─ Example scores: [0.82, 0.76, 0.41, 0.35, ...]
    ↓
[Step 2] Confidence Filtering
    ├─ Filter chunks by threshold (default: 0.65)
    ├─ Keep only high-quality matches
    └─ Example: Keep [0.82, 0.76], discard [0.41, 0.35]
    ↓
[Step 3] Context Building
    ├─ Combine filtered chunks into single context string
    └─ Example output: "...\n\n...\n\n..."
    ↓
[Step 4] Prompt Construction
    ├─ Insert context into system prompt
    ├─ Include user question
    └─ Provide instruction to use context
    ↓
[Step 5] LLM Inference
    ├─ Send augmented prompt to language model
    ├─ LLM grounds answer in provided context
    └─ Generate response
    ↓
Final Answer
```

## Key Components

### 1. Semantic Retriever
**File**: `chatbot/rag/retriever.py` → `AdvancedRetriever.search()`

```python
results = retriever.search(
    query="What causes dermatitis in dogs?",
    top_k=5
)

# Returns:
[
    {
        "content": "Dermatitis is skin inflammation...",
        "score": 0.82,  # Similarity score
        "source": "www.msdvetmanual.com__dog-skin",
        "chunk_type": "text",
        "chunk_id": 42,
        "metadata": {...}
    },
    ...
]
```

### 2. Confidence Filtering
**File**: `chatbot/rag/qa.py` → `ask_rag()` function

```python
# Filter by confidence threshold
filtered_results = [
    r for r in results 
    if r["score"] > 0.65
]

# Before: 5 results
# After: 3 results (only high confidence)
```

**Why This Matters**:
- Scores < 0.65 = weak matches, potentially misleading
- Scores > 0.65 = strong semantic alignment with query
- Prevents LLM from being confused by irrelevant chunks

### 3. Context Building
**File**: `chatbot/rag/qa.py` → `ask_rag()` function

```python
context = "\n\n".join([
    r["content"] for r in filtered_results
])

# Result:
"""
Dermatitis is inflammation of the skin...

Common causes in dogs include allergies...

Treatment options vary depending on cause...
"""
```

### 4. Prompt Template
**File**: `chatbot/rag/qa.py` → `ask_rag()` function

**With Context** (when high-confidence chunks exist):
```
You are a helpful veterinary AI assistant.

Use the following context to answer the question as accurately as possible.

Context:
{retrieved_context}

Question:
{user_question}

Answer:
```

**Without Context** (fallback):
```
You are a helpful veterinary AI assistant.

Answer the following question using your general knowledge.

Question:
{user_question}

Answer:
```

### 5. LLM Answer Generation
**File**: `chatbot/llm.py`

```python
response = llm.invoke(augmented_prompt)
answer = response.content
```

The LLM sees:
- User question
- Retrieved context
- Instruction to answer using context

## Configuration

### Confidence Threshold
**Default**: 0.65 (65% semantic similarity)
**Location**: `chatbot/rag/qa.py`

```python
CONFIDENCE_THRESHOLD = 0.65
```

**Tuning Guide**:
- `0.80+`: Very strict, may miss relevant context
- `0.65`: Balanced (recommended)
- `0.50`: Lenient, may include noise
- `0.00`: Accept all results

### Top-K Retrieval
**Default**: 5 chunks
**Location**: `ask_rag()` parameter

```python
answer = ask_rag(question, top_k=5)
```

**Tuning Guide**:
- `3-5`: Fast, focused context
- `10-15`: Broader coverage
- `>20`: Risk of noise

## Usage Examples

### Example 1: Basic Query
```python
from chatbot.rag.qa import ask_rag

answer = ask_rag("What causes dermatitis in dogs?")
print(answer)

# Output:
# "Dermatitis in dogs is commonly caused by allergies,
#  parasites, infections, or environmental irritants.
#  The most common cause is allergic dermatitis..."
```

### Example 2: Custom Threshold
```python
# More strict filtering (only very confident matches)
answer = ask_rag(
    "Dog ear infections",
    confidence_threshold=0.75
)
```

### Example 3: With More Context
```python
# Retrieve more chunks for complex topics
answer = ask_rag(
    "Feline diabetes management",
    top_k=10  # Get 10 chunks instead of 5
)
```

## Testing the Pipeline

### Run Full RAG Test
```bash
python chatbot/scripts/test_rag_qa.py
```

This will:
1. Ask 4 different veterinary questions
2. Show retrieval process
3. Display LLM-generated answers
4. Log confidence filtering details

### Test Individual Components
```bash
# Test just retrieval
python chatbot/rag/test_retriever.py

# Test legacy retriever
from chatbot.rag.retriever import get_retriever
retriever = get_retriever()
docs = retriever.invoke("Your question")
```

## Logging

The RAG pipeline provides detailed logging:

```
INFO - Retrieving top 5 chunks using advanced RAG
DEBUG - Including chunk: www.msd...dog-skin (type: text, score: 0.821)
DEBUG - Including chunk: www.pet...dermatitis (type: text, score: 0.754)
INFO - Built context from 2 chunks
INFO - Sending prompt to LLM for answer generation
INFO - Generated answer (487 chars)
```

## Fallback Behavior

The system automatically falls back when:

1. **No High-Confidence Matches**
   - All retrieved chunks score < threshold
   - LLM answers using general knowledge
   - Logged as: `"fallback_reason": "low_confidence"`

2. **Advanced Retriever Not Available**
   - Vector index not loaded
   - Falls back to legacy LangChain retriever
   - Logged as: `"fallback_reason": "advanced_not_ready"`

3. **Search Errors**
   - Any retrieval exception caught
   - Returns error message safely
   - Logged with full traceback

## Performance

### Retrieval Phase
- **Time**: ~200-500ms for semantic search
- **Chunks**: 1,415 markdown nodes indexed
- **Vector DB**: ChromaDB with BAAI/bge-small-en-v1.5 embeddings

### Filtering Phase
- **Time**: <10ms (in-memory operation)
- **Typical result**: 2-3 chunks pass confidence threshold

### LLM Phase
- **Time**: 2-10 seconds (streaming response)
- **Model**: Depends on configured LLM

### Total End-to-End
- **Typical**: 5-15 seconds
- **First run**: +2-3s for model downloads

## Best Practices

### 1. Confidence Threshold
✅ DO:
- Start with 0.65 (default)
- Adjust based on query quality
- Monitor fallback rate

❌ DON'T:
- Set too high (> 0.80) → misses context
- Set too low (< 0.50) → noisy results

### 2. Top-K Selection
✅ DO:
- Use 5-10 for most queries
- Increase for complex topics
- Decrease for simple questions

❌ DON'T:
- Use > 20 routinely (slows down LLM)
- Use < 3 (limited context)

### 3. Query Formulation
✅ DO:
- Be specific: "What causes feline urinary infections?"
- Use veterinary terms when known
- Ask one question at a time

❌ DON'T:
- Vague: "Tell me about cats"
- Multi-part: "Causes, symptoms, and treatments of..."
- Off-topic questions

## Future Enhancements

1. **Query Expansion**
   - Expand simple queries to multiple search variants
   - Improve coverage for ambiguous questions

2. **Reranking**
   - Use cross-encoder to rerank top-k results
   - Improve confidence scoring accuracy

3. **Multi-hop Retrieval**
   - Retrieve > 2 levels of related documents
   - Better for complex medical questions

4. **Source Attribution**
   - Show user which documents provided answer
   - Add citations to generated answer

5. **Answer Caching**
   - Cache common question-answer pairs
   - Reduce LLM latency for frequent queries

## Troubleshooting

### No Results Displayed
**Cause**: Chunks not ingested yet
**Fix**: Run ingestion first
```bash
python chatbot/scripts/ingest_documents.py --markdown
```

### Low Confidence Scores (< 0.60)
**Cause**: Query doesn't match indexed content well
**Fix**: 
- Rephrase question
- Lower confidence threshold (temporarily)
- Check ingested documents with `test_retriever.py`

### LLM Timeout
**Cause**: Network issue or overloaded LLM
**Fix**:
- Check LLM endpoint availability
- Reduce top_k to lower token count
- Increase timeout in llm.py

### Out of Memory
**Cause**: Too many chunks loaded
**Fix**:
- Reduce top_k parameter
- Increase confidence_threshold
- Chunk data more aggressively

## References

- [RAG Overview](https://python.langchain.com/docs/use_cases/question_answering/)
- [Semantic Search](https://www.sbert.net/)
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
