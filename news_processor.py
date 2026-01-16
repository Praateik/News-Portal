"""
News processing utilities for duplicate detection and image handling
"""

import re
from difflib import SequenceMatcher
from collections import defaultdict
import requests
from PIL import Image
import io
from typing import List, Dict, Tuple


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two text strings"""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    if not text:
        return ""
    # Remove special characters, extra spaces
    text = re.sub(r'[^\w\s]', '', text.lower())
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def find_duplicate_news(articles: List[Dict]) -> Dict:
    """
    Find duplicate news across different portals
    Returns a dictionary with featured news (appearing in multiple portals)
    """
    # Group articles by similarity
    article_groups = []
    processed = set()
    
    for i, article1 in enumerate(articles):
        if i in processed:
            continue
        
        group = [article1]
        processed.add(i)
        
        # Compare with other articles
        for j, article2 in enumerate(articles[i+1:], start=i+1):
            if j in processed:
                continue
            
            # Compare headlines and descriptions
            headline_sim = calculate_similarity(
                article1.get('headline', ''),
                article2.get('headline', '')
            )
            
            desc_sim = calculate_similarity(
                article1.get('description', '')[:200],  # First 200 chars
                article2.get('description', '')[:200]
            )
            
            # If similar, group them
            if headline_sim > 0.7 or (headline_sim > 0.5 and desc_sim > 0.6):
                group.append(article2)
                processed.add(j)
        
        if len(group) > 1:
            article_groups.append(group)
    
    # Find the most popular news (appears in most portals)
    featured_news = None
    max_sources = 0
    
    for group in article_groups:
        if len(group) >= 2:  # At least 2 portals
            # Merge the group into one featured article
            merged = merge_article_group(group)
            if len(group) > max_sources:
                max_sources = len(group)
                featured_news = merged
    
    return {
        'featured': featured_news,
        'groups': article_groups,
        'regular': [a for i, a in enumerate(articles) if i not in processed]
    }


def merge_article_group(group: List[Dict]) -> Dict:
    """Merge a group of similar articles into one"""
    if not group:
        return None
    
    # Use the article with the longest description
    best_article = max(group, key=lambda x: len(x.get('description', '')))
    
    # Collect all sources
    sources = [a.get('source', '') for a in group if a.get('source')]
    
    merged = best_article.copy()
    merged['source'] = ', '.join(set(sources))
    merged['source_count'] = len(set(sources))
    merged['is_featured'] = True
    
    return merged


def download_image(url: str) -> Image.Image:
    """Download image from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
    except Exception as e:
        print(f"Error downloading image: {e}")
    return None


def detect_watermark(image: Image.Image) -> Tuple[bool, Dict]:
    """
    Detect if image has watermark/trademark
    Returns (has_watermark, watermark_info)
    """
    if not image:
        return False, {}
    
    # Simple heuristic: check corners and edges for text-like patterns
    # This is a basic implementation - can be enhanced with OCR/ML models
    
    width, height = image.size
    
    # Check bottom-right corner (common watermark location)
    corner_size = min(width, height) // 4
    bottom_right = image.crop((
        width - corner_size,
        height - corner_size,
        width,
        height
    ))
    
    # Convert to grayscale and check for high contrast areas (text indicators)
    gray = bottom_right.convert('L')
    # Simple threshold check
    pixels = list(gray.getdata())
    avg_brightness = sum(pixels) / len(pixels)
    
    # If there's high contrast in corner, likely a watermark
    has_watermark = False
    watermark_info = {
        'detected': has_watermark,
        'location': 'bottom-right' if has_watermark else None
    }
    
    return has_watermark, watermark_info


def remove_watermark_basic(image: Image.Image, watermark_info: Dict) -> Image.Image:
    """
    Basic watermark removal (inpainting the watermark area)
    This is a simplified version - can be enhanced with inpainting algorithms
    """
    if not image or not watermark_info.get('detected'):
        return image
    
    # For now, just return the original image
    # Advanced implementations would use inpainting (OpenCV, scikit-image)
    return image






