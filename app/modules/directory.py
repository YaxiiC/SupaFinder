"""Directory page parsing to extract profile URLs."""

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from app.config import DIRECTORY_MIN_PROFILE_LINKS, DIRECTORY_CONSERVATIVE_THRESHOLD


class DirectoryParser:
    """Parse directory pages to find profile URLs."""
    
    def __init__(self):
        # Patterns that indicate a profile page URL (must end with a name/person identifier)
        # These patterns require the URL to end with a person identifier, not a directory
        self.profile_patterns = [
            r"/people/[^/]+$",  # /people/john-smith (not /people/academic-staff/)
            r"/person/[^/]+$",  # /person/jane-doe
            r"/staff/[^/]+$",   # /staff/professor-smith (not /staff/directory/)
            r"/faculty/[^/]+$", # /faculty/dr-jones
            r"/profile/[^/]+$", # /profile/12345-name
            r"/profiles/[^/]+$",  # /profiles/5178-name or profiles.ucl.ac.uk/5178-name
            r"/researcher/[^/]+$", # /researcher/mary-brown
            r"/academic/[^/]+$",   # /academic/prof-wilson
            r"/professor/[^/]+$",  # /professor/dr-taylor
            r"/members?/[^/]+$",   # /member/john-doe (not /members/)
            # HKU Faculty of Education specific: /faculty-academics/ paths
            r"/faculty-academics/[a-z0-9_-]+/?$",  # /faculty-academics/john-smith or /faculty-academics/john-smith/
            # UCL-specific: profiles.ucl.ac.uk/XXXXX-name format (must have number prefix)
            r"profiles\.ucl\.ac\.uk/\d+-[^/]+$",  # Match profiles.ucl.ac.uk/35462-yuanchang-liu
            r"profiles\.[^/]+/[^/]+$",  # Match profiles.domain.com/path (generic fallback)
        ]
        
        # Patterns that indicate directory/listing pages (should be excluded)
        self.directory_patterns = [
            r"/people/?$",  # /people or /people/
            r"/people/[^/]+/",  # /people/academic-staff/ (has trailing slash or more path)
            r"/staff/?$",
            r"/staff/[^/]+/",
            r"/faculty/?$",
            r"/faculty/[^/]+/",
            r"/members/?$",
            r"/members/[^/]+/",
            r"/academic/?$",
            r"/academic/[^/]+/",
            r"/directory",
            r"/list",
            r"/all-",
            r"/browse",
        ]
        
        # Patterns to exclude (strict - reject news, articles, department pages)
        # Note: /faculty-academics/ is NOT excluded - it's a valid profile path pattern
        self.exclude_patterns = [
            r"\.(pdf|doc|docx|ppt|pptx)$",
            r"/news/", r"/article/", r"/articles/", r"/press/", r"/press-release",
            r"/event/", r"/events/", r"/announcement", r"/announcements",
            r"/department-", r"/research-", r"/program/", r"/programme/",
            r"/publication/", r"/publications/", r"/project/", r"/projects/",
            r"/study/", r"/studies/", r"/research/", r"/area/", r"/areas/",
            r"/category/", r"/tag/", r"/blog/",
            r"/discover", r"/discovery", r"/giving/", r"/alumni", r"/about-us",
            r"/contact/", r"/search", r"/filter", r"/browse",
            r"/login",
            r"actu\.", r"news\.", r"\.edu/news", r"\.ac\.uk/news",
            # UCL-specific: exclude URLs that are just "alumni" or "discover" (not profile pages)
            r"profiles\.ucl\.ac\.uk/(alumni|discover|discovery|giving|about-us)(/|$)",
            # Exclude pagination/listing pages for faculty-academics (e.g., /faculty-academics/a-c, /faculty-academics/)
            r"/faculty-academics/?$",  # Just /faculty-academics or /faculty-academics/
            r"/faculty-academics/[a-z]-[a-z]",  # Pagination like /faculty-academics/a-c
        ]
    
    def extract_profile_urls(self, html: str, base_url: str) -> list[str]:
        """Extract profile URLs from a directory page.
        
        Prioritizes links that look like profile pages and filters out
        navigation/listing pages (a-z index, category pages, news pages, etc.).
        """
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(base_url).netloc
        
        profile_urls = set()
        
        # Also check for profiles subdomain (e.g., profiles.ucl.ac.uk if base is ucl.ac.uk)
        base_domain_parts = base_domain.split('.')
        profiles_subdomain = f"profiles.{'.'.join(base_domain_parts[-2:])}" if len(base_domain_parts) >= 2 else None
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(base_url, href)
            parsed_url = urlparse(full_url)
            
            # Must be same domain OR profiles subdomain
            if parsed_url.netloc == base_domain or (profiles_subdomain and parsed_url.netloc == profiles_subdomain):
                # Check if it matches profile patterns (strict - must be a person profile, not directory)
                if self.looks_like_profile_url(full_url):
                    profile_urls.add(full_url)
        
        return list(profile_urls)
    
    def is_directory_like_page(self, text: str, html: str, base_url: str, links_count: int = 0) -> bool:
        """Determine if a page is a directory/listing page or a personal profile page.
        
        Args:
            text: Page text content
            html: Page HTML content
            base_url: Base URL of the page (for resolving relative links)
            links_count: Number of links on the page that look like profile URLs (if 0, will be counted)
        
        Returns:
            True if this looks like a directory page (contains many profile links),
            False if it looks like a personal profile page
        """
        from bs4 import BeautifulSoup
        
        text_lower = text.lower()[:3000]  # Check first 3000 chars
        soup = BeautifulSoup(html, "html.parser")
        
        # Count profile-like links on the page
        if links_count == 0:
            # Count links that look like profile URLs
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if href:
                    full_url = urljoin(base_url, href)
                    if self.looks_like_profile_url(full_url):
                        links_count += 1
        
        # Directory page indicators:
        # 1. Many profile-like links (>= DIRECTORY_MIN_PROFILE_LINKS suggests it's a directory)
        if links_count >= DIRECTORY_MIN_PROFILE_LINKS:
            return True
        
        # 2. Directory-specific text patterns
        directory_indicators = [
            "all members", "all staff", "all faculty", "all people",
            "browse by", "filter by", "search results", "view all",
            "staff directory", "faculty directory", "people directory",
            "member directory", "researcher directory", "academic staff",
            "faculty members", "our people", "our faculty", "our staff"
        ]
        
        if any(indicator in text_lower for indicator in directory_indicators):
            return True
        
        # Personal profile page indicators:
        # 1. H1/title looks like a person's name (not "Directory", "Staff", etc.)
        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(strip=True).lower()
            non_name_words = ["directory", "staff", "faculty", "people", "members", 
                            "browse", "search", "filter", "all"]
            if not any(word in h1_text for word in non_name_words):
                # Check if it looks like a name (2-4 words, capitalized)
                words = h1_text.split()
                if 2 <= len(words) <= 4 and all(w[0].isupper() if w else False for w in words[:3]):
                    return False  # Looks like a name, so it's a profile page
        
        # 2. Contains personal profile sections
        profile_sections = [
            "biography", "research", "publications", "contact", "education",
            "experience", "interests", "teaching", "awards", "grants"
        ]
        section_count = sum(1 for section in profile_sections if section in text_lower)
        if section_count >= 2:
            return False  # Has multiple personal sections, likely a profile page
        
        # 3. Check meta tags for person name
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            og_text = og_title.get("content", "").lower()
            if not any(word in og_text for word in ["directory", "staff", "faculty", "people"]):
                words = og_text.split()
                if 2 <= len(words) <= 4:
                    return False  # og:title looks like a name
        
        # Default: if we have some profile links but not many, it might be a directory
        # But be conservative - if links_count is low, assume it's a profile page
        return links_count >= DIRECTORY_CONSERVATIVE_THRESHOLD  # Threshold: N+ profile links = directory page
    
    def looks_like_profile_url(self, url: str) -> bool:
        """Check if URL looks like a profile page (not a directory/listing page).
        
        This is a more lenient check that allows domain-configurable paths.
        """
        url_lower = url.lower()
        parsed = urlparse(url)
        path = parsed.path
        
        # Exclude certain patterns
        for pattern in self.exclude_patterns:
            if re.search(pattern, url_lower):
                return False
        
        # Exclude directory/listing pages
        for pattern in self.directory_patterns:
            if re.search(pattern, url_lower):
                return False
        
        # Check for /faculty-academics/ pattern (HKU Faculty of Education)
        # Allow both /faculty-academics/name and /faculty-academics/name/
        if re.search(r'^/faculty-academics/[a-z0-9_-]+/?$', path):
            return True
        
        # Match profile patterns (must match exactly - these require a person identifier at the end)
        for pattern in self.profile_patterns:
            if re.search(pattern, url_lower):
                return True
        
        return False
    
    def _is_profile_url(self, url: str) -> bool:
        """Check if URL looks like a profile page (not a directory/listing page).
        
        Alias for looks_like_profile_url for backward compatibility.
        """
        return self.looks_like_profile_url(url)
    
    def find_pagination_links(self, html: str, base_url: str) -> list[str]:
        """Find pagination links to get more profiles."""
        soup = BeautifulSoup(html, "html.parser")
        base_domain = urlparse(base_url).netloc
        
        pagination_urls = set()
        
        # Look for common pagination patterns
        pagination_selectors = [
            "a.page-link",
            "a.pagination-link",
            ".pagination a",
            "a[rel='next']",
            ".pager a",
        ]
        
        for selector in pagination_selectors:
            for link in soup.select(selector):
                href = link.get("href")
                if href:
                    full_url = urljoin(base_url, href)
                    if urlparse(full_url).netloc == base_domain:
                        pagination_urls.add(full_url)
        
        return list(pagination_urls)


# Global parser instance
directory_parser = DirectoryParser()

