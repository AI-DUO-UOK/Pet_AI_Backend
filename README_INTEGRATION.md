# Pet AI - Frontend & Backend Integration Guide

Complete guide for understanding, setting up, and running the integrated Pet AI system.

## 📋 Documentation Map

Start here based on what you need:

### 🚀 **Want to Run It Now?**
1. Read: [QUICK_START.md](./QUICK_START.md) (2 minutes)
2. Follow: [SETUP_CHECKLIST.md](./SETUP_CHECKLIST.md) (5 minutes)
3. Run: Both services and test

### 📚 **Want to Understand It?**
1. Read: [INTEGRATION_COMPLETE.md](./INTEGRATION_COMPLETE.md) (15 minutes)
2. Review: Architecture section below
3. Check: API and Frontend documentation

### 🔧 **Need Technical Details?**
- **Backend API**: [API_SETUP.md](./API_SETUP.md)
- **Frontend Setup**: [../Pet_AI_Frontend/FRONTEND_SETUP.md](../Pet_AI_Frontend/FRONTEND_SETUP.md)
- **Full Integration**: [INTEGRATION_COMPLETE.md](./INTEGRATION_COMPLETE.md)

### 🐛 **Something Not Working?**
1. Check: [SETUP_CHECKLIST.md](./SETUP_CHECKLIST.md) - verification section
2. Read: Troubleshooting in [QUICK_START.md](./QUICK_START.md)
3. Review: API docs at http://localhost:8000/docs (when running)

---

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│            USER (Browser)                               │
│         http://localhost:3000                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                ┌──────▼──────┐
                │  FRONTEND   │
                │ (Next.js 15)│
                │   Port 3000 │
                └──────┬──────┘
                       │
        REST API       │       JSON
        HTTP/HTTPS     │
                       │
        ┌──────────────▼──────────────┐
        │  BACKEND API                │
        │  (FastAPI)                  │
        │  Port 8000                  │
        │  /api/sessions              │
        │  /api/sessions/{id}/chat    │
        └──────────────┬──────────────┘
                       │
        Direct Python  │  Function Calls
        Function Calls │
                       │
        ┌──────────────▼──────────────────────┐
        │  EXISTING CHATBOT LOGIC (UNCHANGED) │
        │                                      │
        │  ✓ Agentic RAG System               │
        │  ✓ Conversation Memory              │
        │  ✓ LLM Integration (OpenRouter)     │
        │  ✓ CV Model Analysis                │
        │  ✓ Prompt Templates                 │
        │  ✓ All Original Features            │
        └──────────────┬──────────────────────┘
                       │
        ┌──────────────▼──────────────────────┐
        │  EXTERNAL SERVICES                  │
        │                                      │
        │  • OpenRouter API (LLM)             │
        │  • ChromaDB (Vector Store)          │
        │  • HuggingFace (Embeddings)         │
        └──────────────────────────────────────┘
```

### Data Flow Example

```
User Types: "My dog is limping"
          │
          ▼
Frontend  → POST /api/sessions/{sessionId}/chat
          │
          │ {content: "My dog is limping"}
          │
          ▼
Backend   → Session Manager
          │
          ├─ Extract pet type: "dog"
          ├─ Detect disease type: "limping"
          ├─ Get conversation context
          │
          ▼
Backend   → Agentic RAG System
          │
          ├─ LLM decides: "Use knowledge base"
          ├─ Search ChromaDB for relevant docs
          ├─ Format retrieved context
          │
          ▼
Backend   → LLM (OpenRouter)
          │
          ├─ Generate response with analysis
          ├─ Parse confidence scores
          │
          ▼
Backend   → Response with Analysis Data
          │
          │ {
          │   message: "...",
          │   is_analysis: true,
          │   analysis_data: {
          │     condition: "Possible Sprain",
          │     confidence: 85,
          │     actions: [...],
          │     dos: [...],
          │     donts: [...]
          │   }
          │ }
          │
          ▼
