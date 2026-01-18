#!/usr/bin/env python3
"""
Performance Testing Script for Production News API
Tests TTFB, caching, and concurrent requests
"""

import requests
import time
import json
import threading
from datetime import datetime
import statistics
from urllib.parse import urlencode

# Configuration
API_URL = "http://127.0.0.1:5000"
TEST_ARTICLES = [
    "https://www.bbc.com/news/world",
    "https://www.techcrunch.com/",
    "https://www.theguardian.com/",
]

# Test results
results = {
    "first_requests": [],
    "cached_requests": [],
    "concurrent_requests": [],
    "health_checks": []
}

def test_health():
    """Test health endpoint"""
    print("\n" + "="*70)
    print("TEST 1: Health Check")
    print("="*70)
    
    try:
        start = time.time()
        response = requests.get(f"{API_URL}/health", timeout=5)
        ttfb = (time.time() - start) * 1000
        
        data = response.json()
        print(f"✓ Status: {response.status_code}")
        print(f"✓ TTFB: {ttfb:.1f}ms")
        print(f"✓ Redis: {data.get('redis', {}).get('redis_connected')}")
        print(f"✓ Services: Jina={data.get('services', {}).get('jina')}, Gemini={data.get('services', {}).get('gemini')}")
        
        results["health_checks"].append(ttfb)
        return ttfb
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def test_first_request(url):
    """Test first request (cache miss)"""
    print(f"\nTesting first request for: {url[:50]}...")
    
    try:
        start = time.time()
        response = requests.get(
            f"{API_URL}/api/article",
            params={"url": url},
            timeout=10
        )
        ttfb = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                article = data.get("article", {})
                print(f"  ✓ Title: {article.get('title', 'N/A')[:60]}...")
                print(f"  ✓ Image: {article.get('image_url', 'N/A')[:60]}...")
                print(f"  ✓ Summary: {article.get('summary', 'N/A')[:60]}...")
                print(f"  ✓ TTFB: {ttfb:.1f}ms")
                
                results["first_requests"].append(ttfb)
                return ttfb, url
        else:
            print(f"  ✗ Status code: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    return None, None

def test_cached_request(url):
    """Test repeat request (cache hit)"""
    print(f"\nTesting cached request for: {url[:50]}...")
    
    try:
        start = time.time()
        response = requests.get(
            f"{API_URL}/api/article",
            params={"url": url},
            timeout=10
        )
        ttfb = (time.time() - start) * 1000
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"  ✓ Cached response")
                print(f"  ✓ TTFB: {ttfb:.1f}ms")
                results["cached_requests"].append(ttfb)
                return ttfb
        else:
            print(f"  ✗ Status code: {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    return None

def test_concurrent_requests(url, num_requests=10):
    """Test concurrent requests"""
    print(f"\n" + "="*70)
    print(f"TEST 3: Concurrent Requests ({num_requests} simultaneous)")
    print("="*70)
    
    concurrent_results = []
    lock = threading.Lock()
    
    def fetch():
        try:
            start = time.time()
            response = requests.get(
                f"{API_URL}/api/article",
                params={"url": url},
                timeout=10
            )
            ttfb = (time.time() - start) * 1000
            
            with lock:
                concurrent_results.append(ttfb)
                if response.status_code == 200:
                    print(f"  ✓ Request {len(concurrent_results)}: {ttfb:.1f}ms")
                else:
                    print(f"  ✗ Request {len(concurrent_results)}: Status {response.status_code}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    threads = [threading.Thread(target=fetch) for _ in range(num_requests)]
    
    start_time = time.time()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    total_time = time.time() - start_time
    
    if concurrent_results:
        print(f"\n  Average TTFB: {statistics.mean(concurrent_results):.1f}ms")
        print(f"  Median TTFB: {statistics.median(concurrent_results):.1f}ms")
        print(f"  Min TTFB: {min(concurrent_results):.1f}ms")
        print(f"  Max TTFB: {max(concurrent_results):.1f}ms")
        print(f"  Total Time: {total_time:.1f}s")
        print(f"  Requests/sec: {num_requests/total_time:.1f}")
        
        results["concurrent_requests"] = concurrent_results
    
    return concurrent_results

def print_summary():
    """Print test summary"""
    print("\n" + "="*70)
    print("PERFORMANCE TEST SUMMARY")
    print("="*70)
    
    print("\n📊 Health Checks:")
    if results["health_checks"]:
        print(f"  Average: {statistics.mean(results['health_checks']):.1f}ms")
        print(f"  Max: {max(results['health_checks']):.1f}ms")
    
    print("\n📊 First Requests (Cache Miss):")
    if results["first_requests"]:
        avg = statistics.mean(results["first_requests"])
        print(f"  Average: {avg:.1f}ms")
        print(f"  Target: <200ms")
        print(f"  Status: {'✓ PASS' if avg < 200 else '✗ FAIL'}")
        print(f"  Min: {min(results['first_requests']):.1f}ms")
        print(f"  Max: {max(results['first_requests']):.1f}ms")
    
    print("\n📊 Cached Requests (Cache Hit):")
    if results["cached_requests"]:
        avg = statistics.mean(results["cached_requests"])
        print(f"  Average: {avg:.1f}ms")
        print(f"  Target: <50ms")
        print(f"  Status: {'✓ PASS' if avg < 50 else '⚠ CHECK' if avg < 100 else '✗ SLOW'}")
        print(f"  Min: {min(results['cached_requests']):.1f}ms")
        print(f"  Max: {max(results['cached_requests']):.1f}ms")
    
    print("\n📊 Concurrent Requests:")
    if results["concurrent_requests"]:
        avg = statistics.mean(results["concurrent_requests"])
        print(f"  Average: {avg:.1f}ms")
        print(f"  Min: {min(results['concurrent_requests']):.1f}ms")
        print(f"  Max: {max(results['concurrent_requests']):.1f}ms")
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    if results["first_requests"]:
        avg = statistics.mean(results["first_requests"])
        if avg > 200:
            print("⚠ First request TTFB >200ms:")
            print("  - Check Jina AI response times")
            print("  - Verify network connectivity")
            print("  - Monitor Redis performance")
    
    if results["cached_requests"]:
        avg = statistics.mean(results["cached_requests"])
        if avg > 50:
            print("⚠ Cached request TTFB >50ms:")
            print("  - Check Redis connection performance")
            print("  - Verify Redis memory usage")
            print("  - Monitor server CPU/memory")
    
    print("\n✓ Performance testing complete!")
    print(f"  Timestamp: {datetime.now().isoformat()}")

def main():
    """Run all performance tests"""
    print("="*70)
    print("🚀 PRODUCTION NEWS API - PERFORMANCE TEST SUITE")
    print("="*70)
    print(f"API URL: {API_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    
    # Test 1: Health check
    print("\n" + "="*70)
    print("TEST 1: Health Check & Service Status")
    print("="*70)
    test_health()
    
    # Test 2: First request (cache miss)
    print("\n" + "="*70)
    print("TEST 2: First Requests (Cache Miss)")
    print("="*70)
    urls_to_test = TEST_ARTICLES[:2]  # Test first 2 articles
    cached_urls = []
    for url in urls_to_test:
        ttfb, test_url = test_first_request(url)
        if ttfb:
            cached_urls.append(test_url)
            time.sleep(1)  # Avoid rate limiting
    
    # Test 3: Cached requests
    print("\n" + "="*70)
    print("TEST 3: Cached Requests (Cache Hit)")
    print("="*70)
    for url in cached_urls[:2]:
        test_cached_request(url)
        time.sleep(0.5)
    
    # Test 4: Concurrent requests
    if cached_urls:
        test_concurrent_requests(cached_urls[0], num_requests=5)
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
