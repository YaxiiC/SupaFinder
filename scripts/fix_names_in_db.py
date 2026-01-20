"""Fix names in database that start with 'essor' or contain 'Professor' incorrectly."""

import sys
import sqlite3
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import CACHE_DB


def clean_name(name: str) -> str:
    """Clean name by removing titles and fixing 'essor' issue."""
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
        # Also remove if it appears anywhere
        pattern = r'\b' + re.escape(prefix) + r'\b'
        name = re.sub(pattern, '', name, flags=re.IGNORECASE).strip()
    
    # Remove "essor" if it appears at the start (leftover from "Professor")
    if name.lower().startswith("essor "):
        name = name[6:].strip()
    elif name.lower().startswith("essor"):
        name = name[5:].strip()
    
    # Clean up multiple spaces
    name = " ".join(name.split())
    
    return name.strip()


def fix_names_in_database():
    """Fix all names in the database."""
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    
    # Get all supervisors
    cursor.execute("SELECT id, name FROM supervisors")
    rows = cursor.fetchall()
    
    fixed_count = 0
    for supervisor_id, original_name in rows:
        cleaned_name = clean_name(original_name)
        
        if cleaned_name != original_name and cleaned_name:
            # Update the name
            cursor.execute("UPDATE supervisors SET name = ?, updated_at = datetime('now') WHERE id = ?", 
                          (cleaned_name, supervisor_id))
            print(f"Fixed ID {supervisor_id}: '{original_name}' -> '{cleaned_name}'")
            fixed_count += 1
        elif not cleaned_name:
            print(f"Warning: ID {supervisor_id} name '{original_name}' became empty after cleaning, skipping")
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Fixed {fixed_count} names in the database")


if __name__ == "__main__":
    print("Fixing names in database...")
    fix_names_in_database()