Frontend  → Display Formatted Response
          │
          ├─ Show message text
          ├─ Show analysis card if present
          ├─ Display confidence %
          ├─ List actions/dos/donts
          │
          ▼
User Sees → Formatted AI Response
```

---

## 📂 Project Structure

### Backend Structure

```
Pet_AI_Backend/
├── chatbot/
│   ├── api.py ✨ NEW - FastAPI wrapper
│   ├── main.py - CLI chatbot (unchanged)
│   ├── llm.py - LLM config (unchanged)
│   ├── memory.py - Conversation memory (unchanged)
│   ├── prompts.py - Prompt templates (unchanged)
│   ├── agent.py - LangChain agent (unchanged)
│   ├── tools.py - CV tools (unchanged)
│   ├── langsmith_config.py (unchanged)
│   │
│   ├── rag/
│   │   ├── agentic_rag.py - Intelligent routing (unchanged)
│   │   ├── retriever.py - Semantic search (unchanged)
│   │   ├── qa.py - Q&A pipeline (unchanged)
│   │   ├── ingest.py - Document ingestion (unchanged)
│   │   ├── cleaner.py - Data cleaning (unchanged)
│   │   ├── crawler.py - Web crawler (unchanged)
│   │   └── test_retriever.py - Tests (unchanged)
│   │
│   ├── db/
│   │   └── chroma.sqlite3 - Vector store (unchanged)
│   │
│   ├── rag_output/ - Crawled data (unchanged)
│   └── rag_output_cleaned/ - Cleaned data (unchanged)
│
├── app/
│   ├── main.py - FastAPI CV server (unchanged)
│   ├── models/ - ML models (unchanged)
│   └── services/ - Services (unchanged)
│
├── weights/ - Model weights (unchanged)
├── sample_images/ - Test images (unchanged)
│
├── requirements.txt - Dependencies (updated, no breaking changes)
├── .env - API keys (you provide)
│
├── API_SETUP.md ✨ NEW - API documentation
├── INTEGRATION_COMPLETE.md ✨ NEW - Full guide
├── QUICK_START.md ✨ NEW - Quick reference
├── SETUP_CHECKLIST.md ✨ NEW - Setup validation
└── README.md (original)
```

### Frontend Structure

```
Pet_AI_Frontend/
├── app/
│   ├── (dashboard)/
│   │   ├── ai-assistant/
│   │   │   └── page.tsx ✨ UPDATED - Now uses API
│   │   ├── dashboard/
│   │   ├── my-pets/
│   │   ├── find-vets/
│   │   ├── layout.tsx
│   │   └── vet/ (vet pages)
│   │
│   ├── auth/
│   │   ├── login/
│   │   ├── signup/
│   │   └── select-role/
│   │
│   ├── layout/
│   │   └── dashboardlayout.tsx
│   │
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   └── TopNavbar.tsx
│   └── ui/
│       ├── PetCard.tsx
│       └── NotificationDropdown.tsx
│
├── contexts/
│   ├── AuthContext.tsx
│   └── ThemeContext.tsx
│
├── .env.local ✨ NEW - API URL config
├── middleware.ts
├── next.config.ts
├── tsconfig.json
├── tailwind.config.js
├── postcss.config.js
│
├── FRONTEND_SETUP.md ✨ NEW - Frontend guide
├── FILE_STRUCTURE_GUIDE.md
└── README.md
```

---

## 🔄 Integration Points

### What Changed

#### ✅ Created Files
- `chatbot/api.py` - New REST API wrapper
- Documentation files (4 new .md files)
- `.env.local` - Frontend configuration

#### ✅ Updated Files
- `app/(dashboard)/ai-assistant/page.tsx` - Now connects to backend API

#### ❌ Unchanged Files
- **All RAG files** - Same agentic routing
- **All Memory files** - Same persistence
- **All LLM files** - Same OpenRouter integration
- **All CV files** - Same model analysis
- **CLI chatbot** - Still works via `python -m chatbot.main`
- **All other backend files** - Completely unchanged
- **All other frontend files** - Completely unchanged

### Why No Breaking Changes

The API layer is a **thin wrapper** that:
1. Receives HTTP requests from frontend
2. Creates session objects
3. Calls existing Python functions
4. Returns responses as JSON

**No logic is modified** - All business logic stays the same!

---

## 🚀 Getting Started

### Quickest Path (5 minutes)

1. **Verify Prerequisites**
   ```bash
   python --version  # Should be 3.11+
   node --version    # Should be 18+
   ```

2. **Check Configuration**
   ```bash
   # Backend
   [ -f Pet_AI_Backend/.env ] && echo "✓ .env exists" || echo "✗ Need .env"
   
   # Frontend
   [ -f Pet_AI_Frontend/.env.local ] && echo "✓ .env.local exists" || echo "✗ Need .env.local"
   ```

3. **Run Backend**
   ```bash
   cd Pet_AI_Backend
   python -m uvicorn chatbot.api:app --reload --host 0.0.0.0 --port 8000
   # Wait for: "Uvicorn running on http://0.0.0.0:8000"
   ```

4. **Run Frontend (new terminal)**
   ```bash
   cd Pet_AI_Frontend
   npm run dev
   # Wait for: "Local: http://localhost:3000"
   ```

5. **Test**
   - Open http://localhost:3000
   - Go to AI Assistant
   - Click "🐕 dog" or "🐱 cat"
   - Send a message
   - Should get real AI response

### Detailed Path (15 minutes)

Follow [SETUP_CHECKLIST.md](./SETUP_CHECKLIST.md) step by step.

---

## 🎯 Key Features

### Frontend Features
- 🐕 Pet type selection (dog/cat)
- 💬 Real-time chat interface
- 🖼️ Image upload button (ready for integration)
- ⚡ Loading states
- ❌ Error handling with messages
- 📝 Suggested prompts
- 🎨 Beautiful responsive UI
- 🌙 Dark mode support

### Backend Features
- 🔄 Session management
- 💾 Conversation memory
- 🧠 Agentic RAG routing
- 📚 ChromaDB vector search
- 🤖 LLM integration (OpenRouter)
- 🐕 Pet-specific CV analysis
- 📊 Structured response parsing
- 🔐 API key management

---

## 📡 API Endpoints

All endpoints documented at: http://localhost:8000/docs (when running)

### Core Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/sessions` | Create chat session |
| GET | `/api/sessions/{id}` | Get session info |
| POST | `/api/sessions/{id}/chat` | Send message |
| POST | `/api/sessions/{id}/analyze-image` | Analyze pet image |
| DELETE | `/api/sessions/{id}` | End session |
| GET | `/api/health` | Health check |

