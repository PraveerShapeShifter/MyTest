# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

This is **Spendly** — a personal expense tracker — built as a Flask + SQLite learning scaffold. The codebase is intentionally incomplete: routes and the database module are stubbed out as numbered "Steps" for students to implement. When asked to add functionality, expect to be filling in these gaps rather than refactoring finished code.

Currency convention throughout the UI is INR (₹). Templates address a user named "Nitish Kumar" in placeholders — that's example copy, not a hardcoded user.

## Commands

```powershell
# Install dependencies (Windows / PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run the dev server — http://localhost:5001
python app.py

# Tests (pytest + pytest-flask are installed; no tests exist yet)
pytest
pytest path/to/test_file.py::test_name   # single test
```

The app runs on **port 5001**, not Flask's default 5000. Debug mode is on in `app.py`.

## Architecture

**Single-module Flask app** (`app.py`) — all routes live at the top level. Completed routes render Jinja2 templates; placeholder routes return plain strings tagged with the Step number that will implement them (e.g. `"Logout — coming in Step 3"`). When implementing a Step, replace the placeholder return with the real handler in-place; don't introduce blueprints unless the user asks.

**Templates** (`templates/`) extend `base.html`, which provides the navbar, footer, and links `static/css/style.css` + `static/js/main.js`. The brand mark is `◈` and the design system is already defined in `style.css` — reuse existing classes (`btn-primary`, `btn-ghost`, `auth-card`, `form-input`, `mock-card`, etc.) before inventing new ones.

**Database layer** (`database/db.py`) is a stub containing only docstring-style comments. The expected shape (per the comments) is three functions in this one file:
- `get_db()` — returns a SQLite connection with `row_factory` set and foreign keys enabled
- `init_db()` — `CREATE TABLE IF NOT EXISTS …` for all tables
- `seed_db()` — inserts development sample data

The SQLite file is `expense_tracker.db` at the repo root (gitignored). Keep the DB module flat — it's imported as `from database.db import …`.

**Step ordering** (from the placeholder strings in `app.py`): Step 1 = DB setup, Step 3 = logout, Step 4 = profile, Step 7 = add expense, Step 8 = edit expense, Step 9 = delete expense. Steps 2, 5, 6 aren't visible from the scaffold — infer them from context (likely register POST handler, login POST handler, expense list view).

## Conventions worth preserving

- Routes that aren't built yet stay as `return "X — coming in Step N"` strings until that Step is being implemented. Don't pre-stub them with `render_template` calls to templates that don't exist.
- New templates extend `base.html` and use `{{ url_for(...) }}` for all internal links (see existing templates).
- Forms POST to the same path they were rendered from (`/register`, `/login`); the route handler will branch on `request.method`.
