"""
Jina AI Reader API wrapper for news extraction.
Replaces newspaper, news-please, lxml, and bs4 libraries.
"""

import requests
from typing import Dict, Optional
import os


def extract_news(url: str) -> Dict:
    """
    Extract news content from a URL using Jina Reader API.
    
    Args:
        url: The article URL to extract content from
        
    Returns:
        Dictionary with extracted news fields:
        - title: Article title
        - content: Article body content
        - published_time: Publication timestamp
        - url: Original URL
        - language: Detected language
        
    Raises:
        ValueError: If URL is invalid
        ConnectionError: If Jina API is unreachable
        RuntimeError: If JINA_API_KEY is not set
    """
    
    # Validate URL
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL must start with http:// or https://")
    
    # Get API key from environment
    api_key = os.getenv('JINA_API_KEY')
    if not api_key:
        raise RuntimeError("JINA_API_KEY environment variable is not set")
    
    # Prepare Jina Reader API request
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # Call Jina Reader API with 30s timeout
        response = requests.get(jina_url, headers=headers, timeout=30)
        
        # Check for API errors
        if response.status_code == 401:
            raise RuntimeError("Invalid JINA_API_KEY - authentication failed")
        
        if response.status_code == 404:
            raise ConnectionError(f"URL not found or inaccessible: {url}")
        
        if response.status_code >= 500:
            raise ConnectionError(f"Jina API error (status {response.status_code}): {response.text[:200]}")
        
        if response.status_code >= 400:
            raise ValueError(f"Bad request (status {response.status_code}): {response.text[:200]}")
        
        response.raise_for_status()
        
        # Parse Jina response
        data = response.json()
        
        # Extract and structure the response
        extracted_data = {
            'title': data.get('title', ''),
            'content': data.get('content', ''),
            'published_time': data.get('publishedTime') or data.get('published_time', ''),
            'url': url,
            'language': data.get('language', 'unknown'),
            'raw_data': data  # Include raw response for debugging
        }
        
        return extracted_data
        
    except requests.exceptions.Timeout:
        raise ConnectionError(f"Timeout fetching URL (30s exceeded): {url}")
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(f"Failed to connect to Jina API or target URL: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Request failed: {str(e)}")
    except ValueError as e:
        raise ValueError(f"Invalid API response format: {str(e)}")
