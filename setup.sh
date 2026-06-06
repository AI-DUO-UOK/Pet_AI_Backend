#!/bin/bash

# Pet AI Backend - Setup Script
# This script installs all dependencies and checks configuration

echo ""
echo "========================================"
echo "  Pet AI Backend - Setup Script"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

echo "[OK] Python found:"
python3 --version
echo ""

# Install requirements
echo "[INSTALL] Installing dependencies from requirements.txt..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi

echo "[OK] All dependencies installed successfully"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "[WARNING] .env file not found"
    echo "[INFO] Creating .env from .env.example..."
    cp .env.example .env
    echo "[INFO] Please edit .env with your Supabase credentials"
    echo ""
fi

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Supabase credentials"
echo "2. Run: python -m uvicorn app.main:app --reload"
echo "3. Visit: http://localhost:8000/docs"
echo ""
echo "For help, see: BACKEND_STARTUP_GUIDE.md"
echo ""
