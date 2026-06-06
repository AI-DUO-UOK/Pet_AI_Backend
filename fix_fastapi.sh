#!/bin/bash

# Fix FastAPI CORS Import Error - Mac/Linux
# This script reinstalls FastAPI and dependencies properly

echo ""
echo "========================================"
echo "  FastAPI Fix - Mac/Linux"
echo "========================================"
echo ""

# Step 1: Uninstall FastAPI
echo "[STEP 1] Uninstalling existing FastAPI..."
pip uninstall fastapi -y
pip uninstall uvicorn -y
pip uninstall starlette -y

# Step 2: Clear pip cache
echo "[STEP 2] Clearing pip cache..."
pip cache purge

# Step 3: Reinstall with specific versions
echo "[STEP 3] Installing FastAPI with compatible versions..."
pip install fastapi==0.104.1 uvicorn==0.24.0 python-multipart==0.0.6

# Step 4: Reinstall all requirements
echo "[STEP 4] Installing all dependencies..."
pip install -r requirements.txt --upgrade

echo ""
echo "========================================"
echo "  Fix Complete!"
echo "========================================"
echo ""
echo "You can now run:"
echo "  python -m uvicorn app.main:app --reload"
echo ""
