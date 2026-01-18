#!/bin/bash
# Production startup script for Jina News Extractor Server
# Usage: ./run_server_jina.sh

set -e

# Determine script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "news" ]; then
    echo "❌ Error: Virtual environment 'news' not found"
    echo "Create it with: python3 -m venv news"
    exit 1
fi

# Activate virtual environment
source news/bin/activate

# Check required dependencies
echo "Checking dependencies..."
python3 -c "import flask; import flask_cors; import requests" 2>/dev/null || {
    echo "❌ Error: Required packages not installed"
    echo "Install with: pip install -r requirements-jina.txt"
    exit 1
}

# Export required environment variables
if [ -z "$JINA_API_KEY" ]; then
    echo "⚠️  WARNING: JINA_API_KEY not set"
    echo "Set it with: export JINA_API_KEY='your_api_key'"
    exit 1
fi

# Export optional configuration
export PORT=${PORT:-5000}
export HOST=${HOST:-0.0.0.0}
export DEBUG=${DEBUG:-False}

echo "========================================================================"
echo "Starting Jina News Extractor Server"
echo "========================================================================"
echo "API Key: ****${JINA_API_KEY: -8}"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Debug: $DEBUG"
echo "========================================================================"

# Start the server
exec python3 server_jina.py
