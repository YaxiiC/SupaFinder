"""HTTP fetching with rate limiting and caching."""

import time
import httpx
from urllib.parse import urlparse
from collections import defaultdict
from bs4 import BeautifulSoup
import trafilatura

from app.config import REQUESTS_PER_DOMAIN_PER_SEC, REQUEST_TIMEOUT
from app.db import get_cached_page, cache_page


class RateLimiter:
    """Per-domain rate limiter."""
    
    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request: dict[str, float] = defaultdict(float)
    
    def wait(self, domain: str) -> None:
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self.last_request[domain]
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request[domain] = time.time()


class Crawler:
    """HTTP crawler with caching and rate limiting."""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(REQUESTS_PER_DOMAIN_PER_SEC)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc
    
    def fetch(self, url: str, use_cache: bool = True) -> dict:
        """Fetch a URL, using cache if available."""
        if use_cache:
            cached = get_cached_page(url)
            if cached:
                return cached
        
        domain = self._get_domain(url)
        self.rate_limiter.wait(domain)
        
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
                response = client.get(url, headers=self.headers)
                html = response.text
                text_content = self._extract_text(html)
                
                result = {
                    "html": html,
                    "text_content": text_content,
                    "status_code": response.status_code
                }
                
                if use_cache and response.status_code == 200:
                    cache_page(url, html, text_content, response.status_code)
                
                return result
        except Exception as e:
            return {
                "html": "",
                "text_content": "",
                "status_code": 0,
                "error": str(e)
            }
    
    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML."""
        try:
            text = trafilatura.extract(html)
            if text:
                return text
        except Exception:
            pass
        
        # Fallback to BeautifulSoup
        try:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)
        except Exception:
            return ""
    
    def fetch_multiple(self, urls: list[str]) -> list[dict]:
        """Fetch multiple URLs sequentially with rate limiting."""
        results = []
        for url in urls:
            results.append(self.fetch(url))
        return results


# Global crawler instance
crawler = Crawler()

