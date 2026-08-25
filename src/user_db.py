import os
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = "data/user_history.db"

def hash_password(password: str, salt: bytes = None) -> Tuple[str, str]:
    """Generates a secure password hash using PBKDF2 native cryptography."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return key.hex(), salt.hex()

def verify_password(stored_hash: str, stored_salt: str, password: str) -> bool:
    """Verifies a password against the stored hash and salt values."""
    salt_bytes = bytes.fromhex(stored_salt)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 100000)
    return key.hex() == stored_hash

def init_user_db():
    """Initializes the database and runs any required schema migrations."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            salt TEXT,
            created_at TEXT
        )
    """)
    
    # 2. Create guess_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guess_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            timestamp TEXT,
            game TEXT,
            main_numbers TEXT,
            powerball INTEGER,
            is_valid INTEGER,
            validation_message TEXT,
            odd_even_ratio TEXT,
            draw_sum INTEGER,
            average_frequency REAL,
            historic_match TEXT
        )
    """)
    
    # 3. Check for schema migration (add username column to legacy DB if needed)
    cursor.execute("PRAGMA table_info(guess_history)")
    columns = [col[1] for col in cursor.fetchall()]
    if "username" not in columns:
        try:
            cursor.execute("ALTER TABLE guess_history ADD COLUMN username TEXT")
            cursor.execute("UPDATE guess_history SET username = 'Guest' WHERE username IS NULL")
        except sqlite3.OperationalError:
            pass
            
    conn.commit()
    conn.close()

def create_user(username: str, password: str) -> Tuple[bool, str]:
    """Creates a new user profile with secure hashing."""
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."
        
    init_user_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check uniqueness
    cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return False, "Username already exists."
        
    password_hash, salt = hash_password(password)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
            (username, password_hash, salt, created_at)
        )
        conn.commit()
        success = True
        msg = "User created successfully."
    except Exception as e:
        success = False
        msg = f"Database error: {e}"
        
    conn.close()
    return success, msg

def authenticate_user(username: str, password: str) -> bool:
    """Authenticates a user against their stored hash."""
    username = username.strip()
    if not username or not password:
        return False
        
    init_user_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False
        
    stored_hash, stored_salt = row
    return verify_password(stored_hash, stored_salt, password)

def save_user_guess(
    game: str,
    main_numbers: List[int],
    powerball: Optional[int],
    is_valid: bool,
    validation_message: str,
    username: str = "Guest",
    odd_even_ratio: str = "",
    draw_sum: int = 0,
    average_frequency: float = 0.0,
    historic_match: str = "No Match"
):
    """Saves a user's guess linked to their username profile."""
    init_user_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    main_numbers_str = ",".join(map(str, sorted(main_numbers)))
    
    cursor.execute("""
        INSERT INTO guess_history (
            username, timestamp, game, main_numbers, powerball, is_valid, 
            validation_message, odd_even_ratio, draw_sum, 
            average_frequency, historic_match
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        username,
        timestamp,
        game,
        main_numbers_str,
        powerball,
        1 if is_valid else 0,
        validation_message,
        odd_even_ratio,
        draw_sum,
        average_frequency,
        historic_match
    ))
    
    conn.commit()
    conn.close()

def get_user_history(game: Optional[str] = None, username: str = "Guest") -> List[Dict[str, Any]]:
    """Retrieves guess history associated with a specific username."""
    init_user_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if game:
        cursor.execute("SELECT * FROM guess_history WHERE game = ? AND username = ? ORDER BY id DESC", (game, username))
    else:
        cursor.execute("SELECT * FROM guess_history WHERE username = ? ORDER BY id DESC", (username,))
        
    rows = cursor.fetchall()
    history = [dict(row) for row in rows]
    conn.close()
    return history

def clear_user_history(game: Optional[str] = None, username: str = "Guest"):
    """Clears history from the database for a specific user."""
    init_user_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if game:
        cursor.execute("DELETE FROM guess_history WHERE game = ? AND username = ?", (game, username))
    else:
        cursor.execute("DELETE FROM guess_history WHERE username = ?", (username,))
        
    conn.commit()
    conn.close()
