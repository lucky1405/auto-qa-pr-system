#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "================================================================"
echo "🛡️  Auto-QA PR Sentinel - Launching Working Demo"
echo "================================================================"

VENV_PYTHON="$DIR/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

echo "Running test suite verification..."
./venv/bin/pytest tests/ -q

echo ""
echo "🚀 Starting FastAPI Server with 4 Async Worker Threads..."
echo "👉 Interactive Dashboard: http://127.0.0.1:8000"
echo "👉 API Documentation:    http://127.0.0.1:8000/docs"
echo ""

exec ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
