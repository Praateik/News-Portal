#!/usr/bin/env python3
"""
Flask backend server for Nepal Times news aggregator
Fetches news from multiple Nepali news portals and serves via API
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import feedparser
import requests
from bs4 import BeautifulSoup
import sys
import os
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# Add news-fetch to path - handle both local and venv installations
news_fetch_path = os.path.join(os.path.dirname(__file__), 'news-fetch')
sys.path.insert(0, news_fetch_path)

# Also add the newsfetch package directory
newsfetch_path = os.path.join(news_fetch_path, 'newsfetch')
if os.path.exists(newsfetch_path):
    sys.path.insert(0, newsfetch_path)

try:
    from newsfetch.news import Newspaper
except ImportError as e:
    # Try alternative import path
    try:
        sys.path.insert(0, os.path.join(news_fetch_path, 'newsfetch'))
        from news import Newspaper
    except ImportError:
        print(f"Error importing Newspaper: {e}")
        print("Make sure you have activated the virtual environment and installed all dependencies.")
        print("Try: source news-fetch/vevn/bin/activate")
        raise

app = Flask(__name__)

# CORS Configuration for local development
# Allow requests from localhost/127.0.0.1 on common dev ports
CORS(
    app,
    origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ],
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    supports_credentials=False,
    max_age=3600
)

# News portals configuration
NEWS_PORTALS = {
    'ekantipur': {
        'name': 'ekantipur',
        'url': 'https://ekantipur.com/',
        'rss': 'https://ekantipur.com/rss'
    },
    'onlinekhabar': {
        'name': 'Onlinekhabar',
        'url': 'https://www.onlinekhabar.com/',
        'rss': 'https://www.onlinekhabar.com/feed'
    },
    'setopati': {
        'name': 'Setopati',
        'url': 'https://www.setopati.com/',
        'rss': 'https://www.setopati.com/rss'
    },
    'cnn': {
        'name': 'CNN',
        'url': 'https://edition.cnn.com/',
        'rss': 'http://rss.cnn.com/rss/edition.rss'
    },
    'bbcnepali': {
        'name': 'BBC Nepali',
        'url': 'https://www.bbc.com/nepali',
        'rss': 'https://feeds.bbci.co.uk/nepali/rss.xml'
    }
}


def get_article_urls_from_rss(rss_url, max_articles=10):
    """Fetch article URLs from RSS feed"""
    try:
        feed = feedparser.parse(rss_url)
        urls = []
        for entry in feed.entries[:max_articles]:
            if 'link' in entry:
                urls.append(entry.link)
        return urls
    except Exception as e:
        print(f"Error fetching RSS from {rss_url}: {e}")
        return []


def get_article_urls_from_homepage(homepage_url, max_articles=10):
    """Scrape homepage to get article URLs"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(homepage_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        urls = []
        # Find article links (common patterns)
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')
            if href and (href.startswith('http') or href.startswith('/')):
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = homepage_url.rstrip('/') + href

                # Filter out non-article URLs
                if any(exclude in href.lower() for exclude in ['javascript:', 'mailto:', '#', 'tag/', 'category/', 'author/', 'page/', 'search']):
                    continue

                # Check if it looks like an article URL
                if any(indicator in href for indicator in ['/news/', '/article/', '/story/', '/post/', '/content/']):
                    urls.append(href)
                elif homepage_url in href and href not in urls:
                    # For sites with different URL structure, add if it's not the homepage
                    if href != homepage_url and href not in urls:
                        urls.append(href)

        # Remove duplicates and limit
        urls = list(dict.fromkeys(urls))[:max_articles]
        return urls
    except Exception as e:
        print(f"Error scraping homepage {homepage_url}: {e}")
        return []


def fetch_article_details(url):
    """Fetch article details using news-fetch"""
    try:
        news = Newspaper(url=url)
        article_data = {
            'headline': news.headline or 'No headline',
            'description': news.description or news.summary or '',
            'article': news.article or '',
            'image_url': news.image_url or '',
            'author': news.authors if isinstance(news.authors, list) else ([news.authors] if news.authors else []),
            'date_publish': str(news.date_publish) if news.date_publish else '',
            'publication': news.publication or '',
            'category': news.category or '',
            'url': url,
            'source_domain': news.source_domain or '',
            'language': news.language or ''
        }
        # Only return if we have at least a headline
        if article_data['headline'] and article_data['headline'] != 'No headline':
            return article_data
        return None
    except Exception as e:
        print(f"Error fetching article from {url}: {e}")
        return None


