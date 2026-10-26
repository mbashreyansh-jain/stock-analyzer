"""Request helpers: a database connection, who is signed in, and the checks every write must pass."""

import secrets
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg
from fastapi import Depends, HTTPException, Request, Response
from psycopg.types.json import Jsonb

from stockai import db
from stockai.config import get_settings
from stockai.web.security import new_token, token_hash

SESSION_COOKIE = "stockai_session"
CSRF_HEADER = "x-csrf-token"


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str
    name: str
    role: str
    csrf: str
    session_hash: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def public(self) -> dict:
        return {"id": self.id, "email": self.email, "name": self.name, "role": self.role}


def get_conn() -> Iterator[psycopg.Connection]:
    with db.connect() as conn:
        yield conn


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def optional_user(request: Request, conn: psycopg.Connection = Depends(get_conn)) -> CurrentUser | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    hashed = token_hash(token)
    row = conn.execute(
        "SELECT u.id, u.email, u.name, u.role, s.csrf_token, s.last_seen_at FROM sessions s"
        " JOIN users u ON u.id = s.user_id"
        " WHERE s.token_hash = %s AND s.expires_at > now() AND u.is_active",
        (hashed,),
    ).fetchone()
    if not row:
        return None
    if row[5] < datetime.now(UTC) - timedelta(minutes=10):
        conn.execute("UPDATE sessions SET last_seen_at = now() WHERE token_hash = %s", (hashed,))
        conn.commit()
    return CurrentUser(id=row[0], email=row[1], name=row[2], role=row[3], csrf=row[4], session_hash=hashed)


def require_user(user: CurrentUser | None = Depends(optional_user)) -> CurrentUser:
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user


def require_admin(user: CurrentUser = Depends(require_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only the admin can do this.")
    return user


def _check_csrf(request: Request, user: CurrentUser) -> None:
    # The session cookie alone is never enough to change anything: the page must also send the
    # token it got from /api/me, which another website cannot read.
    if not secrets.compare_digest(request.headers.get(CSRF_HEADER, ""), user.csrf):
        raise HTTPException(status_code=403, detail="Security check failed. Reload the page and try again.")


def user_writer(request: Request, user: CurrentUser = Depends(require_user)) -> CurrentUser:
    _check_csrf(request, user)
    return user


def admin_writer(request: Request, user: CurrentUser = Depends(require_admin)) -> CurrentUser:
    _check_csrf(request, user)
    return user


def start_session(conn: psycopg.Connection, request: Request, response: Response, user_id: int) -> str:
    """Create a signed-in session and set its cookie. Returns the CSRF token for the page."""
    s = get_settings()
    token, csrf = new_token(), new_token()
    conn.execute("DELETE FROM sessions WHERE user_id = %s AND expires_at < now()", (user_id,))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, csrf_token, expires_at, user_agent, ip)"
        " VALUES (%s, %s, %s, now() + make_interval(days => %s), %s, %s)",
        (token_hash(token), user_id, csrf, s.session_days, request.headers.get("user-agent", "")[:300],
         client_ip(request)),
    )
    conn.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (user_id,))
    response.set_cookie(SESSION_COOKIE, token, max_age=s.session_days * 86400, httponly=True,
                        secure=s.cookie_secure, samesite="lax", path="/")
    return csrf


def audit(conn: psycopg.Connection, user_id: int | None, action: str, **detail) -> None:
    conn.execute("INSERT INTO audit_log (user_id, action, detail) VALUES (%s, %s, %s)",
                 (user_id, action, Jsonb(detail)))
