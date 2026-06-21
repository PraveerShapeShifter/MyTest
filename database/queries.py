from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    member_since = ""
    if row["created_at"]:
        try:
            member_since = datetime.strptime(
                row["created_at"][:19], "%Y-%m-%d %H:%M:%S"
            ).strftime("%B %Y")
        except ValueError:
            member_since = ""

    initials = "".join(part[0] for part in row["name"].split()[:2]).upper() or "?"
    return {
        "name": row["name"],
        "email": row["email"],
        "initials": initials,
        "member_since": member_since,
    }


def get_summary_stats(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        base = "FROM expenses WHERE user_id = :user_id"
        params = {"user_id": user_id}
        if date_from:
            base += " AND date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            base += " AND date <= :date_to"
            params["date_to"] = date_to

        stats_row = conn.execute(
            "SELECT SUM(amount), COUNT(*) " + base, params
        ).fetchone()
        total_raw = stats_row[0] if stats_row[0] is not None else 0
        count = stats_row[1]

        top_row = conn.execute(
            "SELECT category, SUM(amount) as total " + base
            + " GROUP BY category ORDER BY total DESC LIMIT 1",
            params,
        ).fetchone()
        top_category = top_row["category"] if top_row else "—"
    finally:
        conn.close()

    return {
        "total": f"{total_raw:,.2f}",
        "count": count,
        "top_category": top_category,
    }


def get_recent_transactions(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        query = (
            "SELECT id, date, description, category, amount "
            "FROM expenses WHERE user_id = :user_id"
        )
        params = {"user_id": user_id}
        if date_from:
            query += " AND date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND date <= :date_to"
            params["date_to"] = date_to
        query += " ORDER BY date DESC"

        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": int(row["id"]),
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d %b %Y"),
            "description": row["description"] or "",
            "category": row["category"],
            "amount": f"{row['amount']:,.2f}",
        }
        for row in rows
    ]


def get_category_breakdown(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        query = (
            "SELECT category, SUM(amount) as total "
            "FROM expenses WHERE user_id = :user_id"
        )
        params = {"user_id": user_id}
        if date_from:
            query += " AND date >= :date_from"
            params["date_from"] = date_from
        if date_to:
            query += " AND date <= :date_to"
            params["date_to"] = date_to
        query += " GROUP BY category ORDER BY total DESC"

        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    raw_percents = [row["total"] / grand_total * 100 for row in rows]

    # Largest remainder method — ensures integer percents sum to exactly 100
    floored = [int(p) for p in raw_percents]
    slots = 100 - sum(floored)
    indices = sorted(
        range(len(raw_percents)),
        key=lambda i: raw_percents[i] - floored[i],
        reverse=True,
    )
    percents = floored[:]
    for i in range(slots):
        percents[indices[i]] += 1

    return [
        {
            "name": row["category"],
            "amount": f"{row['total']:,.2f}",
            "percent": pct,
        }
        for row, pct in zip(rows, percents)
    ]
