# Quick Start Guide

## Setup is Complete! ✅

All dependencies are installed in the virtual environment at `news-fetch/vevn`.

## To Run the Server:

### Option 1: Using the run script (Easiest)
```bash
./run_server.sh
```

### Option 2: Manual activation
```bash
source news-fetch/vevn/bin/activate
python3 server.py
```

The server will start on `http://localhost:5000`

## To View the Website:

1. Keep the server running (from above)
2. Open a new terminal and run:
   ```bash
   cd news-website-ui
   python3 -m http.server 8000
   ```
3. Open your browser and go to: `http://localhost:8000`

## Testing the API:

You can test the API endpoints:
- Health check: `curl http://localhost:5000/api/health`
- Get news: `curl http://localhost:5000/api/news`
- Get sources: `curl http://localhost:5000/api/sources`

## Troubleshooting:

If you get import errors:
1. Make sure you activated the virtual environment: `source news-fetch/vevn/bin/activate`
2. You should see `(vevn)` at the start of your terminal prompt
3. Try running the import test: `python3 -c "import sys; sys.path.insert(0, 'news-fetch'); from newsfetch.news import Newspaper; print('OK')"`






