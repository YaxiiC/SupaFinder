"""Authentication module for user login and registration."""

import os
import bcrypt
from typing import Optional, Tuple
from app.db_cloud import get_db_connection
from app.config import get_secret


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    return password_hash.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    if not password_hash:
        return False
    
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def set_user_password(user_id: int, password: str) -> bool:
    """Set password for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    password_hash = hash_password(password)
    
    try:
        if db_type == "postgresql":
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (password_hash, user_id)
            )
        else:
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id)
            )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        raise Exception(f"Failed to set password: {e}")


def user_exists(email: str) -> bool:
    """Check if a user exists in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        cursor.execute("SELECT id FROM users WHERE email = %s", (email.lower().strip(),))
    else:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email.lower().strip(),))
    
    row = cursor.fetchone()
    conn.close()
    
    return row is not None


def verify_user_password(email: str, password: str) -> Tuple[bool, Optional[int]]:
    """
    Verify user password.
    
    SECURITY: Password is always required. Users without passwords cannot login.
    
    Returns:
        (is_valid, user_id) - is_valid is True if password is correct, user_id is the user ID
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        cursor.execute("SELECT id, password_hash FROM users WHERE email = %s", (email.lower().strip(),))
    else:
        cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (email.lower().strip(),))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False, None
    
    user_id, password_hash = row
    
    # SECURITY: Password is always required - no password means cannot login
    if password_hash is None:
        return False, None
    
    # Verify password
    if verify_password(password, password_hash):
        return True, user_id
    else:
        return False, None


def user_has_password(email: str) -> bool:
    """Check if user has a password set."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "postgresql":
        cursor.execute("SELECT password_hash FROM users WHERE email = %s", (email.lower().strip(),))
    else:
        cursor.execute("SELECT password_hash FROM users WHERE email = ?", (email.lower().strip(),))
    
    row = cursor.fetchone()
    conn.close()
    
    return row and row[0] is not None


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength.
    
    Returns:
        (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    # Check for at least one letter and one number
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)
    
    if not has_letter:
        return False, "Password must contain at least one letter"
    
    if not has_number:
        return False, "Password must contain at least one number"
    
    return True, None

