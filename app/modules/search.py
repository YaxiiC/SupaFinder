"""Search adapter for finding university pages using Google Custom Search Engine (CSE)."""

import time
import httpx
from collections import defaultdict
from app.config import GOOGLE_CSE_KEY, GOOGLE_CSE_CX


class SearchClient:
    """Search API client using Google Custom Search Engine with rate limiting."""
    
    def __init__(self):
        self.api_key = GOOGLE_CSE_KEY
        self.cx = GOOGLE_CSE_CX
        # Rate limit: 100 requests per minute = ~0.6 seconds per request
        # Use 0.65 seconds to be safe
        self.min_interval = 0.65
        self.last_request_time = 0.0
        self.request_count = defaultdict(int)  # Track requests per minute
        self.request_times = defaultdict(list)  # Track request timestamps
    
    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limit (100 requests per minute)."""
        now = time.time()
        
        # Clean old requests (older than 1 minute)
        cutoff = now - 60.0
        self.request_times['api'] = [t for t in self.request_times['api'] if t > cutoff]
        
        # Check if we're at the limit
        if len(self.request_times['api']) >= 100:
            # Wait until oldest request is more than 1 minute old
            oldest = min(self.request_times['api'])
            wait_time = 60.0 - (now - oldest) + 0.1  # Add small buffer
            if wait_time > 0:
                print(f"  Rate limit reached, waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                now = time.time()
                # Re-clean after waiting
                cutoff = now - 60.0
                self.request_times['api'] = [t for t in self.request_times['api'] if t > cutoff]
        
        # Enforce minimum interval between requests
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        
        self.last_request_time = time.time()
        self.request_times['api'].append(time.time())
    
    def search(self, query: str, num_results: int = 10, max_retries: int = 3) -> list[dict]:
        """Perform a search using Google CSE with rate limiting and retries."""
        if not self.api_key or not self.cx:
            raise ValueError("GOOGLE_CSE_KEY and GOOGLE_CSE_CX must be configured")
        
        # Google CSE API supports up to 10 results per request
        # For more results, we need to paginate
        all_results = []
        max_results = min(num_results, 50)  # Reduced from 100 to limit pagination
        
        # Calculate number of requests needed (10 results per request)
        num_requests = min((max_results + 9) // 10, 5)  # Limit to 5 pages max
        
        for i in range(num_requests):
            start_index = i * 10 + 1
            
            # Rate limiting and retry logic
            for attempt in range(max_retries):
                try:
                    # Wait for rate limit
                    self._wait_for_rate_limit()
                    
                    params = {
                        "key": self.api_key,
                        "cx": self.cx,
                        "q": query,
                        "num": 10,  # Max results per request
                        "start": start_index
                    }
                    
                    response = httpx.get(
                        "https://www.googleapis.com/customsearch/v1",
                        params=params,
                        timeout=30.0
                    )
                    
                    # Handle rate limit errors with exponential backoff
                    if response.status_code == 429:
                        wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                        print(f"  Rate limit exceeded, waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue  # Retry
                    
                    response.raise_for_status()
                    
                    data = response.json()
                    items = data.get("items", [])
                    
                    for item in items:
                        all_results.append({
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", "")
                        })
                    
                    # If we got fewer results than requested, we've reached the end
                    if len(items) < 10:
                        return all_results[:max_results]
                    
                    # Stop if we have enough results
                    if len(all_results) >= max_results:
                        return all_results[:max_results]
                    
                    break  # Success, exit retry loop
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 10
                        print(f"  Rate limit error (429), waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        # If all retries failed for this page, continue to next page
                        if attempt == max_retries - 1:
                            print(f"  Google CSE API error {e.response.status_code} after {max_retries} attempts, skipping page")
                        break  # Exit retry loop, continue to next page
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"  Search error: {e}, skipping page")
                        break  # Exit retry loop, continue to next page
                    time.sleep(1)  # Brief delay before retry
            
        return all_results[:max_results]
    
    def search_site(self, domain: str, query: str, num_results: int = 10) -> list[dict]:
        """Search within a specific site."""
        site_query = f"site:{domain} {query}"
        return self.search(site_query, num_results)
    
    def find_directory_pages(self, domain: str) -> list[dict]:
        """Find staff/faculty directory pages for a university."""
        # Optimized: Reduced queries and result counts to stay within rate limits
        # Include subdomain searches to find profiles on different subdomains
        queries = [
            f"site:{domain} staff directory",
            f"site:{domain} faculty members",
            f"site:profiles.{domain}",  # Most important - direct profiles search
            f"site:{domain} /people/",
            f"site:{domain} /profiles/",
        ]
        
        # Add common subdomain patterns for UK universities (if domain ends with .ac.uk)
        # Google site: search doesn't support wildcards, so we search specific common subdomains
        if domain.endswith('.ac.uk'):
            # Common UK university subdomains
            base = domain.replace('.ac.uk', '')
            common_subdomains = [
                'eng', 'med', 'www', 'www2', 'www3',
                'people', 'staff', 'faculty', 'research',
                'departments', 'dept', 'schools'
            ]
            for subdomain in common_subdomains[:3]:  # Limit to top 3 to save API calls
                queries.append(f"site:{subdomain}.{domain} people")
                queries.append(f"site:{subdomain}.{domain} staff")
        
        all_results = []
        seen_urls = set()
        
        for q in queries:
            results = self.search(q, 5)  # Reduced from 10 to 5 to save API calls
            for r in results:
                if r["link"] not in seen_urls:
                    seen_urls.add(r["link"])
                    all_results.append(r)
        
        return all_results
    
    def find_researcher_profiles(self, domain: str, keywords: list[str]) -> list[dict]:
        """Find researcher profile pages matching keywords (optimized for rate limits)."""
        all_results = []
        seen_urls = set()
        
        # OPTIMIZED Strategy: Prioritize most effective searches to stay within rate limits
        
        # Strategy 1: Combined keywords search (most efficient - 1 query instead of many)
        # This is the most important search
        if len(keywords) > 0:
            # Use top 5 keywords in OR query (reduced from 8)
            keyword_str = " OR ".join(keywords[:5])
            query = f'site:{domain} ({keyword_str}) professor OR "associate professor" OR "assistant professor"'
            results = self.search(query, 10)
            for r in results:
                if r["link"] not in seen_urls:
                    seen_urls.add(r["link"])
                    all_results.append(r)
            
            # Also search without professor requirement (broader)
            query = f'site:{domain} ({keyword_str})'
            results = self.search(query, 10)
            for r in results:
                if r["link"] not in seen_urls:
                    seen_urls.add(r["link"])
                    all_results.append(r)
        
        # Strategy 2: Top 3 individual keywords (reduced from 15)
        # Only search top keywords individually
        for keyword in keywords[:3]:
            query = f'site:{domain} "{keyword}" professor'
            results = self.search(query, 5)
            for r in results:
                if r["link"] not in seen_urls:
                    seen_urls.add(r["link"])
                    all_results.append(r)
        
        # Strategy 3: Medical imaging terms (if relevant)
        # Only search top 2-3 most relevant terms
        medical_terms = ["medical imaging", "biomedical", "radiology"]
        for term in medical_terms[:2]:
            query = f'site:{domain} "{term}"'
            results = self.search(query, 5)
            for r in results:
                if r["link"] not in seen_urls:
                    seen_urls.add(r["link"])
                    all_results.append(r)
        
        return all_results


# Global search client
search_client = SearchClient()

