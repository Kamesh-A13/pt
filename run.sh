#!/usr/bin/env bash

# ==============================================================================
# StudyOS - Autonomous One-Click Runner (macOS / Linux)
# Starts Ollama AI, FastAPI Backend, Vite Frontend, and opens your browser.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "🚀 Starting StudyOS (AI-Powered Student Assistant)"
echo "=================================================================="

# ------------------------------------------------------------------------------
# 1. Check and Start Ollama AI
# ------------------------------------------------------------------------------
echo "🔍 Checking Ollama AI status..."

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is already running on http://localhost:11434"
else
    echo "⚠️ Ollama is not running. Attempting to start Ollama..."
    if command -v open > /dev/null && [ -d "/Applications/Ollama.app" ]; then
        open -a Ollama
        sleep 4
    elif command -v ollama > /dev/null; then
        ollama serve > /dev/null 2>&1 &
        sleep 3
    else
        echo "❌ Ollama not found. Please install it from https://ollama.com"
        exit 1
    fi
fi

# Ensure model llama3.2 is available
echo "🧠 Checking for 'llama3.2' model..."
if ollama list 2>/dev/null | grep -q "llama3.2"; then
    echo "✅ Model 'llama3.2' is ready."
else
    echo "📥 Pulling 'llama3.2' (this may take a minute on first run)..."
    ollama pull llama3.2
fi

# ------------------------------------------------------------------------------
# 2. Start FastAPI Backend (Port 8000)
# ------------------------------------------------------------------------------
echo "⚙️ Preparing Backend..."
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "🚀 Starting FastAPI Backend on http://localhost:8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$SCRIPT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend running (PID: $BACKEND_PID, logs: backend.log)"

# ------------------------------------------------------------------------------
# 3. Start React / Vite Frontend (Port 5173)
# ------------------------------------------------------------------------------
echo "⚙️ Preparing Frontend..."
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
fi

echo "🚀 Starting Frontend dev server on http://localhost:5173..."
npm run dev > "$SCRIPT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "Frontend running (PID: $FRONTEND_PID, logs: frontend.log)"

# ------------------------------------------------------------------------------
# 4. Open Application in Default Browser
# ------------------------------------------------------------------------------
echo "⏳ Waiting for services to initialize..."
sleep 3

URL="http://localhost:5173"
echo "🌐 Opening StudyOS in your default browser: $URL"

if command -v open > /dev/null; then
    open "$URL"
elif command -v xdg-open > /dev/null; then
    xdg-open "$URL"
else
    echo "Please open $URL in your web browser."
fi

echo ""
echo "=================================================================="
echo "🎉 StudyOS is live!"
echo "   - Web App UI:  http://localhost:5173"
echo "   - API Docs:    http://localhost:8000/docs"
echo "   - Ollama LLM:  http://localhost:11434 (llama3.2)"
echo "Press Ctrl+C in this terminal to stop all services."
echo "=================================================================="

# Cleanup handler on exit (Ctrl+C)
cleanup() {
    echo ""
    echo "🛑 Shutting down StudyOS services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "✅ All services stopped."
    exit 0
}

trap cleanup INT TERM

# Wait for background processes
wait
