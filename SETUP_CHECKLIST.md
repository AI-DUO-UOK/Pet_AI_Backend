# Setup Checklist - Before You Run

Follow this checklist to ensure everything is configured correctly.

## Backend Setup Checklist

### Environment Setup
- [ ] Python 3.11+ installed (`python --version`)
- [ ] Virtual environment created and activated (`.venv/`)
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file exists in `Pet_AI_Backend/` directory
- [ ] `.env` contains `OPENROUTER_API_KEY`
- [ ] `.env` contains `LANGCHAIN_API_KEY`
- [ ] `.env` contains `LANGCHAIN_TRACING_V2=true`

### Backend Files
- [ ] `chatbot/api.py` exists (new FastAPI file)
- [ ] `chatbot/main.py` still exists (CLI unchanged)
- [ ] `chatbot/rag/` directory exists with all files
- [ ] `chatbot/memory.py` exists
- [ ] `chatbot/llm.py` exists
- [ ] `chatbot/tools.py` exists
- [ ] `requirements.txt` has fastapi and uvicorn

### Verify Backend Ready
```bash
# Run this command - should show no errors
python -c "from chatbot.api import app; print('✅ Backend ready')"
```

## Frontend Setup Checklist

### Environment Setup
- [ ] Node.js 18+ installed (`node --version`)
- [ ] npm 9+ installed (`npm --version`)
- [ ] `.env.local` file exists in `Pet_AI_Frontend/` directory
- [ ] `.env.local` contains `NEXT_PUBLIC_API_URL=http://localhost:8000`
- [ ] `node_modules/` directory exists or npm dependencies installed

### Frontend Files
- [ ] `app/(dashboard)/ai-assistant/page.tsx` updated (with API integration)
- [ ] Updated file imports `Upload` and `Loader` from lucide-react
- [ ] Updated file has pet selection logic
- [ ] Updated file calls API endpoints

### Verify Frontend Ready
```bash
# Run this command - should show no errors
npm --version  # Shows npm version
```

## Port Availability Checklist

### Check Ports Not In Use
```bash
# Check port 8000 (backend)
lsof -i :8000
# Should show: nothing (or "not found" error)

# Check port 3000 (frontend)
lsof -i :3000
# Should show: nothing (or "not found" error)
```

If ports are in use:
- [ ] Kill existing processes
- [ ] Or use different ports

## File Changes Summary

### Created Files
- [ ] `Pet_AI_Backend/chatbot/api.py` - NEW API wrapper
- [ ] `Pet_AI_Backend/API_SETUP.md` - NEW documentation
- [ ] `Pet_AI_Backend/INTEGRATION_COMPLETE.md` - NEW guide
- [ ] `Pet_AI_Backend/QUICK_START.md` - NEW quick reference
- [ ] `Pet_AI_Backend/SETUP_CHECKLIST.md` - This file
- [ ] `Pet_AI_Frontend/.env.local` - NEW config file
- [ ] `Pet_AI_Frontend/FRONTEND_SETUP.md` - NEW documentation

### Updated Files
- [ ] `Pet_AI_Frontend/app/(dashboard)/ai-assistant/page.tsx` - UPDATED

### Unchanged Files (Verify All Still Exist)
- [ ] `Pet_AI_Backend/chatbot/main.py` - Still there, unchanged
- [ ] `Pet_AI_Backend/chatbot/rag/agentic_rag.py` - Still there, unchanged
- [ ] `Pet_AI_Backend/chatbot/memory.py` - Still there, unchanged
- [ ] `Pet_AI_Backend/chatbot/llm.py` - Still there, unchanged
- [ ] `Pet_AI_Backend/chatbot/tools.py` - Still there, unchanged
- [ ] All other backend files - Should be unchanged
- [ ] All other frontend files - Should be unchanged

## Configuration Verification

### Backend Configuration
```python
# Verify in Pet_AI_Backend/chatbot/api.py:

# ✓ FastAPI app created
app = FastAPI(...)

# ✓ CORS enabled
CORSMiddleware(allow_origins=["*"], ...)

# ✓ Session manager created
session_manager = SessionManager()

# ✓ Endpoints defined
@app.post("/api/sessions")
@app.post("/api/sessions/{session_id}/chat")
# etc.
```

### Frontend Configuration
```typescript
// Verify in Pet_AI_Frontend/app/(dashboard)/ai-assistant/page.tsx:

// ✓ API_URL configured
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ✓ Pet selection state
const [selectedPet, setSelectedPet] = useState<'dog' | 'cat' | null>(null);

// ✓ Session management
const [sessionId, setSessionId] = useState<string | null>(null);

// ✓ API calls present
fetch(`${API_URL}/api/sessions`, ...)
```

## Dependencies Check

### Backend Dependencies
```bash
pip list | grep -E "fastapi|uvicorn|langchain|llama-index|chromadb"
```