### Example: Create Session

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"pet_type": "dog"}'

# Returns:
# {
#   "session_id": "550e8400-e29b-41d4-a716-446655440000",
#   "pet_type": "dog",
#   "messages_count": 0
# }
```

### Example: Send Message

```bash
curl -X POST http://localhost:8000/api/sessions/550e8400-e29b-41d4-a716-446655440000/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "My dog is limping"}'

# Returns:
# {
#   "message": "Based on your description...",
#   "is_analysis": true,
#   "analysis_data": {
#     "condition": "Possible Sprain",
#     "confidence": 85,
#     "actions": [...],
#     "dos": [...],
#     "donts": [...]
#   }
# }
```

---

## 🔍 How to Debug

### Backend Issues

1. **Check API is Running**
   ```bash
   curl http://localhost:8000/api/health
   # Should return: {"status": "healthy"}
   ```

2. **Check API Logs**
   - Look at terminal where uvicorn is running
   - Errors will show with traceback

3. **Use Swagger UI**
   - http://localhost:8000/docs
   - Test endpoints interactively

4. **Check Dependencies**
   ```bash
   pip list | grep -E "fastapi|uvicorn|langchain"
   ```

### Frontend Issues

1. **Check Network**
   - Press F12 in browser
   - Go to Network tab
   - Send message
   - Look for API calls to localhost:8000

2. **Check Console**
   - Press F12
   - Go to Console tab
   - Look for error messages

3. **Check Environment**
   ```bash
   grep NEXT_PUBLIC_API_URL .env.local
   # Should show: NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

