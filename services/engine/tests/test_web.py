"""Website checks that need no database: passwords, page wrapping, sign-in redirects and who may write."""

import httpx
import pytest
from fastapi.testclient import TestClient

from stockai.config import get_settings
from stockai.web import gemini, security
from stockai.web.app import create_app
from stockai.web.deps import CurrentUser, get_conn, optional_user

MEMBER = CurrentUser(id=2, email="friend@example.com", name="Friend", role="member", csrf="m-csrf", session_hash="m")
ADMIN = CurrentUser(id=1, email="owner@example.com", name="Owner", role="admin", csrf="a-csrf", session_hash="a")
POST = {"title": "ACME hits a record high", "stock": "ACME", "publishedAt": "2026-10-24T10:00:00Z",
        "sections": [{"k": "bottom", "h": "The bottom line", "p": ["Signals lean bullish."]}]}


class FakeCursor:
    def fetchone(self):
        return None

    def fetchall(self):
        return []


class FakeConn:
    def __init__(self):
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append(sql)
        return FakeCursor()

    def commit(self):
        pass


def client_as(user):
    app = create_app()
    conn = FakeConn()
    app.dependency_overrides[optional_user] = lambda: user
    app.dependency_overrides[get_conn] = lambda: conn
    return TestClient(app), conn


# ---- passwords and tokens ----

def test_password_hash_round_trip():
    h = security.hash_password("a long enough password")
    assert h.startswith("$argon2id$")
    assert security.verify_password(h, "a long enough password")
    assert not security.verify_password(h, "a long enough passworD")
    assert not security.verify_password("not a hash", "anything")


def test_password_rules():
    assert security.password_problem("short") == "Use at least 10 characters."
    assert "email" in security.password_problem("me@example.com", "me@example.com")
    assert "common" in security.password_problem("password123")
    assert security.password_problem("tea on the terrace at four") is None


def test_tokens_are_random_and_hashed():
    a, b = security.new_token(), security.new_token()
    assert a != b and len(a) >= 40
    assert security.token_hash(a) == security.token_hash(a) != security.token_hash(b)
    assert len(security.token_hash(a)) == 64


def test_email_checks():
    assert security.normalize_email("  Me@Example.COM ") == "me@example.com"
    assert security.valid_email("me@example.com")
    assert not security.valid_email("not-an-email")


# ---- pages ----

def test_pages_need_sign_in():
    client, _ = client_as(None)
    r = client.get("/stocks/ACME/overview", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login?next=/stocks/ACME/overview"
    assert client.get("/", follow_redirects=False).headers["location"] == "/login"
    assert client.get("/portfolio", follow_redirects=False).headers["location"] == "/login?next=/portfolio"


def test_page_is_the_approved_file_unchanged():
    client, _ = client_as(MEMBER)
    r = client.get("/stocks/ACME/overview")
    assert r.status_code == 200
    original = (get_settings().web_dir / "pages" / "overview-tab.html").read_text(encoding="utf-8")
    body = r.text
    assert body.startswith("<!doctype html>")
    assert original in body
    assert body.index("/static/claude-shim.js") < body.index(original) < body.index("/static/app.js")
    assert r.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_every_tab_and_app_page_is_served():
    client, _ = client_as(MEMBER)
    for tab in ("overview", "fundamentals", "technicals", "ai-verdict", "time-machine", "sector", "news", "blog"):
        assert client.get(f"/stocks/ACME/{tab}").status_code == 200, tab
    for page in ("picks", "portfolio", "watchlist"):
        assert client.get(f"/{page}").status_code == 200, page
    assert client.get("/stocks/ACME/nope").status_code == 404


def test_admin_page_is_admin_only():
    client, _ = client_as(MEMBER)
    r = client.get("/admin")
    assert r.status_code == 403 and "Not allowed" in r.text
    client, _ = client_as(ADMIN)
    assert client.get("/admin").status_code == 200


# ---- the blog rule: everyone reads, only the admin writes ----

def test_member_can_read_posts():
    client, _ = client_as(MEMBER)
    r = client.get("/api/blog/posts")
    assert r.status_code == 200 and r.json() == []


def test_signed_out_cannot_read_posts():
    client, _ = client_as(None)
    r = client.get("/api/blog/posts")
    assert r.status_code == 401 and r.json() == {"detail": "Please sign in."}


@pytest.mark.parametrize("method", ["put", "delete"])
def test_member_cannot_publish_or_unpublish(method):
    client, conn = client_as(MEMBER)
    kwargs = {"json": POST} if method == "put" else {}
    r = getattr(client, method)("/api/blog/posts/acme-1", headers={"X-CSRF-Token": MEMBER.csrf}, **kwargs)
    assert r.status_code == 403 and r.json()["detail"] == "Only the admin can do this."
    assert conn.statements == []   # refused before touching the database


def test_admin_write_needs_the_csrf_token():
    client, conn = client_as(ADMIN)
    r = client.put("/api/blog/posts/acme-1", json=POST)
    assert r.status_code == 403 and "Security check" in r.json()["detail"]
    assert conn.statements == []


def test_admin_can_publish():
    client, conn = client_as(ADMIN)
    r = client.put("/api/blog/posts/acme-1", json=POST, headers={"X-CSRF-Token": ADMIN.csrf})
    assert r.status_code == 200 and r.json() == {"ok": True, "id": "acme-1"}
    assert any("INSERT INTO blog_posts" in s for s in conn.statements)
    assert any("INSERT INTO audit_log" in s for s in conn.statements)


def test_post_validation():
    client, _ = client_as(ADMIN)
    h = {"X-CSRF-Token": ADMIN.csrf}
    assert client.put("/api/blog/posts/bad id!", json=POST, headers=h).status_code == 400
    assert client.put("/api/blog/posts/x", json={**POST, "title": ""}, headers=h).status_code == 400
    assert client.put("/api/blog/posts/x", json={**POST, "sections": []}, headers=h).status_code == 400


def test_ai_and_admin_api_are_admin_only():
    client, _ = client_as(MEMBER)
    h = {"X-CSRF-Token": MEMBER.csrf}
    assert client.post("/api/ai/json", json={"prompt": "hi"}, headers=h).status_code == 403
    assert client.get("/api/admin/users").status_code == 403
    assert client.post("/api/admin/invites", json={"email": "x@example.com"}, headers=h).status_code == 403


# ---- Gemini ----

def _settings(key="k"):
    return get_settings().__class__(**{**get_settings().__dict__, "gemini_api_key": key, "gemini_model": "test-model"})


def test_gemini_parses_json_answer():
    def handler(request):
        assert request.headers["x-goog-api-key"] == "k" and "test-model" in str(request.url)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"title": "Hi"}'}]}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as c:
        assert gemini.generate_json("write", _settings(), c) == {"title": "Hi"}


@pytest.mark.parametrize("status,code", [(429, "rate_limited"), (403, "not_granted"), (500, "upstream_error")])
def test_gemini_errors_map_to_page_codes(status, code):
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, json={}))) as c:
        with pytest.raises(gemini.AIError) as err:
            gemini.generate_json("write", _settings(), c)
    assert err.value.code == code


def test_gemini_without_key_falls_back():
    with pytest.raises(gemini.AIError) as err:
        gemini.generate_json("write", _settings(key=""))
    assert err.value.code == "not_granted"
