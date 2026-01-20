"""Interactive script to view and edit supervisors in the database."""

import sys
import sqlite3
from pathlib import Path
import json
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import CACHE_DB
from app.modules.utils_identity import compute_canonical_id


def list_supervisors(limit: int = 20, offset: int = 0):
    """List supervisors from database."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, institution, email, email_confidence, title, 
               keywords_text, profile_url, canonical_id
        FROM supervisors
        ORDER BY last_seen_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    return rows


def get_supervisor_by_id(supervisor_id: int) -> Optional[dict]:
    """Get a supervisor by ID."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM supervisors WHERE id = ?", (supervisor_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return None
    
    # Get column names
    cursor.execute("PRAGMA table_info(supervisors)")
    columns = [col[1] for col in cursor.fetchall()]
    
    supervisor = dict(zip(columns, row))
    conn.close()
    
    return supervisor


def update_supervisor(supervisor_id: int, field: str, value: str) -> bool:
    """Update a supervisor field."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    
    # Validate field name
    cursor.execute("PRAGMA table_info(supervisors)")
    valid_fields = [col[1] for col in cursor.fetchall()]
    
    if field not in valid_fields:
        print(f"Error: '{field}' is not a valid field")
        conn.close()
        return False
    
    # Special handling for JSON fields
    if field in ['keywords_json', 'evidence_snippets_json']:
        # If value is a list string, convert to JSON
        if value.startswith('[') and value.endswith(']'):
            # Already JSON-like
            pass
        else:
            # Convert comma-separated to JSON array
            items = [item.strip() for item in value.split(',')]
            value = json.dumps(items)
    
    # Update the field
    cursor.execute(f"UPDATE supervisors SET {field} = ?, updated_at = datetime('now') WHERE id = ?", 
                   (value, supervisor_id))
    
    # If we updated name, email, institution, or profile_url, we need to recompute canonical_id
    if field in ['name', 'email', 'institution', 'profile_url', 'domain']:
        # Get current values
        cursor.execute("SELECT email, name, institution, domain, profile_url FROM supervisors WHERE id = ?", 
                      (supervisor_id,))
        row = cursor.fetchone()
        if row:
            email, name, institution, domain, profile_url = row
            new_canonical_id = compute_canonical_id(
                email=email,
                name=name,
                institution=institution,
                domain=domain,
                profile_url=profile_url
            )
            cursor.execute("UPDATE supervisors SET canonical_id = ? WHERE id = ?", 
                          (new_canonical_id, supervisor_id))
    
    conn.commit()
    conn.close()
    return True


def delete_supervisor(supervisor_id: int) -> bool:
    """Delete a supervisor from database."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM supervisors WHERE id = ?", (supervisor_id,))
    conn.commit()
    
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def print_supervisor(supervisor: dict):
    """Print supervisor details in a readable format."""
    print("\n" + "=" * 60)
    print(f"ID: {supervisor.get('id')}")
    print(f"Name: {supervisor.get('name', 'N/A')}")
    print(f"Title: {supervisor.get('title', 'N/A')}")
    print(f"Institution: {supervisor.get('institution', 'N/A')}")
    print(f"Domain: {supervisor.get('domain', 'N/A')}")
    print(f"Country: {supervisor.get('country', 'N/A')}")
    print(f"Region: {supervisor.get('region', 'N/A')}")
    print(f"Email: {supervisor.get('email', 'N/A')}")
    print(f"Email Confidence: {supervisor.get('email_confidence', 'N/A')}")
    print(f"Profile URL: {supervisor.get('profile_url', 'N/A')}")
    print(f"Homepage: {supervisor.get('homepage', 'N/A')}")
    print(f"Source URL: {supervisor.get('source_url', 'N/A')}")
    
    # Parse keywords
    keywords_json = supervisor.get('keywords_json', '[]')
    try:
        keywords = json.loads(keywords_json)
        print(f"Keywords: {', '.join(keywords) if keywords else 'None'}")
    except:
        print(f"Keywords: {supervisor.get('keywords_text', 'N/A')}")
    
    # Parse evidence
    evidence_json = supervisor.get('evidence_snippets_json', '[]')
    try:
        evidence = json.loads(evidence_json)
        print(f"Evidence: {' | '.join(evidence) if evidence else 'None'}")
    except:
        print(f"Evidence: {supervisor.get('evidence_email', 'N/A')}")
    
    print(f"Canonical ID: {supervisor.get('canonical_id', 'N/A')}")
    print(f"Last Seen: {supervisor.get('last_seen_at', 'N/A')}")
    print(f"Last Verified: {supervisor.get('last_verified_at', 'N/A')}")
    print("=" * 60)