---

## 📚 Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| [QUICK_START.md](./QUICK_START.md) | Get running in 5 min | Everyone |
| [SETUP_CHECKLIST.md](./SETUP_CHECKLIST.md) | Verify setup complete | First-time setup |
| [INTEGRATION_COMPLETE.md](./INTEGRATION_COMPLETE.md) | Understand architecture | Developers |
| [API_SETUP.md](./API_SETUP.md) | Backend API details | Backend devs |
| [../Pet_AI_Frontend/FRONTEND_SETUP.md](../Pet_AI_Frontend/FRONTEND_SETUP.md) | Frontend details | Frontend devs |

---

## ✅ Verification Checklist

Before running, verify:

- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] Backend .env exists with API keys
- [ ] Frontend .env.local exists with API URL
- [ ] `chatbot/api.py` exists in backend
- [ ] Frontend AI Assistant component is updated
- [ ] Dependencies installed (pip and npm)
- [ ] Ports 3000 and 8000 are free
- [ ] No errors from validation script

---

## 🎓 Learning Path

New to the system? Follow this order:

1. **Read**: This document (you're reading it!)
2. **Run**: [QUICK_START.md](./QUICK_START.md)
3. **Understand**: [INTEGRATION_COMPLETE.md](./INTEGRATION_COMPLETE.md)
4. **Explore**: API docs at http://localhost:8000/docs
5. **Dive Deep**: Backend [API_SETUP.md](./API_SETUP.md) + Frontend [FRONTEND_SETUP.md](../Pet_AI_Frontend/FRONTEND_SETUP.md)

---

## 🆘 Need Help?

| Issue | Solution |
|-------|----------|
| "Port in use" | Kill process: `kill -9 $(lsof -t -i:8000)` |
| "Module not found" | Install dependencies: `pip install -r requirements.txt` |
| "API not responding" | Check backend is running and ports are correct |
| "Frontend won't load" | Check .env.local has correct API_URL |
| "Can't find files" | Check file paths match examples |

---

## 🚢 Production Deployment

When ready to deploy:

1. **Backend**
   - Use production-grade server (Gunicorn, etc.)
   - Update CORS to specific domains
   - Add authentication/authorization
   - Use environment-based configuration
   - See [API_SETUP.md](./API_SETUP.md#production-deployment)

2. **Frontend**
   - Build: `npm run build`
   - Deploy to static host (Vercel, Netlify, etc.)
   - Update NEXT_PUBLIC_API_URL to production API
   - See [../Pet_AI_Frontend/FRONTEND_SETUP.md](../Pet_AI_Frontend/FRONTEND_SETUP.md#building-for-production)

---

## 📞 Support Resources

- **API Documentation**: http://localhost:8000/docs (interactive)
- **Backend Guide**: [API_SETUP.md](./API_SETUP.md)
- **Frontend Guide**: [../Pet_AI_Frontend/FRONTEND_SETUP.md](../Pet_AI_Frontend/FRONTEND_SETUP.md)
- **Troubleshooting**: [QUICK_START.md](./QUICK_START.md#troubleshooting-in-30-seconds)
- **Logs**: Check terminal output where services run

---

## 🎉 You're Ready!

Everything is set up for you to:
- ✅ Run frontend and backend together
- ✅ Chat with real AI powered by the backend
- ✅ See intelligent RAG responses
- ✅ Upload pet images (ready for integration)
- ✅ Deploy to production
- ✅ Scale to multiple users

**Next Step**: Open [QUICK_START.md](./QUICK_START.md) and start running! 🚀
