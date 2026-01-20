"""Validation and deduplication."""

import re
from typing import Optional, List, Tuple
from urllib.parse import urlparse
from app.schemas import SupervisorProfile


def validate_email(email: Optional[str]) -> bool:
    """Validate email format."""
    if not email:
        return True  # None is valid (means not found)
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_url(url: Optional[str]) -> bool:
    """Validate URL format."""
    if not url:
        return True
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_profile(profile: SupervisorProfile) -> Tuple[bool, str]:
    """Validate a supervisor profile.
    
    Returns:
        Tuple of (is_valid, reason). If is_valid is True, reason is empty string.
        If is_valid is False, reason indicates why validation failed.
    """
    # Required fields: name, profile_url (or source_url), institution
    if not profile.name or len(profile.name) < 2:
        return False, "no_name_or_too_short"
    if not profile.institution or len(profile.institution) < 2:
        return False, "no_institution"
    if not profile.source_url:
        return False, "no_source_url"
    
    # Email is optional - allow None/empty, but if present must be valid format
    if profile.email and not validate_email(profile.email):
        return False, "invalid_email_format"
    
    # profile_url is optional, but if present must be valid URL format
    if profile.profile_url and not validate_url(profile.profile_url):
        return False, "invalid_profile_url_format"
    
    # Additional validation: Reject profiles with very low fit_score
    # BUT: Allow PI (Principal Investigator) even with low fit_score
    # Check if profile indicates PI status (from notes or keywords)
    is_pi = False
    if profile.notes:
        notes_lower = profile.notes.lower()
        pi_indicators = ["principal investigator", "pi", "group leader", "lab head", "lab director"]
        is_pi = any(indicator in notes_lower for indicator in pi_indicators)
    
    # Also check keywords for PI-related terms
    if not is_pi and profile.keywords:
        keywords_text = " ".join(profile.keywords).lower()
        pi_indicators = ["principal investigator", "pi", "group leader", "lab head"]
        is_pi = any(indicator in keywords_text for indicator in pi_indicators)
    
    # Allow PI even with low fit_score (they might be valid supervisors)
    if profile.fit_score < 0.1 and not is_pi:
        return False, "very_low_fit_score"
    
    return True, ""


def deduplicate_profiles(profiles: List[SupervisorProfile]) -> List[SupervisorProfile]:
    """Remove duplicate profiles based on email, name+institution, or URL."""
    seen_emails = set()
    seen_name_inst = set()
    seen_urls = set()
    unique = []
    
    for profile in profiles:
        # Check email
        if profile.email:
            if profile.email.lower() in seen_emails:
                continue
            seen_emails.add(profile.email.lower())
        
        # Check name + institution
        name_inst = f"{profile.name.lower()}|{profile.institution.lower()}"
        if name_inst in seen_name_inst:
            continue
        seen_name_inst.add(name_inst)
        
        # Check URL
        if profile.profile_url:
            if profile.profile_url in seen_urls:
                continue
            seen_urls.add(profile.profile_url)
        
        unique.append(profile)
    
    return unique

