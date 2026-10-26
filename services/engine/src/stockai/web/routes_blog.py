"""Blog posts: every signed-in person can read them, only the admin can publish or unpublish (D19, D23)."""

import json
import re
from datetime import UTC, datetime
from typing import Any

import psycopg
from fastapi import APIRouter, Body, Depends, HTTPException
from psycopg.types.json import Jsonb

from stockai.web.deps import CurrentUser, admin_writer, audit, get_conn, require_user

router = APIRouter(prefix="/api/blog")

_POST_ID = re.compile(r"^[A-Za-z0-9_.~:@+-]{1,120}$")
MAX_POST_BYTES = 256 * 1024


def _published_at(value: Any) -> datetime:
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return when if when.tzinfo else when.replace(tzinfo=UTC)
    except ValueError:
        return datetime.now(UTC)


def validate_post(post_id: str, post: dict) -> None:
    if not _POST_ID.match(post_id):
        raise HTTPException(status_code=400, detail="Invalid post id.")
    if len(json.dumps(post)) > MAX_POST_BYTES:
        raise HTTPException(status_code=413, detail="That post is too large.")
    if not isinstance(post.get("title"), str) or not post["title"].strip() or len(post["title"]) > 300:
        raise HTTPException(status_code=400, detail="A post needs a title.")
    if not isinstance(post.get("sections"), list) or not post["sections"] or len(post["sections"]) > 20:
        raise HTTPException(status_code=400, detail="A post needs between 1 and 20 sections.")
    if not isinstance(post.get("stock", ""), str) or len(post.get("stock", "")) > 12:
        raise HTTPException(status_code=400, detail="Invalid stock symbol.")


@router.get("/posts")
def list_posts(_: CurrentUser = Depends(require_user), conn: psycopg.Connection = Depends(get_conn)) -> list[dict]:
    rows = conn.execute("SELECT id, body FROM blog_posts ORDER BY published_at DESC LIMIT 300").fetchall()
    return [{"id": r[0], "data": r[1]} for r in rows]


@router.put("/posts/{post_id}")
def publish(post_id: str, post: dict = Body(...), user: CurrentUser = Depends(admin_writer),
            conn: psycopg.Connection = Depends(get_conn)) -> dict:
    validate_post(post_id, post)
    conn.execute(
        "INSERT INTO blog_posts (id, stock, published_at, body, author_id) VALUES (%s, %s, %s, %s, %s)"
        " ON CONFLICT (id) DO UPDATE SET stock = EXCLUDED.stock, published_at = EXCLUDED.published_at,"
        " body = EXCLUDED.body, updated_at = now()",
        (post_id, post.get("stock", "").upper(), _published_at(post.get("publishedAt")), Jsonb(post), user.id),
    )
    audit(conn, user.id, "blog.published", post=post_id, title=post["title"][:120])
    conn.commit()
    return {"ok": True, "id": post_id}


@router.delete("/posts/{post_id}")
def unpublish(post_id: str, user: CurrentUser = Depends(admin_writer),
              conn: psycopg.Connection = Depends(get_conn)) -> dict:
    if not conn.execute("DELETE FROM blog_posts WHERE id = %s RETURNING id", (post_id,)).fetchone():
        raise HTTPException(status_code=404, detail="No such post.")
    audit(conn, user.id, "blog.unpublished", post=post_id)
    conn.commit()
    return {"ok": True}
