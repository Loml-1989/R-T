import sqlite3
import os
from typing import List, Dict, Any

DB_PATH = "/tmp/roast_toast.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                api_key TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        db.execute("""
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
        db.commit()

# Self-initialize on module load safely
try:
    setup_database()
except Exception:
    pass

def create_api_key(api_key: str):
    setup_database()  # Safety check
    with get_db() as db:
        db.execute("INSERT INTO users (api_key) VALUES (?)", (api_key,))
        db.commit()

def is_valid_key(api_key: str) -> bool:
    try:
        setup_database()
        with get_db() as db:
            cursor = db.execute("SELECT 1 FROM users WHERE api_key = ?", (api_key,))
            return cursor.fetchone() is not None
    except Exception:
        return False

def save_interaction(api_key: str, target: str, type_str: str, result: str):
    setup_database()
    with get_db() as db:
        db.execute(
            "INSERT INTO interactions (api_key, target_username, interaction_type, result_text) VALUES (?, ?, ?, ?)",
            (api_key, target, type_str, result)
        )
        db.commit()

def get_user_history(api_key: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    try:
        setup_database()
        with get_db() as db:
            cursor = db.execute(
                "SELECT id, target_username, interaction_type, result_text, created_at FROM interactions WHERE api_key = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (api_key, limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []

def get_all_users() -> List[Dict[str, Any]]:
    try:
        setup_database()
        with get_db() as db:
            cursor = db.execute("SELECT api_key, created_at FROM users ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []

def get_all_history(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    try:
        setup_database()
        with get_db() as db:
            cursor = db.execute(
                "SELECT id, api_key, target_username, interaction_type, created_at FROM interactions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []