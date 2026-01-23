#!/usr/bin/env python3
"""Clean up database to make it lightweight.

This script:
1. Removes ALL page cache (main space consumer, ~300MB+ for 2972 entries)
2. Removes extracted_profiles table data
3. Removes evidence_snippets_json (keeps only essential supervisor info)
4. VACUUM database to reclaim space
5. Shows before/after size comparison

Note: Page cache can be regenerated when needed during searches.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import CACHE_DB
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()


def get_db_size(db_path: Path) -> int:
    """Get database file size in bytes."""
    return db_path.stat().st_size if db_path.exists() else 0


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def cleanup_database(db_path: Path, keep_cache_days: int = 0) -> dict:
    """Clean up database and return statistics."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    stats = {
        'before_size': get_db_size(db_path),
        'page_cache_deleted': 0,
        'extracted_profiles_deleted': 0,
        'evidence_cleared': 0,
        'supervisors_kept': 0
    }
    
    # Get initial counts
    cursor.execute("SELECT COUNT(*) FROM supervisors")
    stats['supervisors_kept'] = cursor.fetchone()[0]
    
    console.print("[yellow]Starting database cleanup...[/yellow]")
    console.print()
    
    # 1. Delete ALL page cache (can be regenerated when needed)
    # Page cache is the main space consumer - HTML content is very large
    console.print(f"[cyan]1. Cleaning page cache (deleting all entries)...[/cyan]")
    cursor.execute("SELECT COUNT(*) FROM page_cache")
    cache_count_before = cursor.fetchone()[0]
    cursor.execute("DELETE FROM page_cache")
    stats['page_cache_deleted'] = cursor.rowcount
    console.print(f"   [green]Deleted {stats['page_cache_deleted']} cache entries (freed significant space)[/green]")
    
    # 2. Delete all extracted_profiles (not needed, can be regenerated)
    console.print("[cyan]2. Cleaning extracted_profiles table...[/cyan]")
    cursor.execute("DELETE FROM extracted_profiles")
    stats['extracted_profiles_deleted'] = cursor.rowcount
    console.print(f"   [green]Deleted {stats['extracted_profiles_deleted']} extracted profiles[/green]")
    
    # 3. Clear evidence_snippets_json (keeps only essential info)
    # This can be large and is not essential for searching
    console.print("[cyan]3. Clearing evidence_snippets_json (keeping essential info only)...[/cyan]")
    cursor.execute("UPDATE supervisors SET evidence_snippets_json = '[]' WHERE evidence_snippets_json IS NOT NULL AND evidence_snippets_json != '[]'")
    stats['evidence_cleared'] = cursor.rowcount
    console.print(f"   [green]Cleared evidence snippets from {stats['evidence_cleared']} supervisors[/green]")
    
    # 4. Clear evidence_email if not needed (optional, keeping for now)
    # Uncomment if you want to remove evidence_email too:
    # cursor.execute("UPDATE supervisors SET evidence_email = NULL WHERE evidence_email IS NOT NULL")
    
    # 5. Commit changes
    conn.commit()
    console.print()
    console.print("[green]✓ Changes committed[/green]")
    
    # 6. VACUUM to reclaim space
    console.print()
    console.print("[cyan]5. Running VACUUM to reclaim space...[/cyan]")
    console.print("   [dim]This may take a few minutes for large databases...[/dim]")
    cursor.execute("VACUUM")
    console.print("   [green]✓ VACUUM completed[/green]")
    
    # Get final size
    stats['after_size'] = get_db_size(db_path)
    stats['space_saved'] = stats['before_size'] - stats['after_size']
    
    conn.close()
    return stats


def main():
    """Main function."""
    console.print("[bold cyan]Database Cleanup Script[/bold cyan]")
    console.print()
    
    db_path = CACHE_DB
    
    if not db_path.exists():
        console.print(f"[red]Error: Database file not found at {db_path}[/red]")
        return
    
    # Show current database info
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM supervisors")
    supervisor_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM page_cache")
    cache_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM extracted_profiles")
    extracted_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM supervisors WHERE evidence_snippets_json IS NOT NULL AND evidence_snippets_json != '[]'")
    evidence_count = cursor.fetchone()[0]
    
    conn.close()
    
    # Show current state
    console.print("[bold]Current Database State:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Database Size", format_size(get_db_size(db_path)))
    table.add_row("Supervisors", str(supervisor_count))
    table.add_row("Page Cache Entries", str(cache_count))
    table.add_row("Extracted Profiles", str(extracted_count))
    table.add_row("Supervisors with Evidence", str(evidence_count))
    
    console.print(table)
    console.print()
    
    # Ask for confirmation
    response = console.input("[yellow]Do you want to proceed with cleanup? (yes/no): [/yellow]")
    if response.lower() not in ["yes", "y"]:
        console.print("[yellow]Aborted.[/yellow]")
        return
    
    # Perform cleanup (keep_cache_days=0 means delete ALL cache)
    stats = cleanup_database(db_path, keep_cache_days=0)
    
    # Show results
    console.print()
    console.print("[bold]Cleanup Results:[/bold]")
    
    results_table = Table(show_header=True, header_style="bold magenta")
    results_table.add_column("Metric", style="cyan")
    results_table.add_column("Before", style="yellow")
    results_table.add_column("After", style="green")
    results_table.add_column("Saved", style="green")
    
    results_table.add_row(
        "Database Size",
        format_size(stats['before_size']),
        format_size(stats['after_size']),
        format_size(stats['space_saved'])
    )
    results_table.add_row(
        "Page Cache",
        f"{stats['page_cache_deleted']} deleted",
        "All deleted (~300MB+ freed)",
        f"{stats['page_cache_deleted']} entries"
    )
    results_table.add_row(
        "Extracted Profiles",
        f"{stats['extracted_profiles_deleted']} deleted",
        "0",
        f"{stats['extracted_profiles_deleted']} entries"
    )
    results_table.add_row(
        "Evidence Snippets",
        f"{stats['evidence_cleared']} cleared",
        "Empty",
        "Space reclaimed"
    )
    results_table.add_row(
        "Supervisors",
        str(stats['supervisors_kept']),
        str(stats['supervisors_kept']),
        "Kept all"
    )
    
    console.print(results_table)
    console.print()
    
    # Calculate percentage saved
    if stats['before_size'] > 0:
        percent_saved = (stats['space_saved'] / stats['before_size']) * 100
        console.print(f"[bold green]✓ Space saved: {format_size(stats['space_saved'])} ({percent_saved:.1f}%)[/bold green]")
    
    console.print()
    console.print("[green]✓ Cleanup completed successfully![/green]")
    console.print()
    console.print("[dim]Note: Essential supervisor information (name, institution, email, keywords, URLs) has been preserved.[/dim]")
    console.print("[dim]Cache and evidence data can be regenerated when needed.[/dim]")


if __name__ == "__main__":
    main()

