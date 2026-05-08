#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Set PYTHONPATH to include the src directory
export PYTHONPATH=$PYTHONPATH:$SCRIPT_DIR/src

# Check if .venv exists, if so activate it
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load .env variables for backend/frontend startup
if [ -f ".env" ]; then
    echo "Loading environment from .env..."
    set -a
    source .env
    set +a
fi

echo "Stopping processes on ports 8000 and 5173..."
lsof -ti:8000,5173 | xargs kill -9 2>/dev/null || true

# Function to stop background processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $(jobs -p)
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting Ops Agent Backend..."
python3 src/app/main.py &

echo "Starting Ops Agent Frontend..."
cd web && npm run dev &

# Wait for background processes
wait