Should show:
- [ ] fastapi
- [ ] uvicorn
- [ ] langchain
- [ ] llama-index (or llamaindex)
- [ ] chromadb

### Frontend Dependencies
```bash
npm list | grep -E "lucide-react|framer-motion|next"
```

Should show:
- [ ] lucide-react
- [ ] framer-motion
- [ ] next

## API Key Verification

### Test OpenRouter Connection
```bash
cd Pet_AI_Backend

# Check if key is loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); \
print('✓ OPENROUTER_API_KEY' if os.getenv('OPENROUTER_API_KEY') else '✗ Missing')"
```

Should output: `✓ OPENROUTER_API_KEY`

### Test LangChain Key
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); \
print('✓ LANGCHAIN_API_KEY' if os.getenv('LANGCHAIN_API_KEY') else '✗ Missing')"
```

Should output: `✓ LANGCHAIN_API_KEY`

## Quick Validation Script

Save as `validate_setup.sh`:

```bash
#!/bin/bash

echo "🔍 Validating Pet AI Setup..."
echo ""

# Check Python
echo "Checking Python..."
python --version > /dev/null 2>&1 && echo "✓ Python found" || echo "✗ Python not found"

# Check Node
echo "Checking Node.js..."
node --version > /dev/null 2>&1 && echo "✓ Node found" || echo "✗ Node not found"

# Check backend env
echo "Checking backend .env..."
[ -f Pet_AI_Backend/.env ] && echo "✓ Backend .env found" || echo "✗ Backend .env missing"

# Check frontend env
echo "Checking frontend .env.local..."
[ -f Pet_AI_Frontend/.env.local ] && echo "✓ Frontend .env.local found" || echo "✗ Frontend .env.local missing"

# Check API file
echo "Checking API file..."
[ -f Pet_AI_Backend/chatbot/api.py ] && echo "✓ API file found" || echo "✗ API file missing"

# Check frontend component
echo "Checking frontend component..."
[ -f Pet_AI_Frontend/app/\(dashboard\)/ai-assistant/page.tsx ] && \
echo "✓ Frontend component found" || echo "✗ Frontend component missing"

# Check ports
echo "Checking ports..."
! lsof -i :8000 > /dev/null 2>&1 && echo "✓ Port 8000 available" || echo "⚠ Port 8000 in use"
! lsof -i :3000 > /dev/null 2>&1 && echo "✓ Port 3000 available" || echo "⚠ Port 3000 in use"

echo ""
echo "✅ Setup validation complete!"
```

Run it:
```bash
chmod +x validate_setup.sh
./validate_setup.sh
```

## Pre-Run Testing

### Test Backend Imports
```bash
cd Pet_AI_Backend
python -c "
from chatbot.api import app, session_manager
from chatbot.rag.agentic_rag import query_agentic_rag
from chatbot.memory import ConversationMemory
print('✅ All imports successful')
"
```

### Test Frontend Components
```bash
cd Pet_AI_Frontend
npm ls | head -20
```

Should show dependency tree without errors.

## Manual Port Check

### Port 8000 (Backend)
```bash
# If you see output, port is in use
lsof -i :8000

# Kill if needed
kill -9 <PID>
```

### Port 3000 (Frontend)
```bash
# If you see output, port is in use
lsof -i :3000

# Kill if needed
kill -9 <PID>
```

## Final Verification

Before running, check all these are ✓:

- [ ] Python & Node installed
- [ ] `.env` files configured in both backend and frontend
- [ ] API dependencies installed
- [ ] Frontend dependencies installed
- [ ] API file exists at `chatbot/api.py`
- [ ] Frontend component updated with API calls
- [ ] Ports 3000 and 8000 are free
- [ ] No error messages from validation script

## Troubleshooting Pre-Run Issues

| Issue | Check |
|-------|-------|
| "No module named fastapi" | `pip install fastapi uvicorn` |
| "Cannot find Node modules" | `cd Pet_AI_Frontend && npm install` |
| "Port already in use" | Kill process using `lsof -i :<port> && kill -9 <PID>` |
| ".env not found" | Create `.env` in Pet_AI_Backend with API keys |
| ".env.local not found" | Create `.env.local` in Pet_AI_Frontend with API URL |

## You're Ready When:

✅ All checkboxes above are checked
✅ Validation script shows all green ✓
✅ No error messages
✅ Ports are free
✅ Files are in place
✅ Configuration files are complete

## Next Step

Once all items are checked, proceed to [QUICK_START.md](./QUICK_START.md) to run the application.

---

**Last Verified**: Check this date to ensure your setup is current
- [ ] Backend files verified
- [ ] Frontend files verified
- [ ] Environment variables verified
- [ ] Dependencies verified
- [ ] Ready to run!
