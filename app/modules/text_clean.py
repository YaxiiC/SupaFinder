"""Text cleaning utilities."""

import re
from bs4 import BeautifulSoup


def clean_html_to_text(html: str, max_length: int = 5000) -> str:
    """Convert HTML to clean text, limiting length."""
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    
    text = soup.get_text(separator=" ", strip=True)
    
    # Clean up whitespace
    text = re.sub(r"\s+", " ", text)
    
    return text[:max_length]


def extract_relevant_sections(html: str, keywords: list[str]) -> str:
    """Extract sections most relevant to keywords."""
    soup = BeautifulSoup(html, "html.parser")
    
    relevant_parts = []
    
    # Look for sections containing keywords
    for element in soup.find_all(["div", "section", "article", "p"]):
        text = element.get_text(strip=True)
        if any(kw.lower() in text.lower() for kw in keywords):
            relevant_parts.append(text)
    
    combined = " ".join(relevant_parts)
    return combined[:4000] if combined else clean_html_to_text(html, 4000)


def extract_contact_section(html: str) -> str:
    """Extract contact information section."""
    soup = BeautifulSoup(html, "html.parser")
    
    contact_keywords = ["contact", "email", "phone", "address", "office"]
    
    for element in soup.find_all(["div", "section", "aside"]):
        class_or_id = " ".join([
            element.get("class", []) if isinstance(element.get("class"), list) else str(element.get("class", "")),
            str(element.get("id", ""))
        ]).lower()
        
        if any(kw in class_or_id for kw in contact_keywords):
            return element.get_text(separator=" ", strip=True)[:1000]
    
    return ""

