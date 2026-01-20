"""Identity normalization and canonical ID computation."""

import re
import hashlib
from typing import Optional


def normalize_text(text: Optional[str]) -> str:
    """
    Normalize text for comparison and hashing.
    - Convert to lowercase
    - Remove extra whitespace
    - Remove special characters (keep alphanumeric and spaces)
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = " ".join(text.split())
    
    # Remove special characters except alphanumeric and spaces
    text = re.sub(r'[^\w\s]', '', text)
    
    return text.strip()


def compute_canonical_id(
    email: Optional[str],
    name: str,
    institution: str,
    domain: Optional[str] = None,
    profile_url: Optional[str] = None
) -> str:
    """
    Compute canonical ID for a supervisor.
    
    Priority:
    1. If email exists: use lowercase email
    2. Otherwise: sha1(normalize(name) + normalize(institution) + normalize(domain or profile_url))
    
    Args:
        email: Email address (preferred)
        name: Supervisor name
        institution: Institution name
        domain: Institution domain
        profile_url: Profile URL (used if domain is None)
    
    Returns:
        Canonical ID string
    """
    # Priority 1: Use email if available
    if email:
        return email.lower().strip()
    
    # Priority 2: Hash of normalized fields
    normalized_name = normalize_text(name)
    normalized_institution = normalize_text(institution)
    
    # Use domain if available, otherwise extract domain from profile_url, otherwise empty
    if domain:
        normalized_domain = normalize_text(domain)
    elif profile_url:
        # Extract domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(profile_url)
        normalized_domain = normalize_text(parsed.netloc)
    else:
        normalized_domain = ""
    
    # Combine and hash
    combined = f"{normalized_name}|{normalized_institution}|{normalized_domain}"
    hash_obj = hashlib.sha1(combined.encode('utf-8'))
    return hash_obj.hexdigest()

