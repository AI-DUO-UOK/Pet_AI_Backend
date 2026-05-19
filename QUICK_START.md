# Quick Start Guide - Run Everything Now

## 30-Second Setup

### Prerequisites
- Python 3.11+ with pip
- Node.js with npm
- .env file in Pet_AI_Backend with API keys

## Run Backend

```bash
cd /Users/akilafernando/Documents/GitHub/Pet_AI_Backend
python -m uvicorn chatbot.api:app --reload --host 0.0.0.0 --port 8000
```

**Success**: You'll see `Uvicorn running on http://0.0.0.0:8000`

## Run Frontend

In a NEW terminal:

```bash
cd /Users/akilafernando/Documents/GitHub/Pet_AI_Frontend
npm run dev
```

**Success**: You'll see `Local: http://localhost:3000`

## Test It

1. Open http://localhost:3000 in browser
2. Go to AI Assistant page
3. Click "🐕 dog" or "🐱 cat"
4. Type: "My dog is limping"
5. Hit Enter or click Send
6. Watch for AI response

## Verify Everything Works

### Backend API Docs
Open http://localhost:8000/docs - You should see interactive Swagger UI with all endpoints

### Frontend Connection
- Network tab shows POST to `http://localhost:8000/api/sessions`
- Chat messages show real AI responses (not mock)
- Pet type displays in header

## Stop Services

```bash
# Press Ctrl+C in each terminal
# Or kill by port:
lsof -i :8000  # Find backend
lsof -i :3000  # Find frontend
```

## Troubleshooting in 30 Seconds

| Problem | Solution |
|---------|----------|
| "Port already in use" | Kill existing process: `kill -9 <PID>` |
| "Cannot import docling" | `pip install -r requirements.txt` |
| "Frontend can't reach API" | Check API_URL in `.env.local` |
| "No AI response" | Check OpenRouter API key in backend `.env` |
| "CORS error" | Backend CORS enabled - check browser console |

## What You Should See

### Frontend
- Pet selection screen with dog/cat buttons
- Chat interface after pet selected
- Messages display as they're sent
- AI responses appear with analysis cards
- Suggested prompts on first load

### Backend
- "Session created" messages in console
- "Response generated" messages
- No error messages (errors show in frontend)

## Key Files Modified

✅ **Created:**
- `/chatbot/api.py` - FastAPI wrapper
- `/API_SETUP.md` - Backend documentation
- `/FRONTEND_SETUP.md` - Frontend documentation
- `/INTEGRATION_COMPLETE.md` - Full integration guide
- `/.env.local` - Frontend config template

✅ **Updated:**
- `/app/(dashboard)/ai-assistant/page.tsx` - Now uses real API

## File Structure

```
Pet_AI_Backend/
  ├── chatbot/
  │   ├── api.py ✨ (NEW - FastAPI wrapper)
  │   ├── main.py (Unchanged - CLI still works)
  │   ├── rag/ (Unchanged - All RAG features work)
  │   └── ... (Everything else unchanged)
  ├── requirements.txt (fastapi/uvicorn already included)
  ├── API_SETUP.md ✨
  ├── INTEGRATION_COMPLETE.md ✨
  └── .env (Make sure this exists!)

Pet_AI_Frontend/
  ├── app/
  │   └── (dashboard)/
  │       └── ai-assistant/
  │           └── page.tsx ✨ (Updated)
  ├── .env.local ✨ (NEW - Has API URL)
  ├── FRONTEND_SETUP.md ✨
  └── ... (Rest unchanged)
```

## Environment Variables

### Backend (.env in Pet_AI_Backend/)
```
OPENROUTER_API_KEY=your_api_key_here
LANGCHAIN_API_KEY=your_api_key_here
LANGCHAIN_TRACING_V2=true
```

### Frontend (.env.local in Pet_AI_Frontend/)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## One-Command Start (macOS/Linux)

Save as `start_all.sh`:

```bash
#!/bin/bash
cd /Users/akilafernando/Documents/GitHub/Pet_AI_Backend && \
python -m uvicorn chatbot.api:app --reload --host 0.0.0.0 --port 8000 &
sleep 2
cd /Users/akilafernando/Documents/GitHub/Pet_AI_Frontend && npm run dev
```

Then:
```bash
chmod +x start_all.sh
./start_all.sh
```

## Common Commands

```bash
# Backend
cd Pet_AI_Backend
python -m uvicorn chatbot.api:app --reload  # Development
python -m uvicorn chatbot.api:app --host 0.0.0.0  # Production

# Frontend  
cd Pet_AI_Frontend
npm install        # First time
npm run dev       # Development
npm run build     # Production build
npm start         # Run production build

# Testing
curl http://localhost:8000/api/health  # Check if backend is running
curl http://localhost:3000 # Check if frontend is running
```

## Documentation

- **API Details**: Read `API_SETUP.md` in backend folder
- **Frontend Details**: Read `FRONTEND_SETUP.md` in frontend folder
- **Full Integration**: Read `INTEGRATION_COMPLETE.md` in backend folder
- **Interactive Docs**: http://localhost:8000/docs (when running)

## Next Steps

1. ✅ Run backend and frontend
2. ✅ Test chat with different pet types
3. ✅ Read the full guides if you need details
4. ✅ Deploy to production when ready

## Support

Need help?
1. Check error messages in terminal logs
2. Look at browser console (F12)
3. Check network tab (F12 → Network)
4. Read the troubleshooting section in FRONTEND_SETUP.md

## Success Criteria

You'll know it's working when:
- ✅ Backend runs without errors
- ✅ Frontend connects and shows
- ✅ Pet selection screen appears
- ✅ Sending message gets real AI response
- ✅ No console errors in browser

## That's It!

You now have:
- ✅ Full API integration between frontend and backend
- ✅ No backend logic changes
- ✅ Session management
- ✅ Real AI responses
- ✅ Production-ready architecture

Enjoy your connected AI health assistant! 🎉
