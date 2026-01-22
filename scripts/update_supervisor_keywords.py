#!/usr/bin/env python3
"""Update supervisor keywords in database by re-extracting from their homepages.

This script:
1. Reads all supervisors from the database
2. For supervisors with homepages, fetches the page content
3. Uses DeepSeek to extract 3-5 keywords from the homepage
4. Updates the database with the new keywords
"""

import sys
import json
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db_cloud import get_db_connection, init_db
from app.modules.crawl import crawler
from app.modules.llm_deepseek import llm_client
from app.modules.profile import ProfileExtractor
from app.schemas import ResearchProfile
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

console = Console()


def get_all_supervisors(limit: Optional[int] = None) -> List[dict]:
    """Get all supervisors from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = conn.__class__.__module__
    is_postgres = "psycopg2" in db_type
    
    if is_postgres:
        query = "SELECT id, name, institution, homepage, profile_url, keywords_json, keywords_text FROM supervisors"
        if limit:
            query += f" LIMIT {limit}"
    else:
        query = "SELECT id, name, institution, homepage, profile_url, keywords_json, keywords_text FROM supervisors"
        if limit:
            query += f" LIMIT {limit}"
    
    cursor.execute(query)
    
    if is_postgres:
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        supervisors = [dict(zip(columns, row)) for row in rows]
    else:
        supervisors = []
        for row in cursor.fetchall():
            supervisors.append({
                "id": row[0],
                "name": row[1],
                "institution": row[2],
                "homepage": row[3],
                "profile_url": row[4],
                "keywords_json": row[5],
                "keywords_text": row[6]
            })
    
    conn.close()
    return supervisors


def update_supervisor_keywords(supervisor_id: int, keywords: List[str]) -> bool:
    """Update supervisor keywords in database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = conn.__class__.__module__
    is_postgres = "psycopg2" in db_type
    
    keywords_json = json.dumps(keywords)
    keywords_text = ", ".join(keywords)
    updated_at = datetime.now().isoformat()
    
    if is_postgres:
        cursor.execute(
            "UPDATE supervisors SET keywords_json = %s, keywords_text = %s, updated_at = %s WHERE id = %s",
            (keywords_json, keywords_text, updated_at, supervisor_id)
        )
    else:
        cursor.execute(
            "UPDATE supervisors SET keywords_json = ?, keywords_text = ?, updated_at = ? WHERE id = ?",
            (keywords_json, keywords_text, updated_at, supervisor_id)
        )
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def delete_supervisor(supervisor_id: int) -> bool:
    """Delete supervisor from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = conn.__class__.__module__
    is_postgres = "psycopg2" in db_type
    
    if is_postgres:
        cursor.execute("DELETE FROM supervisors WHERE id = %s", (supervisor_id,))
    else:
        cursor.execute("DELETE FROM supervisors WHERE id = ?", (supervisor_id,))
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success


def extract_keywords_from_homepage(homepage_url: str) -> Tuple[Optional[List[str]], bool]:
    """Extract keywords from supervisor homepage using DeepSeek.
    
    Returns:
        Tuple of (keywords, is_blank_page)
        - keywords: List of keywords if extraction successful, None otherwise
        - is_blank_page: True if the page is blank (should be deleted), False otherwise
    """
    profile_extractor = ProfileExtractor()
    
    try:
        # Fetch the page
        page = crawler.fetch(homepage_url, use_cache=False)  # Don't use cache to get fresh content
        
        if page.get("status_code") != 200:
            return None, False
        
        html = page.get("html", "")
        text_content = page.get("text_content", "")
        
        if not text_content or len(text_content.strip()) < 100:
            # Try to get HTML content if text is too short
            if not html:
                return None, False
            soup = BeautifulSoup(html, "html.parser")
            text_content = soup.get_text(separator=" ", strip=True)
        
        if len(text_content.strip()) < 100:
            return None, False
        
        # Check if this is a blank profile page
        soup = BeautifulSoup(html, "html.parser") if html else BeautifulSoup("", "html.parser")
        is_blank = profile_extractor._is_blank_profile_page(text_content, soup, homepage_url)
        
        if is_blank:
            return None, True  # Mark as blank page
        
        # Use DeepSeek to extract keywords
        # We use an empty ResearchProfile since we're just extracting keywords, not matching
        # The LLM will extract keywords directly from the supervisor's page content
        empty_research_profile = ResearchProfile()
        
        # Limit text content to avoid token limits (first 4000 chars)
        text_content = text_content[:4000]
        
        extraction = llm_client.extract_profile_keywords(text_content, empty_research_profile)
        
        if extraction and extraction.keywords:
            # Ensure we have 3-5 keywords
            keywords = extraction.keywords[:5]  # Max 5
            if len(keywords) < 3:
                # If we got less than 3, try to keep what we have or return None
                if len(keywords) == 0:
                    return None, False
            return keywords, False  # Not blank, extraction successful
        
        return None, False  # Extraction failed but not blank
        
    except Exception as e:
        console.print(f"[red]Error extracting keywords from {homepage_url}: {e}[/red]")
        return None, False


def main():
    """Main function to update supervisor keywords."""
    console.print("[bold cyan]Supervisor Keywords Update Script[/bold cyan]")
    console.print()
    
    # Initialize database
    console.print("[yellow]Initializing database...[/yellow]")
    init_db()
    
    # Get all supervisors
    console.print("[yellow]Fetching supervisors from database...[/yellow]")
    supervisors = get_all_supervisors()
    
    console.print(f"[green]Found {len(supervisors)} supervisors in database[/green]")
    console.print()
    
    # Filter supervisors with homepages
    supervisors_with_homepage = [
        s for s in supervisors 
        if s.get("homepage") or s.get("profile_url")
    ]
    
    console.print(f"[cyan]Supervisors with homepage/profile_url: {len(supervisors_with_homepage)}[/cyan]")
    console.print()
    
    # Ask for confirmation
    response = console.input("[yellow]Do you want to proceed with updating keywords? (yes/no): [/yellow]")
    if response.lower() not in ["yes", "y"]:
        console.print("[yellow]Aborted.[/yellow]")
        return
    
    # Process supervisors
    updated_count = 0
    failed_count = 0
    skipped_count = 0
    deleted_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Updating keywords...", total=len(supervisors_with_homepage))
        
        for supervisor in supervisors_with_homepage:
            supervisor_id = supervisor["id"]
            name = supervisor["name"]
            institution = supervisor["institution"]
            homepage = supervisor.get("homepage") or supervisor.get("profile_url")
            
            # Check current keyword count
            current_keywords_json = supervisor.get("keywords_json", "[]")
            try:
                current_keywords = json.loads(current_keywords_json) if current_keywords_json else []
            except:
                current_keywords = []
            
            current_count = len(current_keywords)
            
            # Skip if already has exactly 3-5 keywords (perfect range)
            # Process if has more than 5 keywords (need to reduce) or less than 3 keywords (need to add)
            if 3 <= current_count <= 5:
                skipped_count += 1
                progress.update(task, advance=1, description=f"[dim]Skipped {name} (already has {current_count} keywords)[/dim]")
                continue
            
            # Log what we're doing
            if current_count > 5:
                progress.update(task, advance=0, description=f"Reducing {name} from {current_count} to 3-5 keywords...")
            elif current_count < 3:
                progress.update(task, advance=0, description=f"Adding keywords to {name} (currently {current_count})...")
            else:
                progress.update(task, advance=0, description=f"Processing {name} ({institution})...")
            
            # Extract keywords from homepage
            new_keywords, is_blank_page = extract_keywords_from_homepage(homepage)
            
            # If blank page, delete the supervisor
            if is_blank_page:
                if delete_supervisor(supervisor_id):
                    deleted_count += 1
                    progress.update(
                        task,
                        advance=1,
                        description=f"[red]Deleted {name} (blank homepage)[/red]"
                    )
                else:
                    failed_count += 1
                    progress.update(task, advance=1, description=f"[red]Failed to delete {name}[/red]")
                continue
            
            if new_keywords:
                # Update database
                if update_supervisor_keywords(supervisor_id, new_keywords):
                    updated_count += 1
                    old_count = current_count
                    new_count = len(new_keywords)
                    if old_count > 5:
                        progress.update(
                            task, 
                            advance=1, 
                            description=f"[green]Reduced {name}: {old_count} → {new_count} keywords[/green]"
                        )
                    else:
                        progress.update(
                            task, 
                            advance=1, 
                            description=f"[green]Updated {name}: {old_count} → {new_count} keywords[/green]"
                        )
                else:
                    failed_count += 1
                    progress.update(task, advance=1, description=f"[red]Failed to update {name}[/red]")
            else:
                failed_count += 1
                progress.update(task, advance=1, description=f"[yellow]Could not extract keywords for {name}[/yellow]")
    
    # Summary
    console.print()
    console.print("[bold]Summary:[/bold]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Status", style="cyan")
    table.add_column("Count", style="green")
    
    table.add_row("✅ Updated", str(updated_count))
    table.add_row("🗑️  Deleted (blank homepage)", str(deleted_count))
    table.add_row("⏭️  Skipped (already 3-5)", str(skipped_count))
    table.add_row("❌ Failed", str(failed_count))
    table.add_row("📊 Total with Homepage", str(len(supervisors_with_homepage)))
    
    console.print(table)
    console.print()
    console.print("[green]Done![/green]")


if __name__ == "__main__":
    main()

