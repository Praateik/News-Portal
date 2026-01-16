#!/bin/bash
# Startup script for Nepal Times News Server

echo "Starting Nepal Times News Server..."
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if dependencies are installed
echo "Checking dependencies..."
python3 -c "import flask" 2>/dev/null || {
    echo "Installing server dependencies..."
    pip install -r requirements-server.txt
}

# Start the server
echo "Starting Flask server on http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""
python3 server.py






