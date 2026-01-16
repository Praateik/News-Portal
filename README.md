# Nepal Times - News Aggregator

A news aggregator website that fetches news from multiple Nepali news portals and displays them in a modern, responsive interface.

## Features

- Fetches news from multiple sources:
  - ekantipur.com
  - onlinekhabar.com
  - setopati.com
  - edition.cnn.com
  - bbc.com/nepali
- Real-time news aggregation
- Responsive design
- Clean, modern UI

## Setup Instructions

### 1. Install Python Dependencies

First, install the news-fetch library dependencies:
```bash
cd news-fetch
pip install -r requirements.txt
```

Then, install the server dependencies (from the root directory):
```bash
cd ..
pip install -r requirements-server.txt
```

**Note:** The news-fetch library requires several dependencies including newspaper3k, news-please, beautifulsoup4, selenium, etc. Make sure all dependencies are installed properly.

### 2. Install news-fetch Package (Optional)

You can install news-fetch as a package, but the server will work with the local directory structure as well:
```bash
cd news-fetch
pip install -e .
```

### 3. Run the Server

Start the Flask backend server:
```bash
python server.py
```

The server will run on `http://localhost:5000`

### 4. Open the Website

Open `news-website-ui/index.html` in your web browser, or use a local web server:

```bash
cd news-website-ui
python -m http.server 8000
```

Then open `http://localhost:8000` in your browser.

## API Endpoints

- `GET /api/news` - Get news from all sources
- `GET /api/news?source=<source_key>` - Get news from specific source
- `GET /api/sources` - Get list of available sources
- `GET /api/health` - Health check

## Notes

- The server fetches news from RSS feeds when available
- Falls back to homepage scraping if RSS is unavailable
- Articles are cached for performance
- Rate limiting is applied to avoid overloading news sources

## Troubleshooting

If you encounter issues:

1. Make sure all dependencies are installed
2. Check that the server is running on port 5000
3. Check browser console for CORS errors (the server includes CORS support)
4. Some news sources may have anti-scraping measures - the server handles this gracefully

