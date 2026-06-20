import logging
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DB_PATH = "/tmp/roast_toast.db"

_tables_ready = False


@contextmanager
def get_db():
    """Yield a connection and always close it afterwards (fixes a connection leak)."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
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
    _tables_ready = True


def execute_write(query: str, params: tuple = ()):
    ensure_tables()
    with get_db() as db:
        db.execute(query, params)
        db.commit()


def execute_read(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    ensure_tables()
    try:
        with get_db() as db:
            cursor = db.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        logger.exception("DB read failed for query: %s", query)
        return []


def create_api_key(api_key: str):
    execute_write("INSERT INTO users (api_key) VALUES (?)", (api_key,))


def is_valid_key(api_key: str) -> bool:
    res = execute_read("SELECT 1 FROM users WHERE api_key = ?", (api_key,))
    return len(res) > 0


def save_interaction(api_key: str, target: str, type_str: str, result: str):
    execute_write(
        "INSERT INTO interactions (api_key, target_username, interaction_type, result_text) VALUES (?, ?, ?, ?)",
        (api_key, target, type_str, result)
    )


def get_user_history(api_key: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    return execute_read(
        "SELECT id, target_username, interaction_type, result_text, created_at FROM interactions WHERE api_key = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (api_key, limit, offset)
    )


def get_all_users() -> List[Dict[str, Any]]:
    return execute_read("SELECT api_key, created_at FROM users ORDER BY created_at DESC")


def get_all_history(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    return execute_read(
        "SELECT id, api_key, target_username, interaction_type, created_at FROM interactions ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )