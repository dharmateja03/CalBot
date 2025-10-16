#!/bin/bash

# CalBot Backend Startup Script

echo "🚀 Starting CalBot Backend..."

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -d "venv/lib/python3.*/site-packages/fastapi" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Please create .env file with your API keys"
    echo "You can copy from .env.example"
fi

# Start FastAPI server
echo "✅ Starting server on http://localhost:8000"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
