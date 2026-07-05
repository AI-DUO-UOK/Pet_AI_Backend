#!/bin/bash

# Startup script for Pet AI Backend Services
# Starts the single unified FastAPI server (port 8000)

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

# Start Unified API
echo "🚀 Starting Unified Pet AI API (FastAPI)..."
echo "   Running on: http://localhost:8000"
echo "   API Docs:   http://localhost:8000/docs"
python -m uvicorn main:app --reload --port 8000
