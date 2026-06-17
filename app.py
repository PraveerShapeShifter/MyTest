import os
import sqlite3
from datetime import datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
# Signs the session cookie. Use a real secret via the SECRET_KEY env var in
# production; the fallback below is for local development only.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key")


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name:
        return render_template("register.html", error="Please enter your name.")
    if "@" not in email:
        return render_template("register.html", error="Please enter a valid email address.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return render_template(
            "register.html",
            error="An account with that email already exists.",
        )
    finally:
        conn.close()

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded data for the UI design step — the real DB-backed values are
    # wired in a later step. The date filter is rendered but non-functional for
    # now: the params are echoed back so the controls keep their state, but the
    # data below does not change.
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    # Preset ranges for the filter bar (anchored to the current month for the
    # design; real ranges come with the DB step).
    presets = {
        "this_month": {"date_from": "2026-06-01", "date_to": "2026-06-30"},
        "last_3":     {"date_from": "2026-04-01", "date_to": "2026-06-30"},
        "last_6":     {"date_from": "2026-01-01", "date_to": "2026-06-30"},
    }

    # The identity card reflects the *real* logged-in user. (The spending
    # figures below are still placeholders until the DB step wires them up.)
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (session["user_id"],),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        # Stale session pointing at a user that no longer exists.
        session.clear()
        return redirect(url_for("login"))

    member_since = ""
    if row["created_at"]:
        try:
            member_since = datetime.strptime(
                row["created_at"][:19], "%Y-%m-%d %H:%M:%S"
            ).strftime("%B %Y")
        except ValueError:
            member_since = ""

    initials = "".join(part[0] for part in row["name"].split()[:2]).upper() or "?"

    user = {
        "name": row["name"],
        "email": row["email"],
        "initials": initials,
        "member_since": member_since,
    }
    stats = {
        "total": "8,209.50",
        "count": 8,
        "top_category": "Bills",
    }
    expenses = [
        {"id": 8, "date": "27 Jun 2026", "description": "Misc",                   "category": "Other",         "amount": "200.00"},
        {"id": 7, "date": "23 Jun 2026", "description": "Dinner out",             "category": "Food",          "amount": "410.00"},
        {"id": 6, "date": "19 Jun 2026", "description": "T-shirt",                "category": "Shopping",      "amount": "1,250.00"},
        {"id": 5, "date": "15 Jun 2026", "description": "Streaming subscription", "category": "Entertainment", "amount": "499.00"},
        {"id": 4, "date": "12 Jun 2026", "description": "Pharmacy",               "category": "Health",        "amount": "850.00"},
        {"id": 3, "date": "08 Jun 2026", "description": "Metro pass",             "category": "Transport",     "amount": "180.00"},
        {"id": 2, "date": "05 Jun 2026", "description": "Groceries",              "category": "Food",          "amount": "320.50"},
        {"id": 1, "date": "02 Jun 2026", "description": "Electricity bill",       "category": "Bills",         "amount": "4,500.00"},
    ]
    # `percent` is the category's share of total spend, used for the bar width.
    categories = [
        {"name": "Bills",         "amount": "4,500.00", "percent": 55},
        {"name": "Shopping",      "amount": "1,250.00", "percent": 15},
        {"name": "Health",        "amount": "850.00",   "percent": 10},
        {"name": "Food",          "amount": "730.50",   "percent": 9},
        {"name": "Entertainment", "amount": "499.00",   "percent": 6},
        {"name": "Other",         "amount": "200.00",   "percent": 2},
        {"name": "Transport",     "amount": "180.00",   "percent": 2},
    ]
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        expenses=expenses,
        categories=categories,
        presets=presets,
        date_from=date_from,
        date_to=date_to,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
