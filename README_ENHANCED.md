# Nepal Times - Enhanced Server Features

## New Features

### 1. Automatic Hourly Updates
- News is automatically fetched and updated every hour
- Uses APScheduler for background scheduling
- No need to manually refresh

### 2. Duplicate Detection & Featured News
- Detects when the same news appears in multiple portals
- Automatically promotes news appearing in 2+ portals to "Featured"
- Featured news appears first in the list and as the showcase article

### 3. Image Processing
- Detects watermarks/trademarks in images
- Can generate new images using Gemini API (when configured)
- Processes images during article fetching

### 4. News Caching
- News is cached in memory for fast access
- Updates happen in background without interrupting service

## Setup

### 1. Install Additional Dependencies
```bash
source news-fetch/vevn/bin/activate
pip install -r requirements-server.txt
```

### 2. Configure Gemini API (Optional)
Update `config.py`:
```python
GEMINI_API_KEY = "your-gemini-api-key-here"
```

Get API key from: https://makersuite.google.com/app/apikey

**Note**: The OAuth client ID you provided is not a Gemini API key. See `GEMINI_SETUP.md` for details.

### 3. Run Enhanced Server
```bash
source news-fetch/vevn/bin/activate
python3 server_enhanced.py
```

## API Endpoints

- `GET /api/news` - Get cached news (with featured article)
- `GET /api/health` - Check server status and last update time
- `POST /api/update` - Manually trigger news update
- `GET /api/sources` - Get list of news sources

## Response Format

```json
{
  "success": true,
  "articles": [...],
  "featured": {
    "headline": "...",
    "description": "...",
    "source_count": 3,
    "source": "ekantipur, Onlinekhabar, Setopati",
    "is_featured": true,
    ...
  },
  "count": 20,
  "last_update": "2024-01-01T12:00:00"
}
```

## Features Status

- ✅ Hourly automatic updates
- ✅ Duplicate detection
- ✅ Featured news promotion
- ✅ Image watermark detection (basic)
- ⚠️ Image generation (requires Gemini API key)
- ⚠️ Watermark removal (requires image processing libraries)

## Troubleshooting

**Scheduler not running?**
- Make sure APScheduler is installed: `pip install APScheduler`

**Gemini errors?**
- Image generation is optional - the system works without it
- Get a proper Gemini API key (not OAuth client ID)
- See `GEMINI_SETUP.md` for details

**No featured news?**
- Featured news appears only when same news is found in 2+ portals
- Check similarity threshold in `config.py`






