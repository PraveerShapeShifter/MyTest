# Spec: Login and Logout

## Overview
This step makes Spendly's authentication actually work. Today `/login` only
renders `login.html` on GET and `/logout` is a placeholder string. This
feature adds POST handling to `/login` so a registered user can submit their
email and password, be verified against the werkzeug hash stored in the
`users` table, and have a server-side session established. It also implements
`/logout` to clear that session. This introduces Flask's `session` to the app
for the first time (and the `app.secret_key` needed to sign it). It sits at
Step 03 because every logged-in feature that follows — the profile page
(Step 04) and per-user expense tracking (Steps 07–09) — depends on knowing
*which* user is signed in, which is exactly what the session stores.

## Depends on
- **Step 01 — Database setup** (complete): relies on `get_db()` and the
  `users` table (`email`, `password_hash`) in `database/db.py`.
- **Step 02 — Registration** (complete): users must be able to exist in the
  database before they can log in. The seed user (`demo@spendly.com` /
  `demo123`) also provides a known-good login for testing.

## Routes
- `GET /login` — render the sign-in form (already implemented; unchanged) — public
- `POST /login` — validate credentials, set the session, redirect on success — public
- `GET /logout` — clear the session and redirect to the login page — logged-in

The existing `login()` handler is extended to branch on `request.method`
(`methods=["GET", "POST"]`), per the project convention that forms POST to the
same path they were rendered from. `logout()` replaces its placeholder return.

## Database changes
No database changes. The `users` table from Step 01 already stores `email` and
the werkzeug `password_hash` this feature reads. No new columns are required —
the session lives server-side, not in the database.

## Templates
- **Create:** none.
- **Modify:**
  - `templates/login.html` — no structural change required; it already POSTs
    to `/login`, exposes `email` + `password`, and renders an `{% if error %}`
    block via the `auth-error` class. Touch it only if the error copy needs
    adjusting.
  - `templates/base.html` — make the navbar auth links conditional so a
    logged-in user sees a **Sign out** link (pointing at `url_for('logout')`)
    instead of "Sign in / Get started". This is the minimum needed to reach
    `/logout` through the UI; richer logged-in nav is Step 04's concern.

## Files to change
- `app.py`:
  - Set `app.secret_key` so `session` cookies can be signed (read from an env
    var such as `SECRET_KEY`, with a clearly-labelled dev fallback).
  - Add imports: `session` from `flask`; `check_password_hash` from
    `werkzeug.security`.
  - Extend `login()` to accept `GET`/`POST`: on POST, normalise the email
    (trim + lowercase), look the user up with a parameterised query, verify the
    password with `check_password_hash`, and on success store `user_id` (and
    `user_name`) in `session` and redirect. On failure re-render `login.html`
    with a single generic error.
  - Replace the `logout()` placeholder: clear the session
    (`session.clear()`) and `redirect(url_for("login"))`.
- `templates/base.html` — conditional auth links (see Templates).

## Files to create
None.

## New dependencies
No new dependencies. `check_password_hash` ships with werkzeug; `session` is
part of Flask.

## Rules for implementation
- No SQLAlchemy or ORMs — use the raw `sqlite3` connection from `get_db()`.
- Parameterised queries only — never string-format the email into SQL.
- Passwords verified with werkzeug (`check_password_hash`); never compare
  plaintext, never log the password.
- Use CSS variables — never hardcode hex values (applies only if `base.html` /
  `style.css` are touched).
- All templates extend `base.html`.
- Branch on `request.method`; the form POSTs to the same `/login` path.
- `app.secret_key` must be set before `session` is used; do not commit a real
  secret — use an env var with a dev-only fallback.
- Use a **single generic** error ("Invalid email or password.") for both
  unknown-email and wrong-password cases — do not reveal which one failed.
- Normalise the submitted email (trim + lowercase) so it matches the stored,
  normalised value from registration.
- Close the database connection in a `finally` block.
- On successful login, redirect (`redirect(url_for(...))`) rather than
  rendering, so a refresh doesn't re-POST.
- `logout()` clears the whole session and redirects; it must not error when no
  one is logged in.

## Definition of done
- [ ] App starts with `python app.py` (port 5001) without errors, with
      `app.secret_key` set.
- [ ] `GET /login` still renders the form unchanged.
- [ ] Logging in as the seed user (`demo@spendly.com` / `demo123`) succeeds,
      sets a session cookie, and redirects away from `/login`.
- [ ] A wrong password for a valid email re-renders `/login` with the generic
      "Invalid email or password." error and sets no session.
- [ ] An unknown email re-renders `/login` with the *same* generic error
      (no account-enumeration leak) and sets no session.
- [ ] Email matching ignores surrounding whitespace and case
      (`  DEMO@Spendly.com ` logs the seed user in).
- [ ] After login, `GET /logout` clears the session and redirects to `/login`;
      the navbar then shows "Sign in" again.
- [ ] Visiting `/logout` while not logged in redirects without error.
- [ ] No raw f-strings / string concatenation appear in the SQL, and the
      plaintext password is never stored or logged.
