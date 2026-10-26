"""Sign in, sign out, who am I, change password, and accepting invite or reset links."""

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from stockai.web.deps import (
    SESSION_COOKIE,
    CurrentUser,
    audit,
    client_ip,
    get_conn,
    require_user,
    start_session,
    user_writer,
)
from stockai.web.security import (
    dummy_hash,
    hash_password,
    needs_rehash,
    normalize_email,
    password_problem,
    token_hash,
    verify_password,
)

router = APIRouter(prefix="/api")

# Failed sign-ins allowed in 15 minutes before that email (or address) has to wait.
MAX_FAILS_PER_EMAIL = 5
MAX_FAILS_PER_IP = 30
LINK_GONE = "This link is not valid or has expired. Ask the admin for a new one."


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class PasswordIn(BaseModel):
    current: str = Field(max_length=200)
    new: str = Field(max_length=200)


class AcceptIn(BaseModel):
    name: str = Field(default="", max_length=60)
    password: str = Field(max_length=200)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    email, ip = normalize_email(body.email), client_ip(request)
    by_email, by_ip = conn.execute(
        "SELECT count(*) FILTER (WHERE lower(email) = %s), count(*) FILTER (WHERE ip = %s)"
        " FROM login_attempts WHERE at > now() - interval '15 minutes'",
        (email, ip),
    ).fetchone()
    if by_email >= MAX_FAILS_PER_EMAIL or by_ip >= MAX_FAILS_PER_IP:
        raise HTTPException(status_code=429, detail="Too many attempts. Wait 15 minutes and try again.")
    row = conn.execute("SELECT id, password_hash, is_active FROM users WHERE lower(email) = %s", (email,)).fetchone()
    matches = verify_password(row[1] if row else dummy_hash(), body.password)
    if not (row and matches and row[2]):
        conn.execute("INSERT INTO login_attempts (email, ip) VALUES (%s, %s)", (email, ip))
        conn.commit()
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    user_id = row[0]
    conn.execute("DELETE FROM login_attempts WHERE lower(email) = %s", (email,))
    if needs_rehash(row[1]):
        conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(body.password), user_id))
    csrf = start_session(conn, request, response, user_id)
    audit(conn, user_id, "auth.login", ip=ip)
    name, role = conn.execute("SELECT name, role FROM users WHERE id = %s", (user_id,)).fetchone()
    conn.commit()
    return {"user": {"id": user_id, "email": email, "name": name, "role": role}, "csrf": csrf}


@router.post("/auth/logout")
def logout(response: Response, user: CurrentUser = Depends(user_writer),
           conn: psycopg.Connection = Depends(get_conn)) -> dict:
    conn.execute("DELETE FROM sessions WHERE token_hash = %s", (user.session_hash,))
    audit(conn, user.id, "auth.logout")
    conn.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(user: CurrentUser = Depends(require_user)) -> dict:
    return {"user": user.public(), "csrf": user.csrf}


@router.post("/auth/password")
def change_password(body: PasswordIn, user: CurrentUser = Depends(user_writer),
                    conn: psycopg.Connection = Depends(get_conn)) -> dict:
    current_hash = conn.execute("SELECT password_hash FROM users WHERE id = %s", (user.id,)).fetchone()[0]
    if not verify_password(current_hash, body.current):
        raise HTTPException(status_code=400, detail="Your current password is not right.")
    problem = password_problem(body.new, user.email)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(body.new), user.id))
    # Sign out every other browser, keep this one.
    conn.execute("DELETE FROM sessions WHERE user_id = %s AND token_hash <> %s", (user.id, user.session_hash))
    audit(conn, user.id, "auth.password_changed")
    conn.commit()
    return {"ok": True}


def _open_link(conn: psycopg.Connection, token: str, lock: bool = False):
    row = conn.execute(
        "SELECT i.token_hash, i.kind, i.email, i.role, i.user_id, u.name FROM invites i"
        " LEFT JOIN users u ON u.id = i.user_id"
        " WHERE i.token_hash = %s AND i.used_at IS NULL AND i.expires_at > now()"
        + (" FOR UPDATE OF i" if lock else ""),
        (token_hash(token),),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=LINK_GONE)
    return row


@router.get("/invites/{token}")
def check_link(token: str, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    _, kind, email, role, _, name = _open_link(conn, token)
    return {"kind": kind, "email": email, "role": role, "name": name or ""}


@router.post("/invites/{token}/accept")
def accept_link(token: str, body: AcceptIn, request: Request, response: Response,
                conn: psycopg.Connection = Depends(get_conn)) -> dict:
    hashed, kind, email, role, user_id, name = _open_link(conn, token, lock=True)
    problem = password_problem(body.password, email)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    if kind == "invite":
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Enter your name.")
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = %s", (email.lower(),)).fetchone():
            raise HTTPException(status_code=409, detail="An account with this email already exists. Sign in instead.")
        user_id = conn.execute(
            "INSERT INTO users (email, name, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING id",
            (email, name, hash_password(body.password), role),
        ).fetchone()[0]
        audit(conn, user_id, "auth.joined", role=role)
    else:
        conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(body.password), user_id))
        conn.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
        audit(conn, user_id, "auth.password_reset")
    conn.execute("UPDATE invites SET used_at = now(), used_by = %s WHERE token_hash = %s", (user_id, hashed))
    csrf = start_session(conn, request, response, user_id)
    role = conn.execute("SELECT role FROM users WHERE id = %s", (user_id,)).fetchone()[0]
    conn.commit()
    return {"user": {"id": user_id, "email": email, "name": name, "role": role}, "csrf": csrf}
