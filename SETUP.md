# Quick Setup Guide - Nepal Times

## Prerequisites
- Python 3.6 or higher
- pip (Python package manager)

## Installation Steps

### Step 1: Install News-Fetch Dependencies
```bash
cd news-fetch
pip install -r requirements.txt
cd ..
```

This will install:
- newspaper3k
- news-please
- beautifulsoup4
- selenium
- and other dependencies

### Step 2: Install Server Dependencies
```bash
pip install -r requirements-server.txt
```

This will install:
- Flask
- flask-cors
- feedparser
- requests
- beautifulsoup4

### Step 3: Start the Server

Option A: Using the startup script
```bash
./start_server.sh
```

Option B: Directly with Python
```bash
python3 server.py
```

The server will start on `http://localhost:5000`

### Step 4: Open the Website

Option A: Using Python HTTP server (recommended)
```bash
cd news-website-ui
python3 -m http.server 8000
```
Then open `http://localhost:8000` in your browser.

Option B: Open directly
Simply open `news-website-ui/index.html` in your browser (note: CORS may need server running)

## Testing the API

You can test the API endpoints directly:

1. Health check:
   ```bash
   curl http://localhost:5000/api/health
   ```

2. Get all news:
   ```bash
   curl http://localhost:5000/api/news
   ```

3. Get news from specific source:
   ```bash
   curl http://localhost:5000/api/news?source=ekantipur
   ```

4. Get list of sources:
   ```bash
   curl http://localhost:5000/api/sources
   ```

## Troubleshooting

### Issue: ModuleNotFoundError for 'newspaper'
**Solution:** Make sure you installed news-fetch dependencies:
```bash
cd news-fetch
pip install -r requirements.txt
```

### Issue: CORS errors in browser
**Solution:** The server includes CORS support. Make sure the server is running and the API_BASE_URL in script.js matches your server URL.

### Issue: No articles showing
**Possible causes:**
1. Server is not running
2. News sources are blocking requests
3. RSS feeds are not accessible
4. Network connectivity issues

Check the server console for error messages.

### Issue: Selenium/ChromeDriver errors
**Note:** The GoogleSearchNewsURLExtractor uses Selenium which requires ChromeDriver. However, the main functionality uses RSS feeds and direct scraping, so Selenium is not always required.

## News Sources

The aggregator fetches news from:
- ekantipur.com (Nepali)
- onlinekhabar.com (Nepali)
- setopati.com (Nepali)
- edition.cnn.com (English)
- bbc.com/nepali (Nepali)

## Notes

- The server uses RSS feeds when available
- Falls back to homepage scraping if RSS fails
- Rate limiting is applied to avoid overloading sources
- Articles are fetched in parallel for better performance
- Some news sources may have anti-scraping measures






