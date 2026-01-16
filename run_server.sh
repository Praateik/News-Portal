#!/bin/bash
# Run server script - activates venv and runs server

cd "$(dirname "$0")"

# Check if venv exists in news-fetch directory
if [ -d "news-fetch/vevn" ]; then
    echo "Activating virtual environment from news-fetch/vevn..."
    source news-fetch/vevn/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment from venv..."
    source venv/bin/activate
else
    echo "No virtual environment found. Please create one first:"
    echo "  cd news-fetch && python3 -m venv vevn && source vevn/bin/activate && pip install -r requirements.txt"
    exit 1
fi

echo "Starting Nepal Times News Server..."
echo "Server will run on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

python3 server.py






