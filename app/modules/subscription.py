"""Subscription management module for PhD Supervisor Finder."""

import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.db_cloud import get_db_connection
from app.config import DEVELOPER_EMAILS, BETA_USERS


# Subscription plans
PLANS = {
    "free": {
        "searches_per_month": 1,
        "price_usd": 0,
        "name": "Free Trial"
    },
    "individual": {
        "searches_per_month": 3,
        "price_usd": 16,  # Price in GBP: £16
        "name": "Individual Monthly"
    },
    "enterprise": {
        "searches_per_month": 10,
        "price_usd": 48,  # Price in GBP: £48
        "name": "Enterprise Monthly"
    }
}


def is_developer(email: str) -> bool:
    """Check if email is a developer email with unlimited access."""
    return email.lower().strip() in DEVELOPER_EMAILS


def is_beta_user(email: str) -> bool:
    """Check if email is a beta user."""
    return email.lower().strip() in BETA_USERS


def get_beta_free_searches_count(email: str) -> int:
    """Get the number of free searches allocated to a beta user."""
    return BETA_USERS.get(email.lower().strip(), 0)


def get_or_create_user(email: str) -> int:
    """Get user ID by email, create user if not exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    now = datetime.now()
    
    if db_type == "postgresql":
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        
        if row:
            user_id = row[0]
            # Update last login
            cursor.execute("UPDATE users SET last_login_at = %s WHERE id = %s", (now, user_id))
            # Initialize beta free searches if user is beta and not yet initialized
            if is_beta_user(email):
                cursor.execute("SELECT beta_free_searches_remaining FROM users WHERE id = %s", (user_id,))
                beta_searches = cursor.fetchone()[0]
                if beta_searches is None:
                    free_searches = get_beta_free_searches_count(email)
                    cursor.execute(
                        "UPDATE users SET beta_free_searches_remaining = %s WHERE id = %s",
                        (free_searches, user_id)
                    )
        else:
            # Create new user
            beta_searches = None
            if is_beta_user(email):
                beta_searches = get_beta_free_searches_count(email)
            
            cursor.execute(
                "INSERT INTO users (email, created_at, last_login_at, beta_free_searches_remaining) VALUES (%s, %s, %s, %s) RETURNING id",
                (email, now, now, beta_searches)
            )
            user_id = cursor.fetchone()[0]
            # Create free trial subscription
            expires_at = now + timedelta(days=365)  # Free trial doesn't expire for a year
            cursor.execute(
                """INSERT INTO subscriptions 
                   (user_id, subscription_type, status, searches_per_month, remaining_searches, started_at, expires_at, created_at, updated_at)
                   VALUES (%s, 'free', 'active', %s, %s, %s, %s, %s, %s)""",
                (user_id, PLANS["free"]["searches_per_month"], PLANS["free"]["searches_per_month"], now, expires_at, now, now)
            )
    else:
        # SQLite
        now_str = now.isoformat()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            user_id = row[0]
            # Update last login
            cursor.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_str, user_id))
            # Initialize beta free searches if user is beta and not yet initialized
            if is_beta_user(email):
                cursor.execute("SELECT beta_free_searches_remaining FROM users WHERE id = ?", (user_id,))
                beta_searches = cursor.fetchone()[0]
                if beta_searches is None:
                    free_searches = get_beta_free_searches_count(email)
                    cursor.execute(
                        "UPDATE users SET beta_free_searches_remaining = ? WHERE id = ?",
                        (free_searches, user_id)
                    )
        else:
            # Create new user
            beta_searches = None
            if is_beta_user(email):
                beta_searches = get_beta_free_searches_count(email)
            
            cursor.execute(
                "INSERT INTO users (email, created_at, last_login_at, beta_free_searches_remaining) VALUES (?, ?, ?, ?)",
                (email, now_str, now_str, beta_searches)
            )
            user_id = cursor.lastrowid
            # Create free trial subscription
            expires_at = (now + timedelta(days=365)).isoformat()  # Free trial doesn't expire for a year
            cursor.execute(
                """INSERT INTO subscriptions 
                   (user_id, subscription_type, status, searches_per_month, remaining_searches, started_at, expires_at, created_at, updated_at)
                   VALUES (?, 'free', 'active', ?, ?, ?, ?, ?, ?)""",
                (user_id, PLANS["free"]["searches_per_month"], PLANS["free"]["searches_per_month"], now_str, expires_at, now_str, now_str)
            )
    
    conn.commit()
    conn.close()
    return user_id


def get_user_email(user_id: int) -> Optional[str]:
    """Get user email by user ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    else:
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else None


