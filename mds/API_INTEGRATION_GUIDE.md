# Pet AI Healthcare Chatbot - API Integration Guide

## Overview

The chatbot backend is now exposed as a REST API that the frontend can communicate with. **No chatbot logic has been changed** - all functions are imported and reused from the existing CLI implementation.

## Architecture

```
Frontend (React/Vue)
    ↓
API Endpoints (chatbot/api.py)
    ↓
Chatbot Logic (unchanged)
    ├─ agentic_rag.py (intelligent routing)
    ├─ tools.py (CV image analysis)
    ├─ main.py (conversation flow)
    └─ memory.py (conversation history)
    ↓
CV Models (FastAPI) + LLM + Knowledge Base
```

## API Endpoints

### 1. Start Conversation
**POST** `/api/chat/start`

Initiates a new conversation session with pet type selection.

**Request:**
```json
{
    "animal": "dog",  // "dog" or "cat"
    "user_id": "optional_user_id"  // optional
}
```

**Response:**
```json
{
    "session_id": "uuid-string",
    "animal": "dog",
    "message": "✅ Great! I'll help you with your DOG's health. How can I assist you today?"
}
```

**Usage:**
```javascript
const response = await fetch('http://localhost:8001/api/chat/start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        animal: selectedPetType  // from frontend dropdown
    })
});
const { session_id } = await response.json();
```

---

### 2. Send Message
**POST** `/api/chat/message`

Sends a user message and receives bot response.

**Request:**
```json
{
    "session_id": "uuid-string",
    "message": "My dog is limping on his front leg"
}
```

**Response:**
```json
{
    "session_id": "uuid-string",
    "bot_response": "I understand your concern about your dog's limping...",
    "used_rag": true,
    "disease_detected": null  // "skin", "eye", or null
}
```

**Key Points:**
- Message can include image path: `/path/to/image.jpg`
- `used_rag`: True if knowledge base was searched
- `disease_detected`: Type of disease detected from keywords

**Usage:**
```javascript
const response = await fetch('http://localhost:8001/api/chat/message', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        session_id: sessionId,
        message: userMessage
    })
});
const { bot_response, used_rag } = await response.json();
```

---

### 3. Upload Image
**POST** `/api/chat/upload-image`

Upload and analyze a pet image (skin or eye).

**Request:**
```
POST /api/chat/upload-image
Content-Type: multipart/form-data

Parameters:
- session_id: uuid-string
- disease_type: "skin" or "eye"
- file: <binary image data>
```

**Response:**
```json
{
    "session_id": "uuid-string",
    "disease_class": "Dermatitis",
    "confidence": 0.92,
    "explanation": "# Dermatitis in Dogs\n\nDermatitis is inflammation of the skin..."
}
```

**Usage:**
```javascript
const formData = new FormData();
formData.append('session_id', sessionId);
formData.append('disease_type', 'skin');  // or 'eye'
formData.append('file', imageFile);

const response = await fetch('http://localhost:8001/api/chat/upload-image', {
    method: 'POST',
    body: formData
});
const result = await response.json();
```

---

### 4. Get Chat History
**GET** `/api/chat/history/{session_id}`

Retrieve conversation history for a session.

**Response:**
```json
{
    "session_id": "uuid-string",
    "animal": "dog",
    "chat_history": "HumanMessage: My dog is limping\nAIMessage: I understand your concern..."
}
```

---

### 5. End Session
**DELETE** `/api/chat/session/{session_id}`

End a conversation session and clean up.

**Response:**
```json
{
    "session_id": "uuid-string",
    "message": "Session ended"
}
```

---

### 6. Health Check
**GET** `/health`

Check API status.

**Response:**
```json
{
    "status": "healthy",
    "service": "Pet AI Healthcare Chatbot API",
    "active_sessions": 5
}
```

---

## Frontend Integration Example

### React Example

