# Pet AI Healthcare System - Setup & Testing Guide

## Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment activated
- OpenRouter API key

### Installation

```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installations
pip list | grep -E "langchain|fastapi|torch|pillow|requests"
```

### Environment Setup

```bash
# Create/update .env file
echo "OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE" > .env

# Verify API key is loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key loaded:', bool(os.getenv('OPENROUTER_API_KEY')))"
```

---

## Running the System

### Step 1: Start FastAPI Backend

```bash
# Terminal 1
python -m uvicorn app.main:app --reload --port 8000

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

**Verify API is working:**
```bash
curl http://127.0.0.1:8000/docs  # Should show Swagger UI
```

### Step 2: Start Chatbot

```bash
# Terminal 2
python -m chatbot.main

# Expected output:
# LangChainDeprecationWarning: The function `initialize_agent` was deprecated...
# (This warning is harmless - the agent still works correctly)
#
# 🐾 Pet AI Healthcare Chatbot Started
# ==============================================================
# Welcome! I'm your veterinary assistant.
# ...
# What type of pet do you have? (dog/cat):
```

**Note:** You may see a deprecation warning about `initialize_agent`. This is informational only and doesn't affect functionality. The agent uses `STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION` which properly supports multi-input tools.

---

## Testing Scenarios

### Test 1: General Health Question (No Tool Required)

**Purpose:** Verify chatbot answers directly without using image analysis

```
Input:
  What type of pet: dog
  You: My dog is limping on his back leg and not eating much. What could it be?

Expected:
  ✅ Bot answers directly without asking for image
  ✅ No tool call to /analyze-image
  ✅ Bot provides general diagnostic suggestions
  ✅ Recommends vet consultation

Example Response:
  "Limping combined with loss of appetite could indicate several things..."
```

---

### Test 2: Skin Disease (Tool Required)

**Purpose:** Verify chatbot asks for image when skin issue detected

```
Setup:
  - Have a sample image file ready (e.g., /tmp/dog_skin.jpg)
  - Image should be a dog skin condition

Input:
  What type of pet: dog
  You: My dog has developed a red, scaly rash on his belly. It's itching a lot.

Expected:
  ✅ Bot detects "skin" disease type
  ✅ Bot asks: "Could you please upload an image of your dog's skin?"
  
  You: /tmp/dog_skin.jpg
  
  ✅ Bot calls analyze_pet_image tool
  ✅ FastAPI returns: {"class": "Dermatitis", "confidence": 0.92}
  ✅ Bot explains diagnosis in detail:
     - What dermatitis is
     - Causes
     - Treatment options
     - When to see vet

Example Response:
  "This appears to be Dermatitis (confidence: 92%).
   
   What it is: Dermatitis is inflammation of the skin...
   Causes: Could be due to allergies, parasites, or irritants...
   Treatment: ..."
```

---

### Test 3: Eye Disease (Tool Required)

**Purpose:** Verify chatbot handles eye disease detection and analysis

```
Setup:
  - Have a dog eye image sample (if available)

Input:
  What type of pet: dog
  You: One of my dog's eyes is red and there's discharge coming from it.

Expected:
  ✅ Bot detects "eye" disease type
  ✅ Bot asks for eye image
  
  You: /path/to/eye_image.jpg
  
  ✅ Bot calls analyze_pet_image with disease_type="eye"
  ✅ FastAPI analyzes and returns prediction
  ✅ Bot explains the eye condition thoroughly
```

---

### Test 4: Conversation Memory

**Purpose:** Verify chatbot remembers conversation context

```
Input:
  You: My cat has been sneezing a lot
  Bot: [responds with advice]
  
  You: Should I be worried?
  
Expected:
  ✅ Bot references previous topic (sneezing)
  ✅ Memory includes context from earlier in conversation
  ✅ Response is coherent and context-aware
```

---

### Test 5: Pet Type Selection

**Purpose:** Verify both cat and dog types work

```
Test with cat:
  What type of pet: cat
  You: My cat has a skin issue
  
  ✅ Bot detects skin disease
  ✅ Asks for image
  ✅ Calls tool with animal="cat"
  ✅ Uses cat_skin model

Test with dog:
  What type of pet: dog
  You: My dog's eye is swollen
  
  ✅ Bot detects eye disease
  ✅ Asks for image
  ✅ Calls tool with animal="dog"
  ✅ Uses dog_eye model
