#!/bin/bash

# Startup script for Pet AI Backend Services
# Starts both:
# 1. CV Model FastAPI server (port 8000)
# 2. Chatbot API server (port 8001)

echo "🐾 Pet AI Backend Startup Script"
echo "=================================="

# Check if venv is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Virtual environment not activated"
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

echo "✅ Virtual environment activated"
echo ""

# Start CV Model API
echo "🚀 Starting CV Model API (FastAPI)..."
echo "   Running on: http://localhost:8000"
python -m uvicorn backend.main:app --reload --port 8000 &
CV_PID=$!
sleep 2  # Give it time to start

# Start Chatbot API
echo ""
echo "🚀 Starting Chatbot API..."
echo "   Running on: http://localhost:8001"
uvicorn chatbot.api:app --reload --port 8001 &
CHAT_PID=$!
sleep 2

echo ""
echo "✅ Both services started successfully!"
echo ""
echo "Services running:"
echo "  • CV Model API:  http://localhost:8000"
echo "  • Chatbot API:   http://localhost:8001"
echo "  • API Docs:      http://localhost:8001/docs"
echo "  • Health Check:  http://localhost:8001/health"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait $CV_PID $CHAT_PID