```javascript
import React, { useState } from 'react';

const API_URL = 'http://localhost:8001';

export function ChatBot() {
    const [sessionId, setSessionId] = useState(null);
    const [animal, setAnimal] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    // Step 1: Start conversation
    const handleStartChat = async (selectedAnimal) => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/api/chat/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ animal: selectedAnimal })
            });
            const data = await res.json();
            
            setSessionId(data.session_id);
            setAnimal(selectedAnimal);
            setMessages([{ role: 'bot', content: data.message }]);
        } finally {
            setLoading(false);
        }
    };

    // Step 2: Send message
    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim() || !sessionId) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const res = await fetch(`${API_URL}/api/chat/message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    session_id: sessionId,
                    message: userMsg 
                })
            });
            const data = await res.json();
            
            setMessages(prev => [...prev, { 
                role: 'bot', 
                content: data.bot_response,
                used_rag: data.used_rag,
                disease: data.disease_detected
            }]);
        } finally {
            setLoading(false);
        }
    };

    // Step 3: Handle image upload
    const handleImageUpload = async (e, diseaseType) => {
        const file = e.target.files[0];
        if (!file || !sessionId) return;

        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('session_id', sessionId);
            formData.append('disease_type', diseaseType);
            formData.append('file', file);

            const res = await fetch(`${API_URL}/api/chat/upload-image`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            setMessages(prev => [...prev, {
                role: 'bot',
                content: data.explanation,
                diagnosis: data.disease_class,
                confidence: data.confidence
            }]);
        } finally {
            setLoading(false);
        }
    };

    if (!sessionId) {
        // Pet selection screen
        return (
            <div className="pet-selector">
                <h1>Choose Your Pet Type</h1>
                <button onClick={() => handleStartChat('dog')}>🐕 Dog</button>
                <button onClick={() => handleStartChat('cat')}>🐱 Cat</button>
            </div>
        );
    }

    // Chat screen
    return (
        <div className="chatbot">
            <div className="messages">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`message ${msg.role}`}>
                        {msg.content}
                        {msg.disease && <p>Disease: {msg.disease}</p>}
                        {msg.used_rag && <small>🔍 Knowledge base used</small>}
                    </div>
                ))}
            </div>

            <form onSubmit={handleSendMessage}>
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Describe symptoms or ask questions..."
                    disabled={loading}
                />
                <button type="submit" disabled={loading}>
                    {loading ? 'Loading...' : 'Send'}
                </button>
            </form>

            <input
                type="file"
                onChange={(e) => handleImageUpload(e, 'skin')}
                disabled={loading}
                accept="image/*"
            />
        </div>
    );
}
```

---

## Running the API

### Start the Backend API:

```bash
cd Pet_AI_Backend
source venv/bin/activate

# Option 1: Use uvicorn directly
uvicorn chatbot.api:app --reload --port 8001

# Option 2: Use Python module
python -m uvicorn chatbot.api:app --reload --port 8001
```

### API will be available at:
- **Base**: `http://localhost:8001`
- **Docs**: `http://localhost:8001/docs` (Swagger UI)
- **Health**: `http://localhost:8001/health`

---

## Important Notes

✅ **What's Preserved:**
- All chatbot logic unchanged
- Agentic RAG routing intact
- Image analysis via CV models
- Disease detection and memory
- Conversation history

✅ **What's Added:**
- REST API endpoints
- Session management
- Pet type selection in frontend
- Image upload handling

✅ **Frontend Communication:**
- Pure HTTP/REST (no websockets needed)
- Each session is independent
- Stateless API (sessions stored in memory)

---

## Architecture Flow

```
Frontend:
1. User opens app
2. Selects pet type (dog/cat)
   ↓ POST /api/chat/start
   ↓ Receives session_id
3. Types message
   ↓ POST /api/chat/message
   ↓ Receives bot_response
4. Optionally uploads image
   ↓ POST /api/chat/upload-image
   ↓ Receives disease diagnosis

Backend (unchanged):
- Detects disease type (skin/eye)
- Routes to agentic RAG
- Analyzes images with CV models
- Maintains conversation history
- Returns responses
```

---

## Troubleshooting

**Issue: CORS errors**
- Solution: CORS already enabled in `api.py`

**Issue: 404 session not found**
- Solution: Check session_id is correct, session may have expired

**Issue: Image upload fails**
- Solution: Ensure image format is supported (jpg, png, gif, bmp)

**Issue: No RAG response**
- Solution: Check knowledge base is loaded (check backend logs)

---

## API Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid pet type, etc.) |
| 404 | Session not found |
| 500 | Server error |

---

## Session Management

- Sessions are stored in-memory
- Each session is independent
- Use `DELETE /api/chat/session/{session_id}` to clean up
- Sessions persist for the lifetime of API process
- For production, consider adding session persistence

---

## Next Steps

1. Start the backend API (as shown above)
2. Configure frontend API base URL
3. Implement pet type selection in UI
4. Connect message sending to API
5. Implement image upload functionality
6. Handle RAG indicators in UI

The chatbot is **fully functional and unchanged** - this API is just the communication layer! 🚀
