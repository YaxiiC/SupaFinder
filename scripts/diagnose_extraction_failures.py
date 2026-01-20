#!/usr/bin/env python3
"""Diagnostic script to analyze extraction failures.

This script helps identify why profile extraction is failing for certain URLs.
It can test individual URLs or analyze patterns from logs.
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.modules.crawl import crawler
from app.modules.profile import profile_extractor
from app.modules.directory import directory_parser
from app.schemas import University, ResearchProfile
from rich.console import Console
from rich.table import Table

console = Console()


def diagnose_url(url: str, university_domain: str, institution_name: str = "Test University"):
    """Diagnose why a specific URL fails extraction."""
    console.print(f"\n[bold cyan]Diagnosing URL:[/bold cyan] {url}")
    console.print()
    
    # Fetch the page
    console.print("[yellow]Fetching page...[/yellow]")
    page = crawler.fetch(url)
    
    if page["status_code"] != 200:
        console.print(f"[red]✗ HTTP Status: {page['status_code']}[/red]")
        return
    
    console.print(f"[green]✓ HTTP Status: {page['status_code']}[/green]")
    
    # Check text content
    text_content = page.get("text_content", "") or ""
    text_length = len(text_content)
    console.print(f"  Text content length: {text_length} chars")
    
    if text_length < 20:
        console.print(f"[yellow]⚠ Text content is very short ({text_length} chars)[/yellow]")
    
    # Check HTML
    html = page.get("html", "")
    html_length = len(html)
    console.print(f"  HTML length: {html_length} chars")
    
    # Parse HTML
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    
    # Check for key elements
    console.print("\n[bold]HTML Structure Analysis:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Element", style="cyan")
    table.add_column("Found", style="green")
    table.add_column("Content Preview", style="dim")
    
    h1 = soup.find("h1")
    table.add_row("H1", "✓" if h1 else "✗", h1.get_text(strip=True)[:50] if h1 else "N/A")
    
    title = soup.find("title")
    table.add_row("Title", "✓" if title else "✗", title.get_text(strip=True)[:50] if title else "N/A")
    
    og_title = soup.find("meta", property="og:title")
    table.add_row("OG:Title", "✓" if og_title else "✗", og_title.get("content", "")[:50] if og_title else "N/A")
    
    # Check for email
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    import re
    emails = re.findall(email_pattern, html + text_content)
    has_email = len(emails) > 0
    table.add_row("Email", "✓" if has_email else "✗", emails[0] if emails else "N/A")
    
    # Check if it's a profile URL
    is_profile_url = directory_parser.looks_like_profile_url(url)
    table.add_row("Profile URL Pattern", "✓" if is_profile_url else "✗", "Matches" if is_profile_url else "No match")
    
    console.print(table)
    
    # Try extraction
    console.print("\n[bold]Attempting Extraction:[/bold]")
    university = University(
        institution=institution_name,
        domain=university_domain,
        country="United Kingdom",
        region="Europe",
        qs_rank=None
    )
    
    # Create a minimal research profile for testing
    research_profile = ResearchProfile(
        core_keywords=["test"],
        adjacent_keywords=[],
        negative_keywords=[],
        preferred_departments=[],
        query_templates=[]
    )
    
    try:
        profile, failure_reason = profile_extractor.extract(
            html,
            text_content,
            url,
            university,
            research_profile,
            debug=True  # Enable debug output
        )
        
        if profile:
            console.print("[green]✓ Extraction successful![/green]")
            console.print(f"  Name: {profile.name}")
            console.print(f"  Email: {profile.email or 'None'}")
            console.print(f"  Title: {profile.title or 'None'}")
            console.print(f"  Fit Score: {profile.fit_score:.2f}")
        else:
            console.print(f"[red]✗ Extraction failed: {failure_reason}[/red]")
            
            # Provide suggestions
            console.print("\n[bold yellow]Suggestions:[/bold yellow]")
            if "no_name" in failure_reason:
                console.print("  - Page might not have a clear name in H1/title")
                console.print("  - Check if this is actually a person's profile page")
            if "text_too_short" in failure_reason:
                console.print("  - Page has very little text content")
                console.print("  - Might be a redirect or minimal page")
            if "domain_mismatch" in failure_reason:
                console.print("  - URL domain doesn't match university domain")
                console.print(f"  - Expected: {university_domain}")
                parsed = urlparse(url)
                console.print(f"  - Got: {parsed.netloc}")
                
    except Exception as e:
        console.print(f"[red]✗ Exception during extraction: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        console.print("[bold red]Usage:[/bold red]")
        console.print("  python scripts/diagnose_extraction_failures.py <url> <university_domain> [institution_name]")
        console.print("\n[bold]Example:[/bold]")
        console.print("  python scripts/diagnose_extraction_failures.py \\")
        console.print("    'https://profiles.ucl.ac.uk/94114-natalie-wint' \\")
        console.print("    'ucl.ac.uk' \\")
        console.print("    'University College London'")
        sys.exit(1)
    
    url = sys.argv[1]
    university_domain = sys.argv[2]
    institution_name = sys.argv[3] if len(sys.argv) > 3 else "Test University"
    
    diagnose_url(url, university_domain, institution_name)


if __name__ == "__main__":
    main()

