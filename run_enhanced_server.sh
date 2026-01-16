#!/bin/bash
# Run enhanced server script

cd "$(dirname "$0")"

# Check if venv exists
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

echo "Starting Nepal Times Enhanced News Server..."
echo "Features:"
echo "  - Automatic hourly news updates"
echo "  - Duplicate detection and featured news"
echo "  - Image processing"
echo ""
echo "Server will run on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

python3 server_enhanced.py






