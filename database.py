import sqlite3
from typing import List, Dict, Any

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect("roast_toast.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            api_key TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT,
            target_username TEXT,
            interaction_type TEXT,
            result_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (api_key) REFERENCES users (api_key)
        )
    """)

    conn.commit()
    conn.close()

def create_user(api_key: str) -> None:
    conn = get_db_connection()
    conn.execute("INSERT INTO users (api_key) VALUES (?)", (api_key,))
    conn.commit()
    conn.close()

def verify_user(api_key: str) -> bool:
    conn = get_db_connection()
    cursor = conn.execute("SELECT 1 FROM users WHERE api_key = ?", (api_key,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def log_interaction(api_key: str, target: str, i_type: str, result: str) -> None:
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO interactions (api_key, target_username, interaction_type, result_text) VALUES (?, ?, ?, ?)",
        (api_key, target, i_type, result)
    )
    conn.commit()
    conn.close()

def get_history(api_key: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT id, target_username, interaction_type, result_text, created_at FROM interactions WHERE api_key = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (api_key, limit, offset)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]