import calendar
import os
import sqlite3
from datetime import datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

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

    user_id = session["user_id"]

    # Validate optional date filter params — silently drop invalid YYYY-MM-DD values.
    date_from = request.args.get("date_from", "").strip()
    date_to   = request.args.get("date_to",   "").strip()

    def _valid_date(s):
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    if date_from and not _valid_date(date_from):
        date_from = ""
    if date_to and not _valid_date(date_to):
        date_to = ""

    # Compute preset ranges dynamically from today's date.
    today = datetime.today()
    year, month = today.year, today.month
    first_this = today.replace(day=1).strftime("%Y-%m-%d")
    last_this  = today.replace(day=calendar.monthrange(year, month)[1]).strftime("%Y-%m-%d")

    def _first_of_months_ago(n):
        m, y = month - n, year
        while m <= 0:
            m += 12
            y -= 1
        return datetime(y, m, 1).strftime("%Y-%m-%d")

    presets = {
        "this_month": {"date_from": first_this,              "date_to": last_this},
        "last_3":     {"date_from": _first_of_months_ago(2), "date_to": last_this},
        "last_6":     {"date_from": _first_of_months_ago(5), "date_to": last_this},
    }

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    df = date_from or None
    dt = date_to   or None

    stats      = get_summary_stats(user_id, df, dt)
    expenses   = get_recent_transactions(user_id, df, dt)
    categories = get_category_breakdown(user_id, df, dt)

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
