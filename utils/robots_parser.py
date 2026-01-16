"""
Robots.txt Parser and Rate Limiter
Respects robots.txt rules and implements rate limiting per domain
"""

import urllib.robotparser
from urllib.parse import urlparse
import time
from collections import defaultdict
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class RobotsParser:
    """
    Thread-safe robots.txt parser with caching and rate limiting
    """
    
    def __init__(self, user_agent='*', cache_ttl=3600):
        """
        Initialize robots parser
        
        Args:
            user_agent: User agent string to check against
            cache_ttl: Cache TTL in seconds (default 1 hour)
        """
        self.user_agent = user_agent
        self.cache_ttl = cache_ttl
        self.parsers = {}  # domain -> (parser, timestamp)
        self.rate_limiter = RateLimiter()
        self.lock = Lock()
    
    def can_fetch(self, url):
        """
        Check if URL can be fetched according to robots.txt
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if allowed, False if disallowed
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check rate limit first
        if not self.rate_limiter.can_request(domain):
            logger.debug(f"Rate limit reached for {domain}")
            return False
        
        # Get or create parser for this domain
        parser = self._get_parser(domain)
        
        if parser is None:
            # If we can't parse robots.txt, assume it's allowed (be conservative)
            logger.warning(f"Could not parse robots.txt for {domain}, allowing")
            return True
        
        # Check if fetch is allowed
        path = parsed.path or '/'
        allowed = parser.can_fetch(self.user_agent, url)
        
        if not allowed:
            logger.info(f"Robots.txt disallows: {url}")
        
        return allowed
    
    def _get_parser(self, domain):
        """
        Get or create robots.txt parser for domain (with caching)
        
        Args:
            domain: Domain (scheme://netloc)
            
        Returns:
            urllib.robotparser.RobotFileParser or None
        """
        with self.lock:
            # Check cache
            if domain in self.parsers:
                parser, timestamp = self.parsers[domain]
                if time.time() - timestamp < self.cache_ttl:
                    return parser
            
            # Create new parser
            robots_url = f"{domain}/robots.txt"
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(robots_url)
            
            try:
                parser.read()
                self.parsers[domain] = (parser, time.time())
                logger.debug(f"Loaded robots.txt for {domain}")
                return parser
            except Exception as e:
                logger.warning(f"Failed to load robots.txt from {robots_url}: {e}")
                # Cache None to avoid repeated failures
                self.parsers[domain] = (None, time.time())
                return None
    
    def get_crawl_delay(self, url):
        """
        Get crawl delay for URL from robots.txt
        
        Args:
            url: URL to check
            
        Returns:
            float: Crawl delay in seconds, or 0 if not specified
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._get_parser(domain)
        
        if parser is None:
            return 0
        
        try:
            # RobotFileParser doesn't expose crawl_delay directly
            # We'll use a default delay if specified
            return getattr(parser, 'crawl_delay', 0) or 0
        except:
            return 0


class RateLimiter:
    """
    Thread-safe rate limiter per domain
    """
    
    def __init__(self):
        self.requests = defaultdict(list)  # domain -> list of request timestamps
        self.lock = Lock()
    
    def can_request(self, domain, max_requests=10, window_seconds=60):
        """
        Check if request is allowed based on rate limit
        
        Args:
            domain: Domain to check
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            
        Returns:
            bool: True if request is allowed
        """
        with self.lock:
            now = time.time()
            requests = self.requests[domain]
            
            # Remove old requests outside window
            requests[:] = [ts for ts in requests if now - ts < window_seconds]
            
            # Check if under limit
            if len(requests) < max_requests:
                requests.append(now)
                return True
            
            return False
    
    def wait_if_needed(self, domain, max_requests=10, window_seconds=60):
        """
        Wait if rate limit would be exceeded
        
        Args:
            domain: Domain to check
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        with self.lock:
            now = time.time()
            requests = self.requests[domain]
            
            # Remove old requests
            requests[:] = [ts for ts in requests if now - ts < window_seconds]
            
            if len(requests) >= max_requests:
                # Calculate wait time
                oldest_request = min(requests)
                wait_time = window_seconds - (now - oldest_request) + 0.1
                
                if wait_time > 0:
                    logger.info(f"Rate limit reached for {domain}, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    
                    # Re-check after wait
                    now = time.time()
                    requests[:] = [ts for ts in requests if now - ts < window_seconds]
            
            requests.append(time.time())