def fetch_news_from_portal(portal_key, max_articles=5):
    """Fetch news from a single portal"""
    portal = NEWS_PORTALS[portal_key]
    articles = []

    # Try RSS first
    urls = get_article_urls_from_rss(portal['rss'], max_articles)

    # If RSS fails, try homepage scraping
    if not urls:
        urls = get_article_urls_from_homepage(portal['url'], max_articles)

    # Fetch article details
    for url in urls[:max_articles]:
        article = fetch_article_details(url)
        if article and article.get('headline') and article['headline'] != 'No headline':
            article['source'] = portal['name']
            articles.append(article)
            time.sleep(0.5)  # Rate limiting

    return articles


@app.route('/api/news', methods=['GET'])
def get_news():
    """Get news from all portals"""
    try:
        # Get specific source or all
        source = request.args.get('source', 'all')
        # Number of articles per source
        limit = int(request.args.get('limit', 20))

        all_articles = []

        if source == 'all':
            # Fetch from all portals
            portals = list(NEWS_PORTALS.keys())
        else:
            portals = [source] if source in NEWS_PORTALS else []

        # Use thread pool for concurrent fetching
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_portal = {
                executor.submit(fetch_news_from_portal, portal_key, limit): portal_key
                for portal_key in portals
            }

            for future in as_completed(future_to_portal):
                portal_key = future_to_portal[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    print(f"Error fetching from {portal_key}: {e}")

        # Sort by date (newest first) if available
        all_articles.sort(key=lambda x: x.get(
            'date_publish', ''), reverse=True)

        return jsonify({
            'success': True,
            'articles': all_articles,
            'count': len(all_articles)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/article/<path:url_hash>', methods=['GET'])
def get_article(url_hash):
    """Get full article details by URL hash or URL"""
    try:
        import hashlib
        import base64
        # For now, fetch from all sources and find by hash
        # In enhanced version, this would use cache
        source = request.args.get('source', 'all')
        limit = int(request.args.get('limit', 50))

        all_articles = []
        portals = list(NEWS_PORTALS.keys()) if source == 'all' else [source]

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_portal = {
                executor.submit(fetch_news_from_portal, portal_key, limit): portal_key
                for portal_key in portals
            }

            for future in as_completed(future_to_portal):
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    print(f"Error fetching from portal: {e}")

        # Try to decode base64 URL
        decoded_url = None
        try:
            decoded = base64.b64decode(
                url_hash + '==').decode('utf-8', errors='ignore')
            if decoded.startswith('http'):
                decoded_url = decoded
        except:
            pass

        # Find article by URL or hash
        for article in all_articles:
            article_url = article.get('url', '')
            if decoded_url and article_url == decoded_url:
                return jsonify({
                    'success': True,
                    'article': article
                })
            article_hash = hashlib.md5(article_url.encode()).hexdigest()
            if article_hash == url_hash:
                return jsonify({
                    'success': True,
                    'article': article
                })

        # Try partial URL match
        if decoded_url:
            for article in all_articles:
                if decoded_url in article.get('url', ''):
                    return jsonify({
                        'success': True,
                        'article': article
                    })

        return jsonify({
            'success': False,
            'error': 'Article not found'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get list of available news sources"""
    sources = [{
        'key': key,
        'name': portal['name'],
        'url': portal['url']
    } for key, portal in NEWS_PORTALS.items()]

    return jsonify({
        'success': True,
        'sources': sources
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("Starting Nepal Times News Server...")
    print("Available endpoints:")
    print("  GET /api/news - Get news from all sources")
    print("  GET /api/news?source=<source_key> - Get news from specific source")
    print("  GET /api/sources - Get list of available sources")
    print("  GET /api/health - Health check")
    print("\nNOTE: For enhanced features (hourly updates, duplicate detection, image processing),")
    print("      use server_enhanced.py instead")
    app.run(debug=True, host='0.0.0.0', port=5000)
