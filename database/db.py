import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash


DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "expense_tracker.db")
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()
    (existing,) = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    if existing > 0:
        conn.close()
        return

    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    user_id = cur.lastrowid

    today = date.today()
    expenses = [
        (user_id, 4500.00, "Bills",         today.replace(day=2).isoformat(),  "Electricity bill"),
        (user_id,  320.50, "Food",          today.replace(day=5).isoformat(),  "Groceries"),
        (user_id,  180.00, "Transport",     today.replace(day=8).isoformat(),  "Metro pass"),
        (user_id,  850.00, "Health",        today.replace(day=12).isoformat(), "Pharmacy"),
        (user_id,  499.00, "Entertainment", today.replace(day=15).isoformat(), "Streaming subscription"),
        (user_id, 1250.00, "Shopping",      today.replace(day=19).isoformat(), "T-shirt"),
        (user_id,  410.00, "Food",          today.replace(day=23).isoformat(), "Dinner out"),
        (user_id,  200.00, "Other",         today.replace(day=27).isoformat(), "Misc"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()
