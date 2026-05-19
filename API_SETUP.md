# Pet AI Chatbot API Setup Guide

## Quick Start

### 1. Backend API Setup

The API is now available at `chatbot/api.py`. To run it:

```bash
# From the Pet_AI_Backend directory
python -m uvicorn chatbot.api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

### 2. Environment Setup

Make sure your `.env` file is in the backend root with:
```
OPENROUTER_API_KEY=your_key_here
LANGCHAIN_API_KEY=your_key_here
LANGCHAIN_TRACING_V2=true
```

### 3. Frontend Configuration

Update your frontend `.env.local` with:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## API Endpoints

### Session Management

#### Create a new chat session
```
POST /api/sessions
Content-Type: application/json

{
  "pet_type": "dog"  // or "cat"
}

Response:
{
  "session_id": "uuid-string",
  "pet_type": "dog",
  "messages_count": 0
}
```

#### Get session info
```
GET /api/sessions/{session_id}
```

#### Delete a session
```
DELETE /api/sessions/{session_id}
```

### Chat

#### Send a message
```
POST /api/sessions/{session_id}/chat
Content-Type: application/json

{
  "content": "My dog is limping on his front leg",
  "include_image": false
}

Response:
{
  "message": "Based on the symptoms...",
  "is_analysis": true,
  "analysis_data": {
    "condition": "Possible Sprain",
    "confidence": 85,
    "actions": [...],
    "dos": [...],
    "donts": [...]
  }
}
```

### Image Analysis

#### Analyze an uploaded image
```
POST /api/sessions/{session_id}/analyze-image
Content-Type: multipart/form-data

[binary image file]

Response:
{
  "class_name": "skin_infection",
  "confidence": 0.92,
  "error": null
}
```

### Health Check

```
GET /api/health
```

## Architecture

### How It Works

1. **Session Management**: Each user session maintains:
   - Pet type (dog/cat)
   - Conversation memory
   - Current disease type tracking
   - Analysis state

2. **Message Processing**:
   - User sends message
   - API detects disease type from keywords
   - Builds conversation context
   - Calls agentic RAG system
   - Returns response with optional analysis data

3. **Conversation Memory**:
   - All messages saved in memory
   - Context provided to LLM for follow-up questions
   - Disease type tracked throughout conversation

4. **Image Analysis**:
   - Images uploaded directly to API
   - Analyzed using existing CV models
   - Results returned for display

## No Backend Changes

All existing chatbot logic remains intact:
- ✅ Agentic RAG system (`chatbot/rag/agentic_rag.py`)
- ✅ Conversation memory (`chatbot/memory.py`)
- ✅ LLM integration (`chatbot/llm.py`)
- ✅ CV tools (`chatbot/tools.py`)
- ✅ Message parsing and cleaning
- ✅ Disease type detection
- ✅ Image path extraction

The API is just a thin wrapper that:
- Manages sessions
- Receives HTTP requests
- Delegates to existing functions
- Returns responses in API format

## Running Both Services

For development, you'll want to run:

### Terminal 1 - Backend API
```bash
cd /Users/akilafernando/Documents/GitHub/Pet_AI_Backend
python -m uvicorn chatbot.api:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 - Frontend Development
```bash
cd /Users/akilafernando/Documents/GitHub/Pet_AI_Frontend
npm run dev
```

The frontend will be at http://localhost:3000
The backend API will be at http://localhost:8000

## Testing the API

Use the interactive Swagger UI at http://localhost:8000/docs:

1. Click "Try it out" on `/api/sessions` POST endpoint
2. Create a session with pet_type "dog"
3. Copy the session_id from the response
4. Use the session_id in `/api/sessions/{session_id}/chat` endpoint
5. Send messages and see responses

## Troubleshooting

### CORS Issues
The API has CORS enabled for all origins. For production, update:
```python
# In chatbot/api.py
allow_origins=["https://yourdomain.com"]  # Instead of "*"
```

### Import Errors
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### API Not Responding
Check that:
1. Backend server is running (`python -m uvicorn ...`)
2. Port 8000 is not in use
3. Check logs for errors in the terminal

### Session Not Found
Sessions are stored in memory and lost when API restarts. For production, implement persistent storage (database).
