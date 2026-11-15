import sqlite3
import os

DB_PATH = "tracker.db"
SCHEMA_PATH = "tracker.sql"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH) as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()
    conn.close()

def clear_db():
    conn = get_connection()
    conn.executescript("""
                       DELETE FROM skipped_rows;
                       DELETE FROM transactions;
                       DELETE FROM uploads;
                       DELETE FROM users;"""
                       )
    conn.commit()
    conn.close()