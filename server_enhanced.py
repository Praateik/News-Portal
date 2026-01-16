#!/usr/bin/env python3
"""
Enhanced Flask backend server for Nepal Times news aggregator
- Hourly automatic news updates
- Duplicate detection and featured news
- Image processing and generation
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
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Add news-fetch to path
news_fetch_path = os.path.join(os.path.dirname(__file__), 'news-fetch')
sys.path.insert(0, news_fetch_path)
newsfetch_path = os.path.join(news_fetch_path, 'newsfetch')
if os.path.exists(newsfetch_path):
    sys.path.insert(0, newsfetch_path)

try:
    from newsfetch.news import Newspaper
except ImportError as e:
    try:
        sys.path.insert(0, os.path.join(news_fetch_path, 'newsfetch'))
        from news import Newspaper
    except ImportError:
        print(f"Error importing Newspaper: {e}")
        raise

# Import our modules
from config import NEWS_PORTALS, UPDATE_INTERVAL_HOURS, GEMINI_API_KEY
from news_processor import find_duplicate_news, download_image, detect_watermark, remove_watermark_basic
from gemini_image_generator import GeminiImageGenerator

app = Flask(__name__)
CORS(app)

# Global cache for news
news_cache = {
    'articles': [],
    'featured': None,
    'last_update': None
}

# Initialize Gemini image generator (if API key provided)
image_generator = None
if GEMINI_API_KEY:
    try:
        image_generator = GeminiImageGenerator(GEMINI_API_KEY)
        print("Gemini image generator initialized")
    except Exception as e:
        print(f"Warning: Could not initialize Gemini: {e}")


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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(homepage_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        urls = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            if href and (href.startswith('http') or href.startswith('/')):
                if href.startswith('/'):
                    href = homepage_url.rstrip('/') + href
                if any(exclude in href.lower() for exclude in ['javascript:', 'mailto:', '#', 'tag/', 'category/', 'author/', 'page/', 'search']):
                    continue
                if any(indicator in href for indicator in ['/news/', '/article/', '/story/', '/post/', '/content/']):
                    urls.append(href)
                elif homepage_url in href and href != homepage_url and href not in urls:
                    urls.append(href)
        
        return list(dict.fromkeys(urls))[:max_articles]
    except Exception as e:
        print(f"Error scraping homepage {homepage_url}: {e}")
        return []


def process_image(image_url, headline, description):
    """Process image: detect watermark and optionally generate new one"""
    if not image_url:
        return image_url
    
    try:
        # Download and check image
        image = download_image(image_url)
        if image:
            has_watermark, watermark_info = detect_watermark(image)
            
            # If watermark detected and we have image generator, generate new image
            if has_watermark and image_generator:
                # Try to generate a new image
                generated_image = image_generator.generate_image_from_text(description, headline)
                if generated_image:
                    # Save generated image and return URL
                    # For now, return original URL
                    return image_url
            
            # Try to remove watermark (basic)
            if has_watermark:
                cleaned_image = remove_watermark_basic(image, watermark_info)
                # Save cleaned image and return URL
                # For now, return original URL
                return image_url
        
        return image_url
    except Exception as e:
        print(f"Error processing image: {e}")
        return image_url


def fetch_article_details(url, portal_name):
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
            'language': news.language or '',
            'source': portal_name
        }
        
        # Process image
        if article_data.get('image_url'):
            article_data['image_url'] = process_image(
                article_data['image_url'],
                article_data['headline'],
                article_data['description']
            )
        
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
    
    urls = get_article_urls_from_rss(portal['rss'], max_articles)
    if not urls:
        urls = get_article_urls_from_homepage(portal['url'], max_articles)
    
    for url in urls[:max_articles]:
        article = fetch_article_details(url, portal['name'])
        if article:
            articles.append(article)
            time.sleep(0.5)  # Rate limiting
    
    return articles


def update_news():
    """Update news cache - called by scheduler"""
    global news_cache
    print(f"[{datetime.now()}] Updating news...")
    
    try:
        all_articles = []
        portals = list(NEWS_PORTALS.keys())
        
        # Fetch from all portals
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_portal = {
                executor.submit(fetch_news_from_portal, portal_key, 5): portal_key
                for portal_key in portals
            }
            
            for future in as_completed(future_to_portal):
                portal_key = future_to_portal[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    print(f"Error fetching from {portal_key}: {e}")
        
        # Find duplicates and featured news
        duplicate_info = find_duplicate_news(all_articles)
        
        # Build final article list
        final_articles = []
        
        # Add featured news first if exists
        if duplicate_info.get('featured'):
            final_articles.append(duplicate_info['featured'])
        
        # Add regular articles (excluding those in groups)
        featured_urls = set()
        for group in duplicate_info.get('groups', []):
            for article in group:
                featured_urls.add(article.get('url'))
        
        for article in all_articles:
            if article.get('url') not in featured_urls:
                final_articles.append(article)
        
        # Update cache
        news_cache = {
            'articles': final_articles,
            'featured': duplicate_info.get('featured'),
            'last_update': datetime.now().isoformat()
        }
        
        print(f"[{datetime.now()}] News updated: {len(final_articles)} articles, featured: {duplicate_info.get('featured') is not None}")
        
    except Exception as e:
        print(f"Error updating news: {e}")


# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=update_news,
    trigger=IntervalTrigger(hours=UPDATE_INTERVAL_HOURS),
    id='news_update_job',
    name='Update news every hour',
    replace_existing=True
)
scheduler.start()

# Initial news fetch
print("Fetching initial news...")
update_news()


@app.route('/api/news', methods=['GET'])
def get_news():
    """Get news from cache"""
    try:
        source = request.args.get('source', 'all')
        limit = int(request.args.get('limit', 20))
        
        articles = news_cache.get('articles', [])
        
        # Filter by source if requested
        if source != 'all' and source in NEWS_PORTALS:
            articles = [a for a in articles if a.get('source') == NEWS_PORTALS[source]['name']]
        
        # Limit results
        articles = articles[:limit]
        
        return jsonify({
            'success': True,
            'articles': articles,
            'featured': news_cache.get('featured'),
            'count': len(articles),
            'last_update': news_cache.get('last_update')
        })
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
        'timestamp': datetime.now().isoformat(),
        'last_update': news_cache.get('last_update'),
        'article_count': len(news_cache.get('articles', []))
    })


@app.route('/api/update', methods=['POST'])
def manual_update():
    """Manually trigger news update"""
    try:
        update_news()
        return jsonify({
            'success': True,
            'message': 'News updated successfully',
            'last_update': news_cache.get('last_update')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("Starting Nepal Times Enhanced News Server...")
    print(f"News will be updated every {UPDATE_INTERVAL_HOURS} hour(s)")
    print("Available endpoints:")
    print("  GET /api/news - Get news from cache")
    print("  GET /api/sources - Get list of available sources")
    print("  GET /api/health - Health check")
    print("  POST /api/update - Manually trigger news update")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("\nServer stopped.")






