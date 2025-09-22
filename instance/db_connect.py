from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent   # social network/
DB_PATH = BASE_DIR / "instance" / "app.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