def get_beta_free_searches_remaining(user_id: int) -> Optional[int]:
    """Get remaining beta free searches for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        cursor.execute("SELECT beta_free_searches_remaining FROM users WHERE id = %s", (user_id,))
    else:
        cursor.execute("SELECT beta_free_searches_remaining FROM users WHERE id = ?", (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row and row[0] is not None else None


def get_user_subscription(user_id: int) -> Optional[dict]:
    """Get active subscription for user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    now = datetime.now()
    now_str = now.isoformat()
    
    if db_type == "postgresql":
        cursor.execute(
            """SELECT id, subscription_type, status, searches_per_month, remaining_searches, 
                      started_at, expires_at 
               FROM subscriptions 
               WHERE user_id = %s AND status = 'active' 
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,)
        )
    else:
        cursor.execute(
            """SELECT id, subscription_type, status, searches_per_month, remaining_searches, 
                      started_at, expires_at 
               FROM subscriptions 
               WHERE user_id = ? AND status = 'active' 
               ORDER BY created_at DESC LIMIT 1""",
            (user_id,)
        )
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    # Check if subscription expired
    expires_at = row[6]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    
    if expires_at < now:
        # Mark as expired
        mark_subscription_expired(row[0])
        return None
    
    return {
        "id": row[0],
        "type": row[1],
        "status": row[2],
        "searches_per_month": row[3],
        "remaining_searches": row[4],
        "started_at": row[5],
        "expires_at": expires_at
    }


def mark_subscription_expired(subscription_id: int) -> None:
    """Mark subscription as expired."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    now = datetime.now()
    
    if db_type == "postgresql":
        cursor.execute(
            "UPDATE subscriptions SET status = 'expired', updated_at = %s WHERE id = %s",
            (now, subscription_id)
        )
    else:
        cursor.execute(
            "UPDATE subscriptions SET status = 'expired', updated_at = ? WHERE id = ?",
            (now.isoformat(), subscription_id)
        )
    
    conn.commit()
    conn.close()


def can_perform_search(user_id: int) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Check if user can perform a search.
    Returns: (can_search, error_message, subscription_info)
    
    Priority:
    1. Developers (email in DEVELOPER_EMAILS) - unlimited access
    2. Beta users with free searches remaining
    3. Regular subscriptions
    """
    # Check if user is a developer
    user_email = get_user_email(user_id)
    if user_email and is_developer(user_email):
        # Developers have unlimited access - return a special subscription dict
        return True, None, {
            "id": None,
            "type": "developer",
            "status": "active",
            "searches_per_month": 999999,
            "remaining_searches": 999999,
            "started_at": None,
            "expires_at": None
        }
    
    # Check if user is a beta user with free searches remaining
    if user_email and is_beta_user(user_email):
        beta_searches = get_beta_free_searches_remaining(user_id)
        if beta_searches is not None and beta_searches > 0:
            # Beta user has free searches remaining
            return True, None, {
                "id": None,
                "type": "beta",
                "status": "active",
                "searches_per_month": get_beta_free_searches_count(user_email),
                "remaining_searches": beta_searches,
                "started_at": None,
                "expires_at": None
            }
    
    # Check regular subscription
    subscription = get_user_subscription(user_id)
    
    if not subscription:
        # If beta user but no free searches left, show message
        if user_email and is_beta_user(user_email):
            return False, "Your beta free searches have been used. Please subscribe to continue.", None
        return False, "No active subscription. Please subscribe to continue.", None
    
    # Check if we need to reset monthly quota (check on every call, not just when remaining is 0)
    reset_monthly_quota_if_needed(subscription["id"])
    
    # Refresh subscription info after potential reset
    subscription = get_user_subscription(user_id)
    if not subscription:
        if user_email and is_beta_user(user_email):
            return False, "Your beta free searches have been used. Please subscribe to continue.", None
        return False, "No active subscription. Please subscribe to continue.", None
    
    if subscription["remaining_searches"] <= 0:
        return False, "No searches remaining. Please upgrade your subscription or wait for monthly reset.", subscription
    
    return True, None, subscription


def reset_monthly_quota_if_needed(subscription_id: int) -> None:
    """Reset monthly search quota if a new month has started."""
    subscription = get_subscription_by_id(subscription_id)
    if not subscription:
        return
    
    started_at = subscription["started_at"]
    if isinstance(started_at, str):
        started_at = datetime.fromisoformat(started_at)
    
    now = datetime.now()
    # Check if we're in a new month
    if started_at.year < now.year or (started_at.year == now.year and started_at.month < now.month):
        # Reset quota
        conn = get_db_connection()
        cursor = conn.cursor()
        
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        searches_per_month = subscription["searches_per_month"]
        
        if db_type == "postgresql":
            cursor.execute(
                """UPDATE subscriptions 
                   SET remaining_searches = %s, started_at = %s, updated_at = %s 
                   WHERE id = %s""",
                (searches_per_month, now, now, subscription_id)
            )
        else:
            cursor.execute(
                """UPDATE subscriptions 
                   SET remaining_searches = ?, started_at = ?, updated_at = ? 
                   WHERE id = ?""",
                (searches_per_month, now.isoformat(), now.isoformat(), subscription_id)
            )
        
        conn.commit()
        conn.close()


def get_subscription_by_id(subscription_id: int) -> Optional[dict]:
    """Get subscription by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        cursor.execute(
            """SELECT id, subscription_type, status, searches_per_month, remaining_searches, 
                      started_at, expires_at 
               FROM subscriptions WHERE id = %s""",
            (subscription_id,)
        )
    else:
        cursor.execute(
            """SELECT id, subscription_type, status, searches_per_month, remaining_searches, 
                      started_at, expires_at 
               FROM subscriptions WHERE id = ?""",
            (subscription_id,)
        )
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "type": row[1],
        "status": row[2],
        "searches_per_month": row[3],
        "remaining_searches": row[4],
        "started_at": row[5],
        "expires_at": row[6]
    }


def consume_search(user_id: int, subscription_id: Optional[int], search_info: dict) -> None:
    """
    Consume one search from user's subscription and log it.
    
    Priority:
    1. Beta users: consume from beta_free_searches_remaining first
    2. Regular subscriptions: consume from subscription
    3. Developers: don't consume (unlimited)
    
    Args:
        user_id: User ID
        subscription_id: Subscription ID (None for developers/beta users)
        search_info: Dict with keys: keywords, universities_count, regions, countries, result_count
    """
    # Check if user is a developer
    user_email = get_user_email(user_id)
    is_dev = user_email and is_developer(user_email)
    is_beta = user_email and is_beta_user(user_email)
    
    # Prepare variables for logging
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    now = datetime.now()
    
    # Developers don't consume searches
    if is_dev:
        search_type = "developer"
        subscription_id_for_log = None
    elif is_beta:
        # Check if beta user has free searches remaining
        beta_searches = get_beta_free_searches_remaining(user_id)
        if beta_searches is not None and beta_searches > 0:
            # Consume from beta free searches
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if db_type == "postgresql":
                cursor.execute(
                    "UPDATE users SET beta_free_searches_remaining = beta_free_searches_remaining - 1 WHERE id = %s",
                    (user_id,)
                )
            else:
                cursor.execute(
                    "UPDATE users SET beta_free_searches_remaining = beta_free_searches_remaining - 1 WHERE id = ?",
                    (user_id,)
                )
            
            conn.commit()
            conn.close()
            
            search_type = "beta"
            subscription_id_for_log = None
        else:
            # Beta user has no free searches left, use regular subscription
            if subscription_id is None:
                search_type = "beta"
                subscription_id_for_log = None
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                subscription = get_subscription_by_id(subscription_id)
                if not subscription:
                    conn.close()
                    return
                
                search_type = subscription["type"]
                subscription_id_for_log = subscription_id
                
                # Decrement remaining searches (only for non-developers)
                if db_type == "postgresql":
                    cursor.execute(
                        "UPDATE subscriptions SET remaining_searches = remaining_searches - 1, updated_at = %s WHERE id = %s",
                        (now, subscription_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE subscriptions SET remaining_searches = remaining_searches - 1, updated_at = ? WHERE id = ?",
                        (now.isoformat(), subscription_id)
                    )
                
                conn.commit()
                conn.close()
    elif subscription_id is None:
        search_type = "free"
        subscription_id_for_log = None
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        subscription = get_subscription_by_id(subscription_id)
        if not subscription:
            conn.close()
            return
        
        search_type = subscription["type"]
        subscription_id_for_log = subscription_id
        
        # Decrement remaining searches (only for non-developers)
        if db_type == "postgresql":
            cursor.execute(
                "UPDATE subscriptions SET remaining_searches = remaining_searches - 1, updated_at = %s WHERE id = %s",
                (now, subscription_id)
            )
        else:
            cursor.execute(
                "UPDATE subscriptions SET remaining_searches = remaining_searches - 1, updated_at = ? WHERE id = ?",
                (now.isoformat(), subscription_id)
            )
        
        conn.commit()
        conn.close()
    
    # Log the search (for both developers and regular users)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if db_type == "postgresql":
        cursor.execute(
            """INSERT INTO search_logs 
               (user_id, subscription_id, search_type, keywords, universities_count, regions, countries, result_count, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id, subscription_id_for_log, search_type,
                search_info.get("keywords"), search_info.get("universities_count"),
                search_info.get("regions"), search_info.get("countries"),
                search_info.get("result_count"), now
            )
        )
    else:
        cursor.execute(
            """INSERT INTO search_logs 
               (user_id, subscription_id, search_type, keywords, universities_count, regions, countries, result_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, subscription_id_for_log, search_type,
                search_info.get("keywords"), search_info.get("universities_count"),
                search_info.get("regions"), search_info.get("countries"),
                search_info.get("result_count"), now.isoformat()
            )
        )
    
    conn.commit()
    conn.close()


def create_subscription(user_id: int, subscription_type: str) -> int:
    """
    Create a new subscription for user.
    
    Args:
        user_id: User ID
        subscription_type: 'individual' or 'enterprise'
    
    Returns:
        Subscription ID
    """
    if subscription_type not in ["individual", "enterprise"]:
        raise ValueError(f"Invalid subscription type: {subscription_type}")
    
    # Cancel existing active subscription
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    now = datetime.now()
    
    if db_type == "postgresql":
        cursor.execute(
            "UPDATE subscriptions SET status = 'cancelled', updated_at = %s WHERE user_id = %s AND status = 'active'",
            (now, user_id)
        )
    else:
        cursor.execute(
            "UPDATE subscriptions SET status = 'cancelled', updated_at = ? WHERE user_id = ? AND status = 'active'",
            (now.isoformat(), user_id)
        )
    
    # Create new subscription (monthly)
    plan = PLANS[subscription_type]
    expires_at = now + timedelta(days=30)
    
    if db_type == "postgresql":
        cursor.execute(
            """INSERT INTO subscriptions 
               (user_id, subscription_type, status, searches_per_month, remaining_searches, started_at, expires_at, created_at, updated_at)
               VALUES (%s, %s, 'active', %s, %s, %s, %s, %s, %s) RETURNING id""",
            (user_id, subscription_type, plan["searches_per_month"], plan["searches_per_month"], now, expires_at, now, now)
        )
        subscription_id = cursor.fetchone()[0]
    else:
        cursor.execute(
            """INSERT INTO subscriptions 
               (user_id, subscription_type, status, searches_per_month, remaining_searches, started_at, expires_at, created_at, updated_at)
               VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?)""",
            (user_id, subscription_type, plan["searches_per_month"], plan["searches_per_month"], 
             now.isoformat(), expires_at.isoformat(), now.isoformat(), now.isoformat())
        )
        subscription_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return subscription_id


def get_user_search_history(user_id: int, limit: int = 10) -> list:
    """Get user's search history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        cursor.execute(
            """SELECT id, search_type, keywords, result_count, created_at 
               FROM search_logs 
               WHERE user_id = %s 
               ORDER BY created_at DESC 
               LIMIT %s""",
            (user_id, limit)
        )
    else:
        cursor.execute(
            """SELECT id, search_type, keywords, result_count, created_at 
               FROM search_logs 
               WHERE user_id = ? 
               ORDER BY created_at DESC 
               LIMIT ?""",
            (user_id, limit)
        )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row[0],
            "type": row[1],
            "keywords": row[2],
            "result_count": row[3],
            "created_at": row[4]
        }
        for row in rows
    ]

