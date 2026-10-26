"""Sign-in, invites and the admin-only blog rule against a real PostgreSQL database.

Runs only when STOCKAI_TEST_DATABASE_URL points at a throwaway database. Everything in it is deleted first.
"""

import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from stockai import db
from stockai.web.app import create_app
from stockai.web.security import hash_password

TEST_URL = os.environ.get("STOCKAI_TEST_DATABASE_URL")
pytestmark = [pytest.mark.db, pytest.mark.skipif(not TEST_URL, reason="STOCKAI_TEST_DATABASE_URL not set")]

ADMIN_PW, MEMBER_PW = "admin password for tests", "member password for tests"
POST = {"title": "ACME hits a record high", "stock": "ACME", "publishedAt": "2026-10-24T10:00:00Z",
        "sections": [{"k": "bottom", "h": "The bottom line", "p": ["Signals lean bullish."]}]}


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_URL)
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    with db.connect() as conn:
        db.migrate(conn)
        conn.execute("INSERT INTO users (email, name, password_hash, role) VALUES (%s, %s, %s, 'admin')",
                     ("owner@example.com", "Owner", hash_password(ADMIN_PW)))
    return create_app()


def sign_in(app, email, password):
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    return c, r


def csrf(c):
    return {"X-CSRF-Token": c.get("/api/me").json()["csrf"]}


def invite_member(admin):
    link = admin.post("/api/admin/invites", json={"email": "Friend@Example.com"}, headers=csrf(admin)).json()["link"]
    return link.rsplit("/", 1)[1]


def test_sign_in_and_out(app):
    c, r = sign_in(app, "OWNER@example.com", ADMIN_PW)
    assert r.status_code == 200 and r.json()["user"]["role"] == "admin"
    assert "stockai_session" in c.cookies
    assert c.get("/api/me").json()["user"]["email"] == "owner@example.com"
    assert c.post("/api/auth/logout", headers=csrf(c)).status_code == 200
    assert c.get("/api/me").status_code == 401


def test_wrong_password_and_lockout(app):
    for _ in range(5):
        _, r = sign_in(app, "owner@example.com", "wrong password here")
        assert r.status_code == 401 and r.json()["detail"] == "Email or password is incorrect."
    _, r = sign_in(app, "owner@example.com", ADMIN_PW)
    assert r.status_code == 429   # even the right password waits after 5 failures


def test_invite_flow_and_blog_permissions(app):
    admin, _ = sign_in(app, "owner@example.com", ADMIN_PW)
    token = invite_member(admin)
    guest = TestClient(app)
    assert guest.get(f"/api/invites/{token}").json() == {"kind": "invite", "email": "friend@example.com",
                                                          "role": "member", "name": ""}
    assert guest.post(f"/api/invites/{token}/accept", json={"name": "Friend", "password": "short"}).status_code == 400
    r = guest.post(f"/api/invites/{token}/accept", json={"name": "Friend", "password": MEMBER_PW})
    assert r.status_code == 200 and r.json()["user"]["role"] == "member"
    assert TestClient(app).get(f"/api/invites/{token}").status_code == 404   # links work once

    member = guest
    assert member.put("/api/blog/posts/acme-1", json=POST, headers=csrf(member)).status_code == 403
    assert admin.put("/api/blog/posts/acme-1", json=POST, headers=csrf(admin)).status_code == 200
    posts = member.get("/api/blog/posts").json()
    assert [p["id"] for p in posts] == ["acme-1"] and posts[0]["data"]["title"] == POST["title"]
    assert member.delete("/api/blog/posts/acme-1", headers=csrf(member)).status_code == 403
    assert admin.delete("/api/blog/posts/acme-1", headers=csrf(admin)).status_code == 200
    assert member.get("/api/blog/posts").json() == []


def test_reset_link_and_switch_off(app):
    admin, _ = sign_in(app, "owner@example.com", ADMIN_PW)
    member = TestClient(app)
    member.post(f"/api/invites/{invite_member(admin)}/accept", json={"name": "Friend", "password": MEMBER_PW})
    friend_id = next(u["id"] for u in admin.get("/api/admin/users").json() if u["email"] == "friend@example.com")

    token = admin.post(f"/api/admin/users/{friend_id}/reset-link", headers=csrf(admin)).json()["link"].rsplit("/", 1)[1]
    assert TestClient(app).post(f"/api/invites/{token}/accept", json={"password": "a brand new password"}).status_code == 200
    assert member.get("/api/me").status_code == 401   # old sessions end after a reset
    _, r = sign_in(app, "friend@example.com", "a brand new password")
    assert r.status_code == 200

    again, _ = sign_in(app, "friend@example.com", "a brand new password")
    assert admin.post(f"/api/admin/users/{friend_id}/active", json={"active": False}, headers=csrf(admin)).status_code == 200
    assert again.get("/api/me").status_code == 401
    _, r = sign_in(app, "friend@example.com", "a brand new password")
    assert r.status_code == 401
