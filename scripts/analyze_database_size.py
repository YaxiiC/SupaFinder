#!/usr/bin/env python3
"""Analyze database size distribution to identify space consumers."""

import sys
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import CACHE_DB
from rich.console import Console
from rich.table import Table

console = Console()


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def analyze_database(db_path: Path):
    """Analyze database size distribution."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    console.print("[bold cyan]Database Size Analysis[/bold cyan]")
    console.print()
    
    # Get database file size
    db_size = db_path.stat().st_size
    console.print(f"[bold]Total Database Size:[/bold] {format_size(db_size)}")
    console.print()
    
    # Analyze page_cache table
    console.print("[cyan]Analyzing page_cache table (main space consumer)...[/cyan]")
    cursor.execute("SELECT COUNT(*) FROM page_cache")
    cache_count = cursor.fetchone()[0]
    
    total_cache_size = 0
    if cache_count > 0:
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                SUM(LENGTH(html)) as total_html_size,
                SUM(LENGTH(text_content)) as total_text_size,
                AVG(LENGTH(html)) as avg_html_size,
                AVG(LENGTH(text_content)) as avg_text_size,
                MAX(LENGTH(html)) as max_html_size,
                MAX(LENGTH(text_content)) as max_text_size
            FROM page_cache
        """)
        cache_stats = cursor.fetchone()
        
        if cache_stats[0] > 0:
            total_cache_size = (cache_stats[1] or 0) + (cache_stats[2] or 0)
            console.print(f"  Entries: {cache_stats[0]}")
            console.print(f"  Total HTML size: {format_size(cache_stats[1] or 0)}")
            console.print(f"  Total text size: {format_size(cache_stats[2] or 0)}")
            console.print(f"  Total cache size: {format_size(total_cache_size)}")
            console.print(f"  Average HTML per entry: {format_size(int(cache_stats[3] or 0))}")
            console.print(f"  Average text per entry: {format_size(int(cache_stats[4] or 0))}")
            console.print(f"  Largest HTML entry: {format_size(cache_stats[5] or 0)}")
            console.print(f"  Largest text entry: {format_size(cache_stats[6] or 0)}")
            console.print()
            console.print(f"  [yellow]💡 page_cache accounts for ~{total_cache_size / db_size * 100:.1f}% of database size[/yellow]")
            console.print()
    else:
        console.print("  [green]✓ No page_cache entries (already cleaned)[/green]")
        console.print()
    
    # Analyze supervisors table
    console.print("[cyan]Analyzing supervisors table...[/cyan]")
    cursor.execute("SELECT COUNT(*) FROM supervisors")
    supervisor_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT 
            COUNT(*) as count,
            SUM(LENGTH(keywords_json)) as total_keywords_size,
            SUM(LENGTH(evidence_snippets_json)) as total_evidence_size,
            AVG(LENGTH(keywords_json)) as avg_keywords_size,
            AVG(LENGTH(evidence_snippets_json)) as avg_evidence_size
        FROM supervisors
    """)
    supervisor_stats = cursor.fetchone()
    
    total_supervisor_size = (supervisor_stats[1] or 0) + (supervisor_stats[2] or 0)
    console.print(f"  Supervisors: {supervisor_count}")
    console.print(f"  Total keywords size: {format_size(supervisor_stats[1] or 0)}")
    console.print(f"  Total evidence size: {format_size(supervisor_stats[2] or 0)}")
    console.print(f"  Total supervisor data: {format_size(total_supervisor_size)}")
    console.print()
    
    # Analyze other tables
    console.print("[cyan]Analyzing other tables...[/cyan]")
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT IN ('page_cache', 'supervisors', 'sqlite_sequence')
        ORDER BY name
    """)
    other_tables = cursor.fetchall()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Table", style="cyan")
    table.add_column("Row Count", style="green")
    
    for (table_name,) in other_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            table.add_row(table_name, str(count))
        except:
            table.add_row(table_name, "N/A")
    
    console.print(table)
    console.print()
    
    # Summary
    console.print("[bold]Summary:[/bold]")
    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("Component", style="cyan")
    summary_table.add_column("Size", style="green")
    summary_table.add_column("Percentage", style="yellow")
    
    summary_table.add_row("page_cache", format_size(total_cache_size), f"{total_cache_size / db_size * 100:.1f}%")
    summary_table.add_row("supervisors", format_size(total_supervisor_size), f"{total_supervisor_size / db_size * 100:.1f}%")
    summary_table.add_row("Other/Overhead", format_size(db_size - total_cache_size - total_supervisor_size), f"{(db_size - total_cache_size - total_supervisor_size) / db_size * 100:.1f}%")
    summary_table.add_row("Total", format_size(db_size), "100.0%")
    
    console.print(summary_table)
    console.print()
    
    # Recommendations
    console.print("[bold yellow]💡 Recommendations:[/bold yellow]")
    if cache_count > 0:
        console.print(f"  1. Delete ALL page_cache entries ({cache_count} entries, ~{format_size(total_cache_size)})")
        console.print("     → Can be regenerated during searches")
        console.print("     → Will free ~{:.1f}% of database size".format(total_cache_size / db_size * 100))
    
    if supervisor_stats[2] and supervisor_stats[2] > 0:
        evidence_size = supervisor_stats[2]
        console.print(f"  2. Clear evidence_snippets_json (~{format_size(evidence_size)})")
        console.print("     → Not essential for searching")
    
    console.print("  3. Run VACUUM after cleanup to reclaim space")
    console.print()
    
    conn.close()


if __name__ == "__main__":
    db_path = CACHE_DB
    
    if not db_path.exists():
        console.print(f"[red]Error: Database file not found at {db_path}[/red]")
        sys.exit(1)
    
    analyze_database(db_path)