def interactive_edit():
    """Interactive editor for supervisors."""
    print("=" * 60)
    print("Supervisor Database Editor")
    print("=" * 60)
    
    offset = 0
    limit = 20
    
    while True:
        print("\nOptions:")
        print("  1. List supervisors")
        print("  2. View supervisor by ID")
        print("  3. Edit supervisor field")
        print("  4. Delete supervisor")
        print("  5. Next page")
        print("  6. Previous page")
        print("  7. Exit")
        
        choice = input("\nEnter choice (1-7): ").strip()
        
        if choice == "1":
            print(f"\nListing supervisors (showing {limit} starting from {offset})...")
            rows = list_supervisors(limit, offset)
            if not rows:
                print("No supervisors found.")
            else:
                print(f"\n{'ID':<5} {'Name':<30} {'Institution':<25} {'Email':<30}")
                print("-" * 90)
                for row in rows:
                    id, name, institution, email, email_conf, title, keywords, profile_url, canonical_id = row
                    name_display = name[:28] + ".." if len(name) > 30 else name
                    inst_display = institution[:23] + ".." if len(institution) > 25 else institution
                    email_display = (email[:28] + ".." if email and len(email) > 30 else email) or "N/A"
                    print(f"{id:<5} {name_display:<30} {inst_display:<25} {email_display:<30}")
        
        elif choice == "2":
            try:
                supervisor_id = int(input("Enter supervisor ID: "))
                supervisor = get_supervisor_by_id(supervisor_id)
                if supervisor:
                    print_supervisor(supervisor)
                else:
                    print(f"Supervisor with ID {supervisor_id} not found.")
            except ValueError:
                print("Invalid ID. Please enter a number.")
        
        elif choice == "3":
            try:
                supervisor_id = int(input("Enter supervisor ID to edit: "))
                supervisor = get_supervisor_by_id(supervisor_id)
                if not supervisor:
                    print(f"Supervisor with ID {supervisor_id} not found.")
                    continue
                
                print_supervisor(supervisor)
                print("\nAvailable fields to edit:")
                print("  name, title, institution, domain, country, region,")
                print("  email, email_confidence, profile_url, homepage, source_url,")
                print("  keywords_json (comma-separated), evidence_snippets_json (comma-separated)")
                
                field = input("\nEnter field name to edit: ").strip()
                if not field:
                    print("Field name cannot be empty.")
                    continue
                
                current_value = supervisor.get(field, "")
                print(f"\nCurrent value: {current_value}")
                new_value = input("Enter new value (or press Enter to keep current): ").strip()
                
                if new_value:
                    if update_supervisor(supervisor_id, field, new_value):
                        print(f"✓ Successfully updated {field}")
                    else:
                        print(f"✗ Failed to update {field}")
                else:
                    print("No changes made.")
            except ValueError:
                print("Invalid ID. Please enter a number.")
        
        elif choice == "4":
            try:
                supervisor_id = int(input("Enter supervisor ID to delete: "))
                confirm = input(f"Are you sure you want to delete supervisor {supervisor_id}? (yes/no): ")
                if confirm.lower() == "yes":
                    if delete_supervisor(supervisor_id):
                        print(f"✓ Successfully deleted supervisor {supervisor_id}")
                    else:
                        print(f"✗ Failed to delete supervisor {supervisor_id}")
                else:
                    print("Deletion cancelled.")
            except ValueError:
                print("Invalid ID. Please enter a number.")
        
        elif choice == "5":
            offset += limit
            print(f"Moved to next page (offset: {offset})")
        
        elif choice == "6":
            offset = max(0, offset - limit)
            print(f"Moved to previous page (offset: {offset})")
        
        elif choice == "7":
            print("Exiting editor. Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter 1-7.")


if __name__ == "__main__":
    interactive_edit()

