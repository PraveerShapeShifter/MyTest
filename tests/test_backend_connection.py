"""
Tests for Step 5: Backend Connection.

Unit tests patch database.queries.get_db with an in-memory SQLite database so
they never touch the on-disk expense_tracker.db.

Route tests use the Flask test client against the real app (which auto-seeds
on startup), authenticating by writing directly to the session.
"""
import sqlite3

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEED_EXPENSES = [
    (4500.00, "Bills",         "2026-06-02", "Electricity bill"),
    ( 320.50, "Food",          "2026-06-05", "Groceries"),
    ( 180.00, "Transport",     "2026-06-08", "Metro pass"),
    ( 850.00, "Health",        "2026-06-12", "Pharmacy"),
    ( 499.00, "Entertainment", "2026-06-15", "Streaming subscription"),
    (1250.00, "Shopping",      "2026-06-19", "T-shirt"),
    ( 410.00, "Food",          "2026-06-23", "Dinner out"),
    ( 200.00, "Other",         "2026-06-27", "Misc"),
]
SEED_TOTAL = sum(e[0] for e in SEED_EXPENSES)  # 8209.50


def _make_db():
    """Return an in-memory SQLite connection pre-seeded with one user + 8 expenses."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        CREATE TABLE users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );
        CREATE TABLE expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("Test User", "test@test.com", generate_password_hash("pw"), "2026-01-15 09:00:00"),
    )
    user_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        [(user_id, *e) for e in SEED_EXPENSES],
    )
    conn.commit()
    return conn, user_id


@pytest.fixture
def db_with_user():
    conn, user_id = _make_db()
    yield conn, user_id
    conn.close()


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _no_close(conn):
    """Wrap a connection so close() is a no-op (prevents in-memory DB teardown)."""
    class _Proxy:
        def execute(self, *a, **kw):
            return conn.execute(*a, **kw)
        def close(self):
            pass
    return _Proxy()


def _patch(monkeypatch, conn):
    """Patch database.queries.get_db to return a no-close proxy of conn."""
    proxy = _no_close(conn)
    monkeypatch.setattr("database.queries.get_db", lambda: proxy)


# ---------------------------------------------------------------------------
# Unit tests — get_user_by_id
# ---------------------------------------------------------------------------

class TestGetUserById:
    def test_existing_user_returns_dict(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        result = get_user_by_id(user_id)
        assert result is not None
        assert result["name"] == "Test User"
        assert result["email"] == "test@test.com"
        assert result["initials"] == "TU"
        assert result["member_since"] == "January 2026"

    def test_nonexistent_user_returns_none(self, db_with_user, monkeypatch):
        conn, _ = db_with_user
        _patch(monkeypatch, conn)
        assert get_user_by_id(99999) is None


# ---------------------------------------------------------------------------
# Unit tests — get_summary_stats
# ---------------------------------------------------------------------------

class TestGetSummaryStats:
    def test_with_expenses(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        stats = get_summary_stats(user_id)
        assert stats["count"] == 8
        assert stats["total"] == f"{SEED_TOTAL:,.2f}"
        assert stats["top_category"] == "Bills"

    def test_no_expenses_returns_zeros(self, db_with_user, monkeypatch):
        conn, _ = db_with_user
        _patch(monkeypatch, conn)
        stats = get_summary_stats(99999)
        assert stats == {"total": "0.00", "count": 0, "top_category": "—"}

    def test_date_filter_narrows_results(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        # Only the Jun 2 electricity bill falls before Jun 5
        stats = get_summary_stats(user_id, date_from="2026-06-01", date_to="2026-06-02")
        assert stats["count"] == 1
        assert stats["total"] == "4,500.00"
        assert stats["top_category"] == "Bills"


# ---------------------------------------------------------------------------
# Unit tests — get_recent_transactions
# ---------------------------------------------------------------------------

class TestGetRecentTransactions:
    def test_with_expenses_ordered_newest_first(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        txns = get_recent_transactions(user_id)
        assert len(txns) == 8
        assert txns[0]["date"] == "27 Jun 2026"   # newest
        assert txns[-1]["date"] == "02 Jun 2026"  # oldest

    def test_each_item_has_required_keys(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        txns = get_recent_transactions(user_id)
        for tx in txns:
            assert set(tx.keys()) >= {"id", "date", "description", "category", "amount"}

    def test_amount_formatted_correctly(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        txns = get_recent_transactions(user_id)
        bills_tx = next(t for t in txns if t["category"] == "Bills")
        assert bills_tx["amount"] == "4,500.00"

    def test_no_expenses_returns_empty_list(self, db_with_user, monkeypatch):
        conn, _ = db_with_user
        _patch(monkeypatch, conn)
        assert get_recent_transactions(99999) == []

    def test_date_filter(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        txns = get_recent_transactions(user_id, date_from="2026-06-19", date_to="2026-06-27")
        assert len(txns) == 3  # Shopping (19), Food/Dinner (23), Other/Misc (27)


# ---------------------------------------------------------------------------
# Unit tests — get_category_breakdown
# ---------------------------------------------------------------------------

class TestGetCategoryBreakdown:
    def test_with_expenses_ordered_by_amount_desc(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        cats = get_category_breakdown(user_id)
        assert len(cats) == 7
        assert cats[0]["name"] == "Bills"
        assert cats[0]["amount"] == "4,500.00"

    def test_percents_sum_to_100(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        cats = get_category_breakdown(user_id)
        assert sum(c["percent"] for c in cats) == 100

    def test_percent_values_are_integers(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        for cat in get_category_breakdown(user_id):
            assert isinstance(cat["percent"], int)

    def test_no_expenses_returns_empty_list(self, db_with_user, monkeypatch):
        conn, _ = db_with_user
        _patch(monkeypatch, conn)
        assert get_category_breakdown(99999) == []

    def test_each_item_has_required_keys(self, db_with_user, monkeypatch):
        conn, user_id = db_with_user
        _patch(monkeypatch, conn)
        for cat in get_category_breakdown(user_id):
            assert set(cat.keys()) >= {"name", "amount", "percent"}


# ---------------------------------------------------------------------------
# Route tests — GET /profile
# ---------------------------------------------------------------------------

class TestProfileRoute:
    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def _login_as_seed_user(self, client):
        """Set session to the demo seed user (demo@spendly.com)."""
        from database.db import get_db
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT id, name FROM users WHERE email = ?", ("demo@spendly.com",)
            ).fetchone()
        finally:
            conn.close()
        with client.session_transaction() as sess:
            sess["user_id"] = row["id"]
            sess["user_name"] = row["name"]

    def test_authenticated_returns_200(self, client):
        self._login_as_seed_user(client)
        resp = client.get("/profile")
        assert resp.status_code == 200

    def test_shows_seed_user_name_and_email(self, client):
        self._login_as_seed_user(client)
        body = client.get("/profile").data.decode()
        assert "Demo User" in body
        assert "demo@spendly.com" in body

    def test_shows_rupee_symbol(self, client):
        self._login_as_seed_user(client)
        body = client.get("/profile").data.decode()
        assert "₹" in body

    def test_transaction_count_is_8(self, client):
        self._login_as_seed_user(client)
        body = client.get("/profile").data.decode()
        # The stat card shows the count as a bare number
        assert ">8<" in body

    def test_top_category_is_bills(self, client):
        self._login_as_seed_user(client)
        body = client.get("/profile").data.decode()
        assert "Bills" in body

    def test_invalid_date_param_does_not_crash(self, client):
        self._login_as_seed_user(client)
        resp = client.get("/profile?date_from=not-a-date&date_to=abc")
        assert resp.status_code == 200
