"""
Background image generation for articles using Gemini AI.

This module handles:
1. Immediate response with placeholder image
2. Background thread to generate real image
3. Cache final image URL for reuse
4. No blocking of HTTP responses
"""

import logging
import threading
import time
from typing import Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class BackgroundImageGenerator:
    """Manages background image generation with thread pool"""
    
    # Placeholder image for immediate response
    PLACEHOLDER_IMAGE = "/images/placeholder-blur.jpg"
    
    # Store ongoing generation tasks to prevent duplicates
    _generating = set()  # Set of URL hashes currently being generated
    _lock = threading.Lock()
    
    def __init__(self, generate_fn: Callable, redis_cache=None):
        """
        Initialize generator.
        
        Args:
            generate_fn: Async function that takes (title, description) -> image_url
            redis_cache: Redis cache instance for storing results
        """
        self.generate_fn = generate_fn
        self.redis_cache = redis_cache
    
    def get_image(self, url_hash: str, title: str, description: str) -> str:
        """
        Get image - returns placeholder immediately, generates in background.
        
        Args:
            url_hash: Unique identifier for article (for caching)
            title: Article title for prompt
            description: Article description for prompt
        
        Returns:
            Placeholder image URL immediately
        """
        # Check if already cached
        if self.redis_cache:
            cached = self.redis_cache.get_image(url_hash)
            if cached and cached != self.PLACEHOLDER_IMAGE:
                return cached
        
        # Check if already generating (prevent duplicate jobs)
        with self._lock:
            if url_hash not in self._generating:
                self._generating.add(url_hash)
                # Start background generation
                thread = threading.Thread(
                    target=self._generate_background,
                    args=(url_hash, title, description),
                    daemon=True,
                    name=f"ImageGen-{url_hash}"
                )
                thread.start()
        
        # Return placeholder immediately
        return self.PLACEHOLDER_IMAGE
    
    def _generate_background(self, url_hash: str, title: str, description: str):
        """
        Generate image in background thread (non-blocking).
        
        Args:
            url_hash: Article identifier
            title: Article title
            description: Article description
        """
        try:
            logger.info(f"🎨 Starting background image generation for {url_hash}")
            
            # Create prompt
            prompt = f"{title}. {description[:200]}"
            
            # Call the async generator function
            start = time.time()
            image_url = self.generate_fn(title, description, prompt)
            elapsed = time.time() - start
            
            if image_url and image_url != self.PLACEHOLDER_IMAGE:
                # Cache the result (7-day TTL)
                if self.redis_cache:
                    self.redis_cache.set_image(url_hash, image_url)
                logger.info(f"✓ Image generated in {elapsed:.2f}s: {url_hash} → {image_url[:50]}...")
            else:
                logger.warning(f"✗ Image generation failed for {url_hash}")
        
        except Exception as e:
            logger.error(f"✗ Error generating image for {url_hash}: {e}")
        
        finally:
            # Clean up: mark as done generating
            with self._lock:
                self._generating.discard(url_hash)


class AsyncImageGenWrapper:
    """Wrapper to convert async image generation to sync with background threading"""
    
    def __init__(self, gemini_generator, puter_generator=None):
        """
        Args:
            gemini_generator: Function to call for Gemini image generation
            puter_generator: Optional function to call for Puter.js image generation
        """
        self.gemini_generator = gemini_generator
        self.puter_generator = puter_generator
    
    def generate(self, title: str, description: str, prompt: str) -> str:
        """
        Generate image (or trigger async generation).
        
        For now, returns placeholder. In production, this could:
        1. Use sync API calls if available
        2. Return status endpoint URL
        3. Return placeholder and let frontend poll for updates
        
        Args:
            title: Article title
            description: Article description
            prompt: Full prompt for image generation
        
        Returns:
            Image URL or placeholder
        """
        try:
            # Try Gemini first if available
            if self.gemini_generator:
                image_url = self.gemini_generator(title, description)
                if image_url:
                    return image_url
            
            # Fallback to Puter if available
            if self.puter_generator:
                image_url = self.puter_generator(prompt)
                if image_url:
                    return image_url
        
        except Exception as e:
            logger.warning(f"Sync image generation failed: {e}")
        
        # Return placeholder if generation fails
        return BackgroundImageGenerator.PLACEHOLDER_IMAGE


# Example usage pattern in Flask app:
# 
# from background_image_generator import BackgroundImageGenerator
# 
# def my_image_generator(title, description, prompt):
#     # This runs in background thread
#     return call_gemini_api(prompt)
# 
# image_gen = BackgroundImageGenerator(my_image_generator, redis_cache)
# 
# # In API endpoint:
# image_url = image_gen.get_image(url_hash, title, description)  # Returns immediately
