# Nepal Times - Setup Instructions

## Quick Start

### Step 1: Activate Virtual Environment
```bash
cd /home/pratik/Desktop/news
source news-fetch/vevn/bin/activate
```
You should see `(vevn)` at the start of your terminal prompt.

### Step 2: Start the Server
```bash
python3 server.py
```
The server will start on `http://localhost:5000`

**OR** use the run script:
```bash
./run_server.sh
```

### Step 3: Open the Website (in a new terminal)
```bash
cd /home/pratik/Desktop/news/news-website-ui
python3 -m http.server 8000
```
Then open `http://localhost:8000` in your browser.

---

## API Endpoints

- **Health check**: `curl http://localhost:5000/api/health`
- **Get all news**: `curl http://localhost:5000/api/news`
- **Get specific source**: `curl http://localhost:5000/api/news?source=ekantipur`
- **Get sources list**: `curl http://localhost:5000/api/sources`

## News Sources

The aggregator fetches from:
- ekantipur.com
- onlinekhabar.com  
- setopati.com
- edition.cnn.com
- bbc.com/nepali

## Troubleshooting

**Import errors?**
- Make sure virtual environment is activated: `source news-fetch/vevn/bin/activate`
- You should see `(vevn)` in your prompt

**Server won't start?**
- Check if port 5000 is already in use
- Make sure all dependencies are installed in the venv

**No news showing?**
- Check server console for errors
- Verify internet connection
- Some news sources may block automated requests






