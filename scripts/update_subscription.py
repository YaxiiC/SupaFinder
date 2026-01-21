"""Script to update user subscription (remaining searches or set as developer)."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.modules.subscription import get_or_create_user, get_user_subscription
from app.db_cloud import get_db_connection, init_db
import os
from datetime import datetime


def update_remaining_searches(email: str, remaining_searches: int):
    """Update remaining searches for a user's subscription."""
    init_db()
    
    # Get or create user
    user_id = get_or_create_user(email)
    print(f"User ID: {user_id}")
    
    # Get current subscription
    subscription = get_user_subscription(user_id)
    
    if not subscription:
        print(f"❌ No active subscription found for {email}")
        print("   Please create a subscription first using the UI or create_subscription function.")
        return False
    
    # Update remaining searches
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Use get_secret to support both local env and Streamlit secrets
    from app.config import get_secret
    db_type = get_secret("DB_TYPE", "sqlite").lower()
    now = datetime.now()
    
    print(f"   Database type: {db_type}")
    
    if db_type == "postgresql":
        cursor.execute(
            "UPDATE subscriptions SET remaining_searches = %s, updated_at = %s WHERE id = %s",
            (remaining_searches, now, subscription["id"])
        )
    else:
        cursor.execute(
            "UPDATE subscriptions SET remaining_searches = ?, updated_at = ? WHERE id = ?",
            (remaining_searches, now.isoformat(), subscription["id"])
        )
    
    conn.commit()
    conn.close()
    
    print(f"✅ Updated remaining searches to {remaining_searches} for {email}")
    
    # Verify
    updated_subscription = get_user_subscription(user_id)
    if updated_subscription:
        print(f"   Current subscription: {updated_subscription['type']}")
        print(f"   Remaining searches: {updated_subscription['remaining_searches']}")
        print(f"   Searches per month: {updated_subscription['searches_per_month']}")
    
    return True


def check_developer_mode(email: str):
    """Check if email is configured as developer."""
    from app.config import DEVELOPER_EMAILS
    
    is_dev = email.lower().strip() in DEVELOPER_EMAILS
    
    if is_dev:
        print(f"✅ {email} is configured as DEVELOPER (unlimited access)")
        print(f"   Developer emails configured: {DEVELOPER_EMAILS}")
    else:
        print(f"❌ {email} is NOT configured as developer")
        print(f"   Currently configured developer emails: {DEVELOPER_EMAILS}")
        print(f"\n   To set as developer, add to Streamlit Secrets:")
        print(f'   DEVELOPER_EMAILS = "{email}"')
        print(f"   (Or append to existing: DEVELOPER_EMAILS = \"existing@email.com,{email}\")")
    
    return is_dev


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update user subscription")
    parser.add_argument("email", help="User email address")
    parser.add_argument("--remaining", type=int, help="Set remaining searches (e.g., 999)")
    parser.add_argument("--check-dev", action="store_true", help="Check if email is configured as developer")
    parser.add_argument("--db-type", choices=["sqlite", "postgresql"], help="Force database type (default: auto-detect)")
    
    args = parser.parse_args()
    
    email = args.email.lower().strip()
    
    # Override DB_TYPE if specified
    if args.db_type:
        os.environ["DB_TYPE"] = args.db_type
        print(f"Using database type: {args.db_type}")
    
    if args.check_dev:
        check_developer_mode(email)
    elif args.remaining is not None:
        update_remaining_searches(email, args.remaining)
    else:
        # Check both
        print(f"Checking subscription for: {email}\n")
        
        # Check developer mode
        check_developer_mode(email)
        print()
        
        # Check subscription
        user_id = get_or_create_user(email)
        subscription = get_user_subscription(user_id)
        
        if subscription:
            print(f"Current subscription:")
            print(f"  Type: {subscription['type']}")
            print(f"  Remaining searches: {subscription['remaining_searches']}")
            print(f"  Searches per month: {subscription['searches_per_month']}")
        else:
            print("No active subscription found.")
        
        # Show database info
        from app.config import get_secret
        db_type = get_secret("DB_TYPE", "sqlite").lower()
        print(f"\nDatabase: {db_type}")
        if db_type == "postgresql":
            db_host = get_secret("DB_HOST", "not set")
            print(f"  Host: {db_host}")

