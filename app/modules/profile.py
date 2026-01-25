"""Profile extraction with rules and LLM fallback."""

import re
from typing import Optional, Tuple, List
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup

from app.schemas import SupervisorProfile, ResearchProfile, University
from app.modules.llm_deepseek import llm_client
from app.config import CORE_THRESHOLD


class ProfileExtractor:
    """Extract supervisor profile data from page content."""
    
    def __init__(self):
        self.email_pattern = re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        )
        # Only include Assistant Professor and above
        self.acceptable_titles = [
            "Professor", "Prof.", "Associate Professor", "Assistant Professor", "Reader"
        ]
        
        # Titles to exclude
        self.excluded_titles = [
            "PhD Student", "Ph.D. Student", "Doctoral Student", "Graduate Student",
            "Postdoc", "Postdoctoral", "Post-doctoral", "Post Doctoral",
            "Research Fellow", "Junior Research Fellow", "Senior Research Fellow",
            "Research Associate", "Research Assistant", "Teaching Assistant",
            "Lecturer", "Senior Lecturer",  # Exclude lecturers as they're typically not supervisors
            "Emeritus Professor", "Emeritus", "Professor Emeritus"  # Exclude emeritus professors
        ]
    
    def extract(
        self,
        html: str,
        text_content: str,
        url: str,
        university: University,
        research_profile: ResearchProfile,
        debug: bool = False,
        allow_student_postdoc: bool = False,
        allow_low_fit_score: bool = False
    ) -> Tuple[Optional[SupervisorProfile], Optional[str]]:
        """Extract supervisor profile from page content.
        
        Returns:
            Tuple of (profile, failure_reason). 
            If profile is not None, failure_reason is None.
            If profile is None, failure_reason indicates why extraction failed.
        """
        skip_reason = None
        
        # CRITICAL: Validate that URL domain matches university domain
        # This prevents assigning profiles from other universities to the wrong institution
        if not self._validate_url_domain(url, university.domain):
            skip_reason = "domain_mismatch"
            if debug:
                print(f"  [DEBUG] Skipped {url[:60]}: domain mismatch")
            return None, skip_reason  # URL domain doesn't match university, skip this profile
        
        soup = BeautifulSoup(html, "html.parser")
        
        # For short text content, try to extract more from HTML directly
        # This is especially useful for structured pages like UCL profiles
        if not text_content or len(text_content.strip()) < 100:
            # Try to get more text from HTML for better extraction
            # Extract text from common content areas
            content_selectors = [
                "main", "article", ".content", ".main-content", 
                "#content", ".profile-content", ".person-details"
            ]
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    additional_text = " ".join([elem.get_text(strip=True) for elem in elements])
                    if additional_text and len(additional_text) > len(text_content):
                        text_content = additional_text
                        break
        
        # Extract name (usually in h1 or title)
        name = self._extract_name(soup, text_content, url)
        if not name:
            skip_reason = "no_name"
            # Try to get more context about why name extraction failed
            h1 = soup.find("h1")
            title_tag = soup.find("title")
            og_title = soup.find("meta", property="og:title")
            has_h1 = h1 is not None
            has_title = title_tag is not None
            has_og_title = og_title is not None
            text_length = len(text_content) if text_content else 0
            
            reason_detail = f"no_name (h1={has_h1}, title={has_title}, og_title={has_og_title}, text_len={text_length})"
            if debug:
                print(f"  [DEBUG] Skipped {url[:60]}: {reason_detail}")
            return None, reason_detail
        
        # Clean and parse name - remove any URLs that might have been extracted
        name = self._clean_name(name)
        
        # Validate name is not a URL or invalid
        if not name or self._is_url_or_invalid(name):
            skip_reason = f"invalid_name (extracted='{name[:50] if name else 'None'}')"
            if debug:
                print(f"  [DEBUG] Skipped {url[:60]}: {skip_reason}")
            return None, skip_reason
        
        first_name, last_name = self._parse_name(name)
        
        # Extract email (rule-based, optional - don't reject if missing)
        email, email_confidence, email_evidence = self._extract_email(html, text_content)
        
        # REMOVED: Email-name consistency check - too strict, email formats vary
        
        # Extract title (optional - don't reject if missing)
        title = self._extract_title(text_content)
        
        # Check if page is blank or has insufficient content
        # Blank pages typically have only name, title, and basic contact info but no research content
        if self._is_blank_profile_page(text_content, soup, url):
            skip_reason = "blank_profile_page"
            if debug:
                print(f"  [DEBUG] Skipped {url[:60]}: blank profile page (insufficient content)")
            return None, skip_reason
        
        # Check if page contains academic title indicators
        # Required titles: Prof, Dr, Professor, Reader, Lecturer, Research Fellow, etc.
        text_lower = text_content.lower()
        url_lower = url.lower()
        is_profiles_subdomain = "profiles." in url_lower and "/" in url_lower.split("profiles.")[-1][:50]
        is_likely_profile_url = is_profiles_subdomain or self._is_valid_profile_url(url)
        
        # Check for academic titles in text
        academic_title_patterns = [
            r'\bprof\b', r'\bprofessor\b', r'\bdr\.?\b', r'\bdoctor\b',
            r'\breader\b', r'\blecturer\b', r'\bsenior\s+lecturer\b',
            r'\bresearch\s+fellow\b', r'\bsenior\s+research\s+fellow\b',
            r'\bprincipal\s+investigator\b', r'\bpi\b', r'\bgroup\s+leader\b',
            r'\blab\s+head\b', r'\bdirector\b', r'\bhead\s+of\b'
        ]
        has_academic_title = any(re.search(pattern, text_lower) for pattern in academic_title_patterns)
        
        # Check for PI indicators (Principal Investigator, Group Leader, etc.)
        pi_indicators = [
            r'\bprincipal\s+investigator\b', r'\bpi\b', r'\bgroup\s+leader\b',
            r'\blab\s+head\b', r'\blab\s+director\b', r'\bresearch\s+group\s+leader\b'
        ]
        is_pi = any(re.search(pattern, text_lower) for pattern in pi_indicators)
        
        # If no academic title found, check if it's a valid PI or if URL suggests it's a profile
        if not has_academic_title and not is_pi:
            # For profile URLs, be more lenient - might have title in structured data
            if not is_likely_profile_url:
                skip_reason = "no_academic_title"
                if debug:
                    print(f"  [DEBUG] Skipped {url[:60]}: no academic title found")
                return None, skip_reason
        
        # Check for excluded titles (student/postdoc) - but allow if it's a PI or if allow_student_postdoc is True
        if not is_pi and not allow_student_postdoc:
            excluded_patterns = [
                r'\bphd\s+student\b', r'\bph\.?d\.?\s+student\b',
                r'\bdoctoral\s+student\b', r'\bgraduate\s+student\b',
                r'\bpostdoc\b', r'\bpost-?doc\b', r'\bpostdoctoral\b'
            ]
            if any(re.search(pattern, text_lower) for pattern in excluded_patterns):
                skip_reason = "student_postdoc"
                if debug:
                    print(f"  [DEBUG] Skipped {url[:60]}: student/postdoc position")
                return None, skip_reason
        
        # Extract homepage/publications links
        homepage_url = self._extract_homepage(soup, url)
        publications_links = self._extract_publications_links(soup, url)
        
        # Use LLM for keywords and fit score
        extraction = llm_client.extract_profile_keywords(text_content, research_profile)
        
        # Check again for PI status (after LLM extraction, might have more context)
        text_lower = text_content.lower()
        pi_indicators = [
            r'\bprincipal\s+investigator\b', r'\bpi\b', r'\bgroup\s+leader\b',
            r'\blab\s+head\b', r'\blab\s+director\b', r'\bresearch\s+group\s+leader\b'
        ]
        is_pi = any(re.search(pattern, text_lower) for pattern in pi_indicators)
        
        # SIMPLIFIED: Only reject if fit_score is extremely low (< 0.1) or negative keywords found
        # BUT: Allow PI even with low fit_score
        # Let the ranking/scoring system handle relevance filtering later
        text_lower = text_content.lower()
        negative_keywords = [k.lower() for k in research_profile.negative_keywords]
        has_negative_keyword = any(nk in text_lower for nk in negative_keywords)
        
        if has_negative_keyword:
            skip_reason = "negative_keyword"
            if debug:
                print(f"  [DEBUG] Skipped {url[:60]}: contains negative keyword")
            return None, skip_reason
        
        # Only reject if fit_score is extremely low (< 0.1) - BUT allow PI
        # PI might have low fit_score but still be valid supervisors
        # If allow_low_fit_score=True (manual addition), always allow extraction
        if extraction.fit_score < 0.1 and not is_pi and not allow_low_fit_score:
            skip_reason = f"very_low_fit_score_{extraction.fit_score:.2f}"
            if debug:
                print(f"  [DEBUG] Skipped {url[:60]}: very low fit_score {extraction.fit_score:.2f}")
            return None, skip_reason
        
        # Generate Scholar search URL
        scholar_url = self._generate_scholar_url(name)
        
        # Build evidence snippets
        evidence = []
        if email_evidence:
            evidence.append(f"Email: {email_evidence}")
        
        # Build notes - include PI status if detected
        notes_parts = []
        if extraction.one_sentence_reason:
            notes_parts.append(extraction.one_sentence_reason)
        if is_pi:
            notes_parts.append("Principal Investigator/Group Leader")
        notes = " | ".join(notes_parts) if notes_parts else None
        
        profile = SupervisorProfile(
            name=name,
            first_name=first_name,
            last_name=last_name,
            title=title,
            institution=university.institution,
            country=university.country,
            region=university.region,
            qs_rank=university.qs_rank,
            email=email,
            email_confidence=email_confidence,
            profile_url=url,
            homepage_url=homepage_url,
            keywords=extraction.keywords,
            publications_links=publications_links,
            scholar_search_url=scholar_url,
            fit_score=extraction.fit_score,
            tier="Core" if extraction.fit_score >= CORE_THRESHOLD else "Adjacent",
            source_url=url,
            evidence_snippets=evidence,
            notes=notes
        )
        return profile, None  # Success, no failure reason
    
    def _extract_name(self, soup: BeautifulSoup, text_content: str, url: str) -> Optional[str]:
        """Extract name from page with multiple strategies."""
        # First, check if this is actually a person's profile page (not a directory/department page)
        if not self._is_person_profile_page(soup, text_content, url):
            return None
        
        # Strategy 1: Try h1 first (most common)
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text(strip=True)
            # Explicitly reject common non-name words
            text_lower = text.lower().strip()
            reject_words = [
                "alumni", "discovery", "discover", "giving", "about", "home", "contact",
                "visiting", "current", "doctoral", "students", "student", "fellows",
                "associates", "assistants", "emeritus", "adjunct",
                # Common research topic words that are NOT names
                "music", "covid", "covid-19", "coronavirus", "pandemic",
                "therapy", "intervention", "treatment", "disease", "disorder",
                "education", "research", "study", "analysis", "method",
                "theory", "practice", "approach", "framework", "model",
                "health", "medicine", "clinical", "medical", "patient",
                "learning", "teaching", "instruction", "curriculum",
                "project", "program", "initiative", "collaboration"
            ]
            if text_lower in reject_words or any(word in text_lower for word in ["visiting ", "current ", "doctoral student", "sts"]):
                return None
            # Filter out generic titles
            if (len(text) < 100 and 
                not any(w in text.lower() for w in ["directory", "staff", "faculty", "department", "home", "welcome", "about us"]) and
                self._looks_like_name(text)):
                return text
        
        # Strategy 2: Try meta tags
        for prop in ["og:title", "twitter:title"]:
            meta = soup.find("meta", property=prop)
            if meta and meta.get("content"):
                text = meta["content"].strip()
                if self._looks_like_name(text):
                    return text
        
        # Strategy 3: Try title tag
        title = soup.find("title")
        if title:
            text = title.get_text(strip=True)
            # Clean common suffixes
            for sep in ["|", "-", "–", ":", "|"]:
                if sep in text:
                    text = text.split(sep)[0].strip()
            # Explicitly reject common non-name words
            text_lower = text.lower().strip()
            reject_words = [
                "alumni", "discovery", "discover", "giving", "about", "home", "contact",
                "visiting", "current", "doctoral", "students", "student", "fellows",
                "associates", "assistants", "emeritus", "adjunct",
                # Common research topic words that are NOT names
                "music", "covid", "covid-19", "coronavirus", "pandemic",
                "therapy", "intervention", "treatment", "disease", "disorder",
                "education", "research", "study", "analysis", "method",
                "theory", "practice", "approach", "framework", "model",
                "health", "medicine", "clinical", "medical", "patient",
                "learning", "teaching", "instruction", "curriculum",
                "project", "program", "initiative", "collaboration"
            ]
            if text_lower in reject_words or any(word in text_lower for word in ["visiting ", "current ", "doctoral student", "sts"]):
                return None
            if len(text) < 60 and self._looks_like_name(text):
                return text
        
        # Strategy 4: Look for name patterns in structured data
        # Try schema.org Person
        person_name = soup.find(attrs={"itemtype": re.compile(r".*Person", re.I)})
        if person_name:
            name_elem = person_name.find(attrs={"itemprop": "name"})
            if name_elem:
                text = name_elem.get_text(strip=True)
                if self._looks_like_name(text):
                    return text
        
        # Strategy 5: Look for common name patterns in text (e.g., "Dr. John Smith")
        # More specific pattern to avoid matching research terms
        name_pattern = re.compile(
            r'\b(?:Dr\.?|Prof\.?|Professor)\s+([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,2})\b'
        )
        matches = name_pattern.finditer(text_content[:2000])  # Check first 2000 chars
        for match in matches:
            potential_name = match.group(1).strip()
            # Additional validation: name should be 2-4 words, not contain research terms
            words = potential_name.split()
            if 2 <= len(words) <= 4 and self._looks_like_name(potential_name):
                # Double check it's not a research phrase
                if not any(term in potential_name.lower() for term in 
                          ["medical", "imaging", "analysis", "image", "research", "study"]):
                    return potential_name
        
        return None
    
    def _looks_like_name(self, text: str) -> bool:
        """Check if text looks like a person's name."""
        if not text or len(text) < 2:
            return False
        
        # Too long to be a name
        if len(text) > 80:
            return False
        
        # Should contain letters
        if not re.search(r'[A-Za-z]', text):
            return False
        
        # Should not be all caps (unless very short)
        if text.isupper() and len(text) > 10:
            return False
        
        # Should not contain common non-name words (only the most obvious ones)
        non_name_words = [
            "university", "college", "department", "school", "institute",
            "faculty", "staff", "directory", "home", "welcome", "about",
            "contact", "profile", "page", "members", "people",
            "center", "centre", "program", "programme", "course",
            "news", "events", "announcements", "search", "find",
            "browse", "list", "all", "view", "show", "more",
            "alumni", "discovery", "discover", "giving", "about-us",
            "visiting", "current", "doctoral", "students", "student",
            "postdoctoral", "postdoc", "fellow", "fellows", "research fellow",
            "associate", "assistant", "emeritus", "adjunct",
            # Common research topic words that are NOT names
            "music", "covid", "covid-19", "coronavirus", "pandemic",
            "therapy", "intervention", "treatment", "disease", "disorder",
            "education", "research", "study", "analysis", "method",
            "theory", "practice", "approach", "framework", "model",
            "system", "technology", "application", "development",
            "learning", "teaching", "instruction", "curriculum",
            "health", "medicine", "clinical", "medical", "patient",
            "publication", "journal", "article", "paper", "conference",
            "project", "program", "initiative", "collaboration",
            # Common nouns that are clearly not names
            "service", "support", "help", "information", "resources",
            "events", "calendar", "schedule", "location", "address",
            "phone", "email", "website", "link", "download",
            "publication", "publications", "grants", "funding",
            # Academic/administrative terms
            "admission", "application", "registration", "enrollment",
            "tuition", "scholarship", "financial", "aid", "support"
        ]
        text_lower = text.lower()
        if any(word in text_lower for word in non_name_words):
            return False
        
        # Additional check: if it's a single word, reject common nouns
        words = text_lower.split()
        if len(words) == 1:
            single_word_blacklist = [
                "music", "covid", "therapy", "education", "research",
                "study", "analysis", "health", "medicine", "clinical",
                "treatment", "intervention", "patient", "disease",
                "disorder", "learning", "teaching", "method", "theory",
                "practice", "approach", "framework", "model", "system",
                "technology", "application", "development", "project",
                "program", "initiative", "collaboration", "service",
                "support", "help", "information", "resources", "news",
                "events", "publication", "publications", "grants",
                "funding", "admission", "application", "registration"
            ]
            if words[0] in single_word_blacklist:
                return False
        
        # Reject academic/program names (e.g., "Taught Masters Mechanical Engineering")
        academic_terms = [
            "taught", "masters", "bachelor", "beng", "meng", "msc", "phd",
            "mechanical engineering", "electronic engineering", "civil engineering",
            "electrical engineering", "computer engineering", "aerospace engineering",
            "hydrodynamics", "lab", "laboratory", "lab", "studentship", "studentships",
            "student support", "accessibility", "links", "general engineering",
            "integrated", "comfort", "engineering", "mediacom", "support",
            "fellowship", "fellowships", "scholarship", "scholarships",
            # Directory/category terms
            "visiting", "current", "doctoral students", "doctoral student",
            "postdoctoral", "fellows", "associates", "assistants", "emeritus",
            "adjunct", "affiliated", "honorary"
        ]
        if any(term in text_lower for term in academic_terms):
            return False
        
        # Reject if contains too many commas (likely a list or description)
        if text.count(',') >= 2:
            return False
        
        # Reject if contains common academic phrases
        academic_phrases = [
            "mechanical engineering", "electronic engineering", "general engineering",
            "student support", "phd studentship", "accessibility links",
            "integrated comfort engineering", "hydrodynamics lab",
            # Directory/category phrases
            "visiting", "current doctoral students", "current doctoral student",
            "doctoral students", "postdoctoral fellows", "research associates",
            "visiting scholars", "visiting professors", "affiliated faculty"
        ]
        for phrase in academic_phrases:
            if phrase in text_lower:
                return False
        
        # Reject if it's all uppercase and short (likely an acronym)
        if text.isupper() and len(text) <= 6:
            return False
        
        # Reject if it looks like an acronym (all caps, 2-6 chars)
        if re.match(r'^[A-Z]{2,6}$', text.strip()):
            return False
        
        # REMOVED: Research keywords check - too strict, might reject valid names
        # REMOVED: Navigation/action words check - too strict
        
        # Should have at least one space (first + last name)
        # RELAXED: Allow single-word names if they look valid (e.g., from structured data)
        words = text.split()
        if len(words) == 1:
            # For single-word names, be very strict - reject common non-name words
            # Check if it's an acronym or too short
            if len(text) <= 3 or text.isupper():
                return False
            # Reject common single-word navigation/page titles
            common_single_words = [
                "alumni", "discovery", "discover", "giving", "about", 
                "home", "contact", "search", "directory", "profile",
                "visiting", "current", "doctoral", "students", "student",
                "fellows", "associates", "assistants", "emeritus", "adjunct"
            ]
            if text.lower() in common_single_words:
                return False
            # Allow single-word names if they're reasonable length and capitalized
            # But be more strict - require at least 5 chars and proper capitalization
            if len(text) >= 5 and text[0].isupper() and not text.isupper():
                return True
            return False
        elif len(words) >= 2:
            # Multiple words - at least first should be capitalized
            # All words should start with capital (for proper names)
            if not all(word and word[0].isupper() for word in words[:3]):
                return False
            # Should not be a sentence or phrase
            if len(words) > 4:  # Too many words suggests it's not just a name
                return False
            # Each word should be reasonable length (2-20 chars typically)
            if any(len(word) > 20 or len(word) < 1 for word in words[:4]):
                return False
            # Check for common research phrases
            text_joined = " ".join(words).lower()
            research_phrases = ["medical image", "image analysis", "machine learning",
                              "biomedical engineering", "deep learning"]
            if any(phrase in text_joined for phrase in research_phrases):
                return False
            return True
        
        return True
    
    def _is_valid_profile_url(self, url: str) -> bool:
        """Check if URL looks like a valid personal profile page (not news/department/article)."""
        url_lower = url.lower()
        
        # STRICT: Exclude news, articles, department pages, etc.
        # Also exclude URLs that contain these words as standalone paths (with or without trailing slash)
        exclude_patterns = [
            r'/news/', r'/article/', r'/articles/', r'/press/', r'/press-release',
            r'/event/', r'/events/', r'/announcement', r'/announcements',
            r'/department-', r'/research-', r'/program/', r'/programme/',
            r'/publication/', r'/publications/', r'/project/', r'/projects/',
            r'/study/', r'/studies/', r'/research/', r'/area/', r'/areas/',
            r'/category/', r'/tag/', r'/blog/', r'/blog/',
            r'/discover', r'/discovery', r'/giving/', r'/alumni', r'/about-us',
            r'/contact/', r'/search', r'/filter', r'/browse',
            r'actu\.', r'news\.', r'\.edu/news', r'\.ac\.uk/news',
            # UCL-specific: exclude URLs that are just "alumni" or "discover" (not profile pages)
            r'profiles\.ucl\.ac\.uk/(alumni|discover|discovery|giving|about-us)(/|$)',
            # Additional news/article patterns
            r'news\.[^/]+/',  # news.domain.com
            r'\.edu/news/', r'\.ac\.uk/news/', r'\.edu/blog/', r'\.ac\.uk/blog/',
            r'/story/', r'/stories/', r'/post/', r'/posts/',
            r'/magazine/', r'/mag/', r'/update/', r'/updates/',
            r'/media/', r'/press/', r'/media-center/', r'/communications/',
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, url_lower):
                return False
        
        # POSITIVE: Must match profile patterns
        # Added /profiles/ pattern (e.g., profiles.ucl.ac.uk/5178-name)
        profile_url_patterns = [
            r'/people/[^/]+$', r'/person/[^/]+$', r'/staff/[^/]+$',
            r'/faculty/[^/]+$', r'/member/[^/]+$', r'/profile/[^/]+$',
            r'/profiles/[^/]+$',  # Added for sites like profiles.ucl.ac.uk
            r'/researcher/[^/]+$', r'/academic/[^/]+$', r'/professor/[^/]+$',
            r'/team/[^/]+$',  # Some sites use /team/name
            # UCL-specific: profiles.ucl.ac.uk/XXXXX-name format (must have number prefix)
            r'profiles\.ucl\.ac\.uk/\d+-[^/]+$',  # Match profiles.ucl.ac.uk/35462-yuanchang-liu
            r'profiles\.[^/]+/[^/]+$'  # Match profiles.domain.com/path (generic fallback)
        ]
        
        # URL should match at least one profile pattern
        is_likely_profile_url = any(re.search(pattern, url_lower) for pattern in profile_url_patterns)
        
        return is_likely_profile_url
    
    def _validate_name_email_consistency(self, name: str, email: str) -> bool:
        """Validate that the email's local part matches the name (rough check)."""
        if not name or not email:
            return True  # If missing, can't validate, but don't reject
        
        # Extract local part (before @)
        email_local = email.split('@')[0].lower()
        
        # Extract name parts (first and last)
        name_parts = [p.lower() for p in name.split() if len(p) > 1]
        
        if len(name_parts) < 2:
            return True  # Can't validate single-word names, allow them
        
        first_name = name_parts[0]
        last_name = name_parts[-1]
        
        # Check if email contains parts of the name
        # Common patterns: firstname.lastname, firstname_lastname, f.lastname, etc.
        # Allow partial matches (at least first name or last name)
        first_in_email = first_name[:3] in email_local or first_name in email_local
        last_in_email = last_name[:3] in email_local or last_name in email_local
        
        # Reject ONLY if email is clearly generic (webmaster, admin, etc.)
        # Otherwise be more lenient - allow if not clearly wrong
        if any(x in email_local for x in ['webmaster', 'admin', 'info', 'contact', 'noreply', 'enquiry']):
            return False  # Reject generic emails
        
        # If email is very short (< 3 chars), likely wrong
        if len(email_local) < 3:
            return False
        
        # Otherwise, be lenient - allow even if name doesn't perfectly match email
        # (email might use different format, initials, etc.)
        return True
    
    def _is_person_profile_page(self, soup: BeautifulSoup, text_content: str, url: str) -> bool:
        """Check if this page is actually a person's profile page, not a directory/department page.
        
        SIMPLIFIED: Be more lenient - only reject clear directory pages.
        """
        text_lower = text_content.lower()
        url_lower = url.lower()
        
        # Strong indicators this is NOT a person's page (directory/listing page)
        directory_indicators = [
            "all members", "all staff", "all faculty", "all people",
            "browse by", "filter by", "search results", "view all",
            "staff directory", "faculty directory",
            "people directory", "member directory", "researcher directory",
            "visiting", "current doctoral students", "doctoral students",
            "postdoctoral fellows", "research associates", "visiting scholars",
            "visiting professors", "affiliated faculty", "honorary"
        ]
        
        first_chunk = text_lower[:2000]
        if any(indicator in first_chunk for indicator in directory_indicators):
            # Check if URL also looks like directory (not a person page)
            if any(pattern in url_lower for pattern in ['/directory', '/people/?$', '/staff/?$', '/faculty/?$']):
                return False
        
        # Check for many names/links (likely a directory)
        name_patterns = re.findall(r'\b(?:Dr\.?|Prof\.?|Professor)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b', text_content[:3000])
        if len(name_patterns) > 15:  # Many names = directory
            return False
        
        # If URL looks like a profile URL, trust it
        if self._is_valid_profile_url(url) or "profiles." in url_lower:
            return True
        
        # Default: be lenient - accept if not clearly a directory
        return True
    
    def _clean_name(self, name: str) -> str:
        """Clean extracted name."""
        if not name:
            return ""
        
        # Remove extra whitespace
        name = " ".join(name.split())
        
        # Remove common prefixes (case-insensitive, anywhere in the string)
        prefixes = ["Dr.", "Dr", "Prof.", "Prof", "Professor", "Mr.", "Mr", "Mrs.", "Mrs", "Ms.", "Ms"]
        for prefix in prefixes:
            # Remove from start
            if name.lower().startswith(prefix.lower() + " "):
                name = name[len(prefix):].strip()
            elif name.lower().startswith(prefix.lower()):
                name = name[len(prefix):].strip()
            # Also remove if it appears anywhere (e.g., "Professor John Smith" -> "John Smith")
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(prefix) + r'\b'
            name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
        
        # Remove "essor" if it appears at the start (leftover from "Professor")
        if name.lower().startswith("essor "):
            name = name[6:].strip()
        elif name.lower().startswith("essor"):
            name = name[5:].strip()
        
        # Remove common suffixes
        suffixes = ["PhD", "Ph.D.", "MD", "Jr.", "Jr", "Sr.", "Sr", "III", "II", "IV"]
        for suffix in suffixes:
            if name.endswith(" " + suffix):
                name = name[:-len(suffix)-1].strip()
            elif name.endswith(suffix):
                name = name[:-len(suffix)].strip()
        
        # Remove email addresses if accidentally included
        name = re.sub(r'\S+@\S+', '', name).strip()
        
        # Remove URLs if accidentally included (more thorough)
        name = re.sub(r'https?://[^\s]+', '', name)
        name = re.sub(r'www\.[^\s]+', '', name)
        name = re.sub(r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?', '', name)  # Remove domain-like patterns
        
        # Remove special characters except spaces, hyphens, and apostrophes
        name = re.sub(r'[^\w\s\-\']', '', name)
        
        # Clean up multiple spaces
        name = " ".join(name.split())
        
        return name.strip()
    
    def _is_url_or_invalid(self, text: str) -> bool:
        """Check if text is a URL or invalid name."""
        if not text or len(text) < 2:
            return True
        
        text_lower = text.lower()
        
        # Check for URL patterns
        url_patterns = [
            r'https?://',
            r'www\.',
            r'\.(com|org|edu|ac|uk|gov|net)',
            r'/[a-z]',  # Contains path-like patterns
        ]
        
        for pattern in url_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Check if it's too long (likely not a name)
        if len(text) > 100:
            return True
        
        # Check if it contains too many special patterns that suggest it's not a name
        if re.search(r'\d{4,}', text):  # Contains long numbers
            return True
        
        return False
    
    def _parse_name(self, name: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse name into first name and last name."""
        if not name:
            return None, None
        
        name = name.strip()
        if not name:
            return None, None
        
        # Split by spaces
        parts = name.split()
        
        if len(parts) == 0:
            return None, None
        elif len(parts) == 1:
            # Single name - assume it's last name
            return None, parts[0]
        elif len(parts) == 2:
            # First Last
            return parts[0], parts[1]
        else:
            # Multiple parts - common patterns:
            # "First Middle Last" -> First, Last
            # "First Last1 Last2" -> First, "Last1 Last2"
            # "First M. Last" -> First, Last
            
            # If middle initial (single letter or letter + period)
            if len(parts) == 3 and len(parts[1]) <= 2:
                return parts[0], parts[2]
            
            # Otherwise, take first as first name, rest as last name
            return parts[0], " ".join(parts[1:])
    
    def _extract_email(self, html: str, text: str) -> Tuple[Optional[str], str, str]:
        """Extract email from page with evidence."""
        # Check for mailto links first (high confidence)
        mailto_match = re.search(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html)
        if mailto_match:
            email = mailto_match.group(1)
            return email, "high", f"mailto:{email}"
        
        # Check for visible email in text
        emails = self.email_pattern.findall(text)
        # Filter out common non-personal emails
        filtered = [e for e in emails if not any(x in e.lower() for x in ["noreply", "info@", "admin@", "contact@", "enquir"])]
        
        if filtered:
            email = filtered[0]
            # Find context around email for evidence
            idx = text.find(email)
            start = max(0, idx - 30)
            end = min(len(text), idx + len(email) + 30)
            evidence = text[start:end].strip()
            return email, "medium", evidence
        
        return None, "none", ""
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract academic title - only the title itself, not surrounding text."""
        text_lower = text.lower()
        
        # First check for acceptable titles (in order of specificity - longest first)
        # Sort by length descending to match longest titles first
        sorted_titles = sorted(self.acceptable_titles, key=len, reverse=True)
        
        for title in sorted_titles:
            title_lower = title.lower()
            if title_lower in text_lower:
                # Find the position of the title
                idx = text_lower.find(title_lower)
                
                # Extract just the title word/phrase, not following text
                # Look for word boundaries
                pattern = r'\b' + re.escape(title) + r'\b'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Return just the matched title, not additional text
                    return title
                
                # Fallback: if pattern matching fails, return the title itself
                return title
        
        return None
    
    def _is_blank_profile_page(self, text_content: str, soup: BeautifulSoup, url: str) -> bool:
        """Check if this is a blank profile page with insufficient content.
        
        Blank pages typically have:
        - Only name, title, email, basic contact info
        - No research keywords, publications, biography, research interests
        - Very short content (< 300 characters of meaningful text)
        - No research-related sections
        
        Examples of blank pages:
        - https://medicine-psychology.anu.edu.au/people/dr-kerrie-aust
        - https://www.liverpool.ac.uk/people/yu-lin-lu
        - https://www.mgmt.ucl.ac.uk/people/viethungly
        """
        text_lower = text_content.lower()
        text_length = len(text_content.strip())
        
        # Remove common navigation/menu text to get actual content length
        navigation_keywords = [
            "skip to main content", "menu", "navigation", "search", "contact us", 
            "about us", "home", "staff", "news", "events", "alumni", "current students",
            "study", "research", "people", "services", "our impact", "partner with us",
            "job vacancies", "toggle navigation", "blog", "contact", "advanced search",
            "freedom of information", "accessibility", "privacy", "cookies", "disclaimer"
        ]
        content_text = text_content
        for nav_keyword in navigation_keywords:
            content_text = content_text.replace(nav_keyword, "")
        meaningful_length = len(content_text.strip())
        
        # If meaningful content is very short, likely blank
        if meaningful_length < 300:
            return True
        
        # Check for research-related content indicators
        research_indicators = [
            "research", "publication", "biography", "bio", "interest", "expertise",
            "field", "area", "focus", "project", "grant", "award", "education",
            "experience", "background", "work", "study", "investigation", "method",
            "analysis", "theory", "model", "approach", "contribution", "journal",
            "conference", "paper", "article", "book", "chapter", "thesis", "dissertation",
            "teaching", "supervision", "student", "phd", "doctoral", "postgraduate"
        ]
        
        # Count research indicators
        research_indicator_count = sum(1 for indicator in research_indicators if indicator in text_lower)
        
        # If very few research indicators and short content, likely blank
        if research_indicator_count < 3 and meaningful_length < 500:
            return True
        
        # Check if page has meaningful content sections
        # Look for common profile sections that indicate substantial content
        content_sections = soup.find_all(['section', 'div', 'article'], class_=re.compile(
            r'biography|bio|research|publication|interest|expertise|education|experience|background|profile-content|person-details|content',
            re.I
        ))
        
        # Also check for headings that indicate content sections
        content_headings = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(
            r'research|publication|biography|interest|expertise|education|experience|background|teaching|supervision',
            re.I
        ))
        
        # If no content sections/headings found and text is short, likely blank
        if len(content_sections) == 0 and len(content_headings) == 0 and meaningful_length < 400:
            return True
        
        # Check if text is mostly navigation/menu items
        navigation_count = sum(1 for keyword in navigation_keywords if keyword in text_lower)
        
        # If mostly navigation and very little actual content, likely blank
        if navigation_count > 8 and meaningful_length < 500:
            return True
        
        # Check for pages that only have name, title, email, and affiliation
        # These are typically blank pages (e.g., Teaching Assistant pages with no research content)
        basic_info_patterns = [
            r'\bdr\s+[a-z\s]+\b',  # Name
            r'\bprofessor\b|\bprof\b|\blecturer\b|\bteaching\s+assistant\b',  # Title
            r'[a-z]+@[a-z\.]+\.[a-z]+',  # Email
            r'\buniversity\b|\binstitution\b|\bschool\b|\bdepartment\b'  # Affiliation
        ]
        
        # Count how many basic info patterns are present
        basic_info_matches = sum(1 for pattern in basic_info_patterns if re.search(pattern, text_lower))
        
        # STRICT: If page has basic info (name, title, email) but no research content, it's blank
        # This catches pages like https://www.mgmt.ucl.ac.uk/people/viethungly
        if basic_info_matches >= 2:  # At least name/title and email
            # Check if there's substantial research content beyond basic info
            # If meaningful length is short and research indicators are few, it's blank
            if meaningful_length < 500 and research_indicator_count < 2:
                return True
            # Even if length is OK, if research indicators are very few, likely blank
            if meaningful_length < 800 and research_indicator_count < 1:
                return True
        
        # Additional check: If page only contains name, title, email, and navigation,
        # and has no paragraphs or substantial text blocks, it's blank
        paragraphs = soup.find_all(['p', 'div'], class_=re.compile(r'content|bio|description|about', re.I))
        paragraph_text = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        # If no substantial paragraphs and content is minimal, likely blank
        if len(paragraph_text.strip()) < 200 and meaningful_length < 600 and research_indicator_count < 2:
            return True
        
        return False
    
    def _is_acceptable_title(self, text_content: str, extracted_title: Optional[str], university: Optional[University] = None) -> bool:
        """Check if the person has an acceptable title (Assistant Professor and above).
        
        For UK universities, also accepts Reader and Senior Lecturer as these are valid supervisor positions.
        """
        text_lower = text_content.lower()
        
        # Check if this is a UK university (by domain or country)
        is_uk_university = False
        if university:
            is_uk_university = (
                university.country and "united kingdom" in university.country.lower() or
                university.domain and ".ac.uk" in university.domain.lower()
            )
        
        # For UK universities, accept additional titles
        if is_uk_university:
            uk_acceptable_titles = [
                "reader", "senior lecturer", "lecturer",  # UK-specific titles
                "professor", "prof.", "associate professor", "assistant professor"
            ]
            for uk_title in uk_acceptable_titles:
                if uk_title in text_lower:
                    # But still exclude if it's clearly a student position
                    if any(excluded in text_lower for excluded in ["phd student", "doctoral student", "graduate student"]):
                        continue
                    return True
        
        # First, check for excluded titles/positions (but be more careful about context)
        for excluded in self.excluded_titles:
            excluded_lower = excluded.lower()
            
            # Skip if it's "Assistant Professor" (which is acceptable)
            if excluded_lower == "assistant professor":
                continue
            
            # For UK universities, don't exclude "Lecturer" or "Senior Lecturer"
            if is_uk_university and excluded_lower in ["lecturer", "senior lecturer"]:
                continue
            
            # Use word boundaries to avoid false matches
            # e.g., don't match "Research Assistant" when looking for "Assistant"
            pattern = r'\b' + re.escape(excluded_lower) + r'\b'
            if re.search(pattern, text_lower):
                return False
        
        # Check for specific excluded patterns
        excluded_patterns = [
            r'\bphd\s+student\b',
            r'\bph\.?d\.?\s+student\b',
            r'\bdoctoral\s+student\b',
            r'\bgraduate\s+student\b',
            r'\bpostdoc\b',
            r'\bpost-?doc\b',
            r'\bpostdoctoral\b',
            r'\bpost-?doctoral\b',
            r'\bresearch\s+fellow\b',
            r'\bresearch\s+associate\b',
            r'\bresearch\s+assistant\b',
            r'\bteaching\s+assistant\b',
            # Exclude emeritus professors (always exclude, regardless of university)
            r'\bemeritus\s+professor\b',
            r'\bprofessor\s+emeritus\b',
            r'\bemeritus\b',  # Standalone "emeritus" in title context
        ]
        
        # Only exclude lecturer titles for non-UK universities
        if not is_uk_university:
            excluded_patterns.extend([
                r'\blecturer\b',  # Exclude lecturers (non-UK)
                r'\bsenior\s+lecturer\b'  # Exclude senior lecturers (non-UK)
            ])
        
        for pattern in excluded_patterns:
            if re.search(pattern, text_lower):
                return False
        
        # If we have an extracted title, check if it's acceptable
        if extracted_title:
            title_lower = extracted_title.lower()
            for acceptable in self.acceptable_titles:
                if acceptable.lower() in title_lower:
                    return True
            # If extracted title doesn't match acceptable titles, reject
            return False
        
        # If no title extracted, check if text contains acceptable titles
        for acceptable in self.acceptable_titles:
            if acceptable.lower() in text_lower:
                return True
        
        # More lenient: if URL suggests it's a faculty/staff page and has email/research keywords, accept it
        # This handles cases where title might be in a format we don't recognize
        has_research_keywords = bool(re.search(r'\b(research|publication|study|paper|medical imaging|imaging)\b', text_lower[:2000]))
        has_contact = bool(re.search(r'\b(email|contact|@)\b', text_lower[:2000]))
        has_phd = bool(re.search(r'\bph\.?d\.?|phd|doctorate\b', text_lower[:2000]))
        
        # Be more lenient: accept if it's clearly a researcher profile
        # Check for indicators that this is a PI/researcher:
        pi_indicators = [
            r'\bprincipal investigator\b', r'\bgroup leader\b', r'\blab head\b',
            r'\bdirector\b', r'\blead\b', r'\bhead of\b', r'\bsupervisor\b'
        ]
        has_pi_indicator = any(re.search(pattern, text_lower[:2000]) for pattern in pi_indicators)
        
        # If has research keywords AND (contact info OR PhD), likely a researcher
        if has_research_keywords and (has_contact or has_phd):
            return True
        
        # If has PI indicators, accept
        if has_pi_indicator:
            return True
        
        # If URL is clearly a profile URL (already validated), be lenient
        # Many profile pages don't explicitly list title but are still valid
        # Accept if no excluded titles found and URL looks like profile
        return True  # Changed from False to True - be more lenient
    
    def _extract_homepage(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """Extract personal homepage URL if present."""
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True).lower()
            if any(w in text for w in ["homepage", "personal page", "website", "personal website"]):
                return link["href"]
        return None
    
    def _extract_publications_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract publication links if present on page."""
        links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True).lower()
            if any(w in text or w in href.lower() for w in ["publication", "paper", "research output", "scholar", "orcid"]):
                links.append(href)
        return links[:5]  # Limit to 5
    
    def _generate_scholar_url(self, name: str) -> str:
        """Generate a Google Scholar search URL for the person."""
        query = quote_plus(f'author:"{name}"')
        return f"https://scholar.google.com/scholar?q={query}"
    
    def _validate_url_domain(self, url: str, expected_domain: str) -> bool:
        """
        Validate that the URL's domain matches the expected university domain.
        
        This is critical to prevent assigning profiles from other universities
        (e.g., Stanford, Columbia) to the wrong institution (e.g., King's College London).
        
        Args:
            url: Profile URL to validate
            expected_domain: Expected university domain (e.g., "kcl.ac.uk")
        
        Returns:
            True if domain matches, False otherwise
        """
        if not expected_domain or expected_domain.strip() == "":
            # If no expected domain, try to infer from institution name or be more strict
            # For now, we'll extract domain from URL and check if it looks like a university domain
            # This is a fallback - ideally domain should always be provided
            try:
                parsed_url = urlparse(url)
                url_domain = parsed_url.netloc.lower()
                
                # Check if URL domain looks like a university domain
                # Accept common university domain patterns
                university_domain_patterns = [
                    r'\.ac\.uk$',  # UK universities
                    r'\.edu$',     # US universities
                    r'\.ac\.',     # Other .ac domains
                    r'\.edu\.',    # Other .edu domains
                    r'university', # Contains "university"
                    r'\.edu\.',    # .edu domains
                ]
                
                import re
                is_university_domain = any(re.search(pattern, url_domain) for pattern in university_domain_patterns)
                
                # Also check for known non-university domains to reject
                non_university_domains = [
                    'ncfdd.org',
                    'statecancerprofiles.cancer.gov',
                    'cps.edu',  # Chicago Public Schools, not a university
                    'institut-curie.org',  # Research institute, might be OK but be careful
                ]
                
                if any(non_uni in url_domain for non_uni in non_university_domains):
                    return False
                
                # If it looks like a university domain, accept it (we can't validate further without domain)
                # But be conservative - only accept if it clearly looks like a university domain
                return is_university_domain
            except:
                # If parsing fails, reject to be safe
                return False
        
        try:
            parsed_url = urlparse(url)
            url_domain = parsed_url.netloc.lower()
            expected_domain_lower = expected_domain.lower().strip()
            
            # Direct match
            if url_domain == expected_domain_lower:
                return True
            
            # Check for profiles subdomain (e.g., profiles.kcl.ac.uk matches kcl.ac.uk)
            if url_domain.startswith("profiles."):
                # Extract base domain from profiles subdomain
                base_domain = url_domain.replace("profiles.", "", 1)
                if base_domain == expected_domain_lower:
                    return True
                
                # Also check if expected domain is the base (e.g., kcl.ac.uk matches profiles.kcl.ac.uk)
                # by checking if expected domain is a suffix of the base domain
                if base_domain.endswith("." + expected_domain_lower) or base_domain == expected_domain_lower:
                    return True
            
            # Check if expected domain is a suffix of URL domain (handles subdomains)
            # e.g., "www.kcl.ac.uk" should match "kcl.ac.uk"
            # e.g., "eng.ox.ac.uk" should match "ox.ac.uk"
            # e.g., "med.cam.ac.uk" should match "cam.ac.uk"
            if url_domain.endswith("." + expected_domain_lower):
                return True
            
            # Also check if URL domain contains expected domain as a subdomain
            # This handles cases like "eng.ox.ac.uk" matching "ox.ac.uk"
            # Split by dots and check if any segment matches the expected domain
            url_parts = url_domain.split('.')
            expected_parts = expected_domain_lower.split('.')
            
            # Check if expected domain parts appear consecutively in URL domain
            # e.g., ["eng", "ox", "ac", "uk"] contains ["ox", "ac", "uk"]
            for i in range(len(url_parts) - len(expected_parts) + 1):
                if url_parts[i:i+len(expected_parts)] == expected_parts:
                    return True
            
            # Check if URL domain is a suffix of expected domain (reverse case)
            # e.g., "kcl.ac.uk" should match "www.kcl.ac.uk" (though this is less common)
            if expected_domain_lower.endswith("." + url_domain):
                return True
            
            # If none of the above match, reject
            return False
            
        except Exception:
            # If parsing fails, be conservative and reject
            return False


# Global extractor instance
profile_extractor = ProfileExtractor()

