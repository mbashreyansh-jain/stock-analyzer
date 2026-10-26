"""Admin only: people, invite links and password-reset links."""

from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from stockai.config import get_settings
from stockai.web.deps import CurrentUser, admin_writer, audit, get_conn, require_admin
from stockai.web.security import new_token, normalize_email, token_hash, valid_email

router = APIRouter(prefix="/api/admin")

INVITE_DAYS = 7
RESET_HOURS = 24


class InviteIn(BaseModel):
    email: str = Field(max_length=254)
    role: Literal["member", "admin"] = "member"


class ActiveIn(BaseModel):
    active: bool


class RoleIn(BaseModel):
    role: Literal["member", "admin"]


def _link(token: str) -> str:
    return f"{get_settings().public_url}/invite/{token}"


@router.get("/users")
def users(_: CurrentUser = Depends(require_admin), conn: psycopg.Connection = Depends(get_conn)) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, email, role, is_active, created_at, last_login_at FROM users ORDER BY created_at"
    ).fetchall()
    return [{"id": r[0], "name": r[1], "email": r[2], "role": r[3], "active": r[4],
             "created_at": r[5].isoformat(), "last_login_at": r[6].isoformat() if r[6] else None} for r in rows]


@router.get("/invites")
def invites(_: CurrentUser = Depends(require_admin), conn: psycopg.Connection = Depends(get_conn)) -> list[dict]:
    rows = conn.execute(
        "SELECT token_hash, kind, email, role, created_at, expires_at, used_at FROM invites"
        " WHERE used_at IS NOT NULL OR expires_at > now() ORDER BY created_at DESC LIMIT 100"
    ).fetchall()
    return [{"id": r[0], "kind": r[1], "email": r[2], "role": r[3], "created_at": r[4].isoformat(),
             "expires_at": r[5].isoformat(), "used_at": r[6].isoformat() if r[6] else None} for r in rows]


@router.post("/invites")
def create_invite(body: InviteIn, user: CurrentUser = Depends(admin_writer),
                  conn: psycopg.Connection = Depends(get_conn)) -> dict:
    email = normalize_email(body.email)
    if not valid_email(email):
        raise HTTPException(status_code=400, detail="That doesn't look like an email address.")
    if conn.execute("SELECT 1 FROM users WHERE lower(email) = %s", (email,)).fetchone():
        raise HTTPException(status_code=409, detail="This person already has an account.")
    token = new_token()
    expires = conn.execute(
        "INSERT INTO invites (token_hash, kind, email, role, created_by, expires_at)"
        " VALUES (%s, 'invite', %s, %s, %s, now() + make_interval(days => %s)) RETURNING expires_at",
        (token_hash(token), email, body.role, user.id, INVITE_DAYS),
    ).fetchone()[0]
    audit(conn, user.id, "admin.invite_created", email=email, role=body.role)
    conn.commit()
    # The link is shown once. Only its hash is stored, so it can't be recovered later.
    return {"link": _link(token), "email": email, "role": body.role, "expires_at": expires.isoformat()}


@router.delete("/invites/{invite_id}")
def revoke_invite(invite_id: str, user: CurrentUser = Depends(admin_writer),
                  conn: psycopg.Connection = Depends(get_conn)) -> dict:
    gone = conn.execute("DELETE FROM invites WHERE token_hash = %s AND used_at IS NULL RETURNING email",
                        (invite_id,)).fetchone()
    if not gone:
        raise HTTPException(status_code=404, detail="That link was already used or doesn't exist.")
    audit(conn, user.id, "admin.invite_revoked", email=gone[0])
    conn.commit()
    return {"ok": True}


@router.post("/users/{user_id}/reset-link")
def reset_link(user_id: int, user: CurrentUser = Depends(admin_writer),
               conn: psycopg.Connection = Depends(get_conn)) -> dict:
    row = conn.execute("SELECT email FROM users WHERE id = %s", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No such person.")
    token = new_token()
    conn.execute(
        "INSERT INTO invites (token_hash, kind, email, role, user_id, created_by, expires_at)"
        " VALUES (%s, 'reset', %s, 'member', %s, %s, now() + make_interval(hours => %s))",
        (token_hash(token), row[0], user_id, user.id, RESET_HOURS),
    )
    audit(conn, user.id, "admin.reset_link_created", target=user_id)
    conn.commit()
    return {"link": _link(token), "email": row[0], "expires_in_hours": RESET_HOURS}


@router.post("/users/{user_id}/active")
def set_active(user_id: int, body: ActiveIn, user: CurrentUser = Depends(admin_writer),
               conn: psycopg.Connection = Depends(get_conn)) -> dict:
    if user_id == user.id and not body.active:
        raise HTTPException(status_code=400, detail="You can't switch off your own account.")
    updated = conn.execute("UPDATE users SET is_active = %s WHERE id = %s RETURNING id", (body.active, user_id))
    if not updated.fetchone():
        raise HTTPException(status_code=404, detail="No such person.")
    if not body.active:
        conn.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
    audit(conn, user.id, "admin.user_active", target=user_id, active=body.active)
    conn.commit()
    return {"ok": True}


@router.post("/users/{user_id}/role")
def set_role(user_id: int, body: RoleIn, user: CurrentUser = Depends(admin_writer),
             conn: psycopg.Connection = Depends(get_conn)) -> dict:
    if user_id == user.id and body.role != "admin":
        raise HTTPException(status_code=400, detail="You can't remove your own admin role.")
    if not conn.execute("UPDATE users SET role = %s WHERE id = %s RETURNING id", (body.role, user_id)).fetchone():
        raise HTTPException(status_code=404, detail="No such person.")
    audit(conn, user.id, "admin.user_role", target=user_id, role=body.role)
    conn.commit()
    return {"ok": True}
