# Spec: Registration

## Overview
This step turns the `/register` route into a working account-creation
flow. Today the route only renders `register.html` on GET; this feature
adds POST handling so a visitor can submit the form, have their details
validated, and get a new row written to the `users` table with a securely
hashed password. It sits early in the Spendly roadmap (Step 02) because
every later feature — login, profile, and per-user expense tracking —
depends on real user accounts existing in the database. The matching
login flow is a separate later step; on success this step simply redirects
the new user to the login page.

## Depends on
- **Step 01 — Database setup** (complete): relies on `get_db()` and the
  `users` table (`name`, `email`, `password_hash`, with a `UNIQUE` email
  constraint) already implemented in `database/db.py`.

## Routes
- `GET /register` — render the registration form (already implemented; unchanged) — public
- `POST /register` — validate the submitted form, create the user, redirect to login — public

The existing `register()` handler in `app.py` is extended to branch on
`request.method` (`methods=["GET", "POST"]`), per the project convention
that forms POST to the same path they were rendered from.

## Database changes
No database changes. The `users` table from Step 01 already has every
column this feature needs (`name`, `email`, `password_hash`, `created_at`)
and enforces the `UNIQUE` email constraint relied on for duplicate
detection.

## Templates
- **Create:** none.
- **Modify:** none required. `templates/register.html` already POSTs to
  `/register`, renders an `{% if error %}` block via the `auth-error`
  class, and includes the `name`, `email`, and `password` fields. Only
  touch it if a validation message needs a field the form doesn't already
  expose.

## Files to change
- `app.py` — replace the GET-only `register()` stub with a `GET`/`POST`
  handler: validate input, insert the user via a parameterised query with
  a werkzeug-hashed password, handle duplicate-email `sqlite3.IntegrityError`,
  and redirect to `login` on success. Add the needed imports (`sqlite3`,
  and `redirect`, `request`, `url_for` from `flask`,
  `generate_password_hash` from `werkzeug.security`).

## Files to create
None.

## New dependencies
No new dependencies. `sqlite3` is in the standard library and `werkzeug`
ships with Flask.

## Rules for implementation
- No SQLAlchemy or ORMs — use the raw `sqlite3` connection from `get_db()`.
- Parameterised queries only — never string-format values into SQL.
- Passwords hashed with werkzeug (`generate_password_hash`); never store
  the plaintext password.
- Use CSS variables — never hardcode hex values (applies only if
  `register.html` / `style.css` are touched).
- All templates extend `base.html`.
- Branch on `request.method`; the form POSTs to the same `/register` path.
- Normalise email (trim + lowercase) and strip the name before insert so
  the `UNIQUE` email check is consistent.
- Catch `sqlite3.IntegrityError` and re-render the form with a friendly
  error rather than 500-ing.
- Close the connection in a `finally` block.
- On success, `redirect(url_for("login"))` — do not auto-login (that's a
  later step).

## Definition of done
- [ ] App starts with `python app.py` (port 5001) without errors.
- [ ] `GET /register` still renders the form unchanged.
- [ ] Submitting valid details creates exactly one new row in `users`
      and redirects to `/login`.
- [ ] The stored `password_hash` is a werkzeug hash, not the plaintext
      password (verify by inspecting the row).
- [ ] Submitting an email that already exists re-renders the form with a
      visible "already exists" error and creates no new row.
- [ ] Submitting an empty name, an email without `@`, or a password
      shorter than 8 characters re-renders the form with the relevant
      error and creates no new row.
- [ ] No raw f-strings / string concatenation appear in the SQL.
