import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "data/user_history.db"

def init_user_db():
    """Initializes the user history database and creates the guess_history table if missing."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guess_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    conn.commit()
    conn.close()

def save_user_guess(
    game: str,
    main_numbers: List[int],
    powerball: Optional[int],
    is_valid: bool,
    validation_message: str,
    odd_even_ratio: str = "",
    draw_sum: int = 0,
    average_frequency: float = 0.0,
    historic_match: str = "No Match"
):
    """Saves a user's guess and its statistical analysis to the database."""
    init_user_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    main_numbers_str = ",".join(map(str, sorted(main_numbers)))
    
    cursor.execute("""
        INSERT INTO guess_history (
            timestamp, game, main_numbers, powerball, is_valid, 
            validation_message, odd_even_ratio, draw_sum, 
            average_frequency, historic_match
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
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

def get_user_history(game: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves saved guess history, optionally filtered by game."""
    init_user_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if game:
        cursor.execute("SELECT * FROM guess_history WHERE game = ? ORDER BY id DESC", (game,))
    else:
        cursor.execute("SELECT * FROM guess_history ORDER BY id DESC")
        
    rows = cursor.fetchall()
    history = [dict(row) for row in rows]
    conn.close()
    return history

def clear_user_history(game: Optional[str] = None):
    """Clears history from the database, optionally filtered by game."""
    init_user_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if game:
        cursor.execute("DELETE FROM guess_history WHERE game = ?", (game,))
    else:
        cursor.execute("DELETE FROM guess_history")
        
    conn.commit()
    conn.close()