```

---

### Test 6: Error Handling

**Purpose:** Verify graceful error handling

```
Test invalid image path:
  You: My dog has a skin rash
  Bot: Please upload an image
  You: /nonexistent/image.jpg
  
  ✅ Tool returns error gracefully
  ✅ Bot handles error and asks to try again

Test API unavailable:
  (Stop FastAPI server)
  You: [ask about skin issue]
  
  ✅ Tool catches connection error
  ✅ Bot informs user about connection issue
```

---

## Debugging Tips

### Check FastAPI Endpoint

```bash
# Test /predict endpoint directly
curl -X POST http://127.0.0.1:8000/predict \
  -F "file=@path/to/image.jpg" \
  -F "animal=dog" \
  -F "disease_type=skin"

# Test /analyze-image endpoint (used by chatbot)
curl -X POST http://127.0.0.1:8000/analyze-image \
  -F "file=@path/to/image.jpg" \
  -F "disease_type=skin" \
  -F "animal=dog"
```

### Test LLM Connection

```bash
python -c "
from chatbot.llm import llm
response = llm.invoke('Say hello')
print(response.content)
"
```

### Test Tool Directly

```bash
python -c "
from chatbot.tools import analyze_pet_image
result = analyze_pet_image('/path/to/image.jpg', 'dog', 'skin')
print(result)
"
```

### Enable Verbose Logging

Add to main.py after agent.run():
```python
# Already enabled with verbose=True in agent.py
# Check console for:
# > Entering new AgentExecutor Executor...
# > Tool: analyze_pet_image
# > Result: {...}
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| [app/main.py](app/main.py) | FastAPI endpoints for image analysis |
| [chatbot/main.py](chatbot/main.py) | CLI chatbot entry point with intent detection |
| [chatbot/agent.py](chatbot/agent.py) | LangChain agent with tool integration |
| [chatbot/tools.py](chatbot/tools.py) | Tool that calls FastAPI for image analysis |
| [chatbot/llm.py](chatbot/llm.py) | LLM configuration (OpenRouter) |
| [chatbot/memory.py](chatbot/memory.py) | Conversation memory |
| [chatbot/prompts.py](chatbot/prompts.py) | System prompts |

---

## Command Reference

### Stop Chatbot
```
You: exit
You: quit  
You: bye

Bot: Goodbye! Take care of your pet! 🐾
```

### View Full Help
```
python -m chatbot.main --help
```

### Run Tests (if any)
```
pytest tests/  # When tests are added
```

---

## Common Issues & Solutions

### Issue: "API key not found"
**Solution:**
```bash
# Verify .env exists and has key
cat .env
# Should show: OPENROUTER_API_KEY=sk-or-v1-...

# If missing:
echo "OPENROUTER_API_KEY=your_key" > .env
```

### Issue: "Connection refused on 127.0.0.1:8000"
**Solution:**
```bash
# Verify FastAPI is running
netstat -an | grep 8000  # or lsof -i :8000

# If not running, start it:
python -m uvicorn app.main:app --reload --port 8000
```

### Issue: "Module not found: langchain"
**Solution:**
```bash
pip install -r requirements.txt
python -c "import langchain; print(langchain.__version__)"
```

### Issue: "Tool is not being called"
**Solution:**
- Check verbose output (enabled by default)
- Verify disease keywords in your question
- Try: "My dog has ringworm" instead of "My dog is sick"
- Check image path format

### Issue: "Image not found"
**Solution:**
- Use absolute path: `/Users/username/image.jpg`
- Or relative to current directory: `image.jpg`
- Make sure file exists and is readable:
  ```bash
  ls -l /path/to/image.jpg
  file /path/to/image.jpg  # Should be image type
  ```

---

## Performance Optimization

### Model Loading Time
First inference takes ~10-15 seconds (model warmup). Subsequent inferences are faster.

### Memory Usage
- Monitor GPU memory: `nvidia-smi`
- Monitor CPU memory: `ps aux | grep python`

### API Rate Limits
- OpenRouter: Check your account limits
- Implement caching for identical images (future enhancement)

---

## Next Steps After Testing

1. ✅ Verify all test scenarios pass
2. ✅ Check verbose output for any warnings
3. 📋 Review conversation flows in production
4. 📊 Implement RAG for medical knowledge base
5. 🎨 Build web UI for image uploads
6. 💾 Add database for diagnosis history

---

## Support Resources

- FastAPI Docs: http://127.0.0.1:8000/docs
- LangChain Docs: https://python.langchain.com
- OpenRouter Docs: https://openrouter.ai/docs
- PyTorch: https://pytorch.org
