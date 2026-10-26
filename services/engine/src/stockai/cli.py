"""Command line entry point: `uv run stockai <command>`. Run `uv run stockai --help` for the list."""

import argparse
from datetime import date

from stockai import db
from stockai.config import get_settings
from stockai.data.nse.client import NseClient
from stockai.ingest import pipeline


def _client() -> NseClient:
    s = get_settings()
    return NseClient(s.raw_dir / "nse", min_interval=s.nse_min_interval)


def _print_day(r: pipeline.DayResult) -> None:
    if r.status != "ok":
        print(f"{r.day}  {r.status}")
        return
    issues = " ".join(f"{k}={v}" for k, v in sorted(r.issues.items())) or "none"
    print(f"{r.day}  ok  prices={r.prices} delivery={r.delivery} indices={r.indices} "
          f"adjustments={r.adjustments} issues: {issues}", flush=True)


def cmd_migrate(args) -> None:
    with db.connect() as conn:
        applied = db.migrate(conn)
    print("Applied: " + ", ".join(applied) if applied else "Database already up to date.")


def cmd_universe(args) -> None:
    with db.connect() as conn:
        counts = pipeline.refresh_universe(conn, _client(), pipeline.today_ist())
    for name, n in counts.items():
        print(f"{name}: {n} members")


def cmd_ingest(args) -> None:
    day = args.date or pipeline.last_weekday(pipeline.today_ist())
    with db.connect() as conn:
        _print_day(pipeline.ingest_day(conn, _client(), day))


def cmd_backfill(args) -> None:
    end = args.end or pipeline.last_weekday(pipeline.today_ist())
    with db.connect() as conn:
        results = pipeline.backfill(conn, _client(), args.start, end, force=args.force, on_day=_print_day)
        events = pipeline.rebuild_adjustments(conn)
    ok = sum(r.status == "ok" for r in results)
    print(f"Done. {ok} trading days loaded, {len(results) - ok} skipped or failed. "
          f"{events} split/bonus adjustments on record.")


def cmd_rebuild_adjustments(args) -> None:
    with db.connect() as conn:
        print(f"{pipeline.rebuild_adjustments(conn)} adjustments on record.")


def cmd_status(args) -> None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT count(*), min(trade_date), max(trade_date) FROM ingest_runs"
            " WHERE dataset = 'bhavcopy' AND status = 'ok'"
        ).fetchone()
        print(f"Trading days loaded: {row[0]}  ({row[1]} to {row[2]})")
        n_inst, n_rows = conn.execute(
            "SELECT (SELECT count(*) FROM instruments), (SELECT count(*) FROM prices_daily)"
        ).fetchone()
        print(f"Stocks: {n_inst}   Price rows: {n_rows}")
        print(f"Split/bonus adjustments: {conn.execute('SELECT count(*) FROM price_adjustments').fetchone()[0]}")
        failed = conn.execute(
            "SELECT trade_date, message FROM ingest_runs WHERE status = 'error' ORDER BY trade_date"
        ).fetchall()
        for d, msg in failed:
            print(f"FAILED {d}: {msg}")
        latest = row[2]
        if latest:
            issues = conn.execute(
                "SELECT severity, check_name, count(*) FROM data_quality_issues WHERE trade_date = %s"
                " GROUP BY 1, 2 ORDER BY 1, 2",
                (latest,),
            ).fetchall()
            print(f"Quality checks for {latest}: " + (", ".join(f"{s}/{c}={n}" for s, c, n in issues) or "clean"))


def cmd_show(args) -> None:
    from stockai.prices import series

    with db.connect() as conn:
        df = series.load(conn, args.symbol, adjusted=not args.raw)
    print(df.tail(args.days).to_string(index=False))


def cmd_create_admin(args) -> None:
    import getpass

    from stockai.web.security import hash_password, normalize_email, password_problem, valid_email

    email = normalize_email(args.email)
    if not valid_email(email):
        raise SystemExit("That doesn't look like an email address.")
    password = getpass.getpass("Choose a password (typing is hidden): ")
    problem = password_problem(password, email)
    if problem:
        raise SystemExit(problem)
    if getpass.getpass("Type it again: ") != password:
        raise SystemExit("The passwords don't match. Nothing was saved.")
    with db.connect() as conn:
        if conn.execute("SELECT 1 FROM users WHERE lower(email) = %s", (email,)).fetchone():
            raise SystemExit("An account with that email already exists.")
        user_id = conn.execute(
            "INSERT INTO users (email, name, password_hash, role) VALUES (%s, %s, %s, 'admin') RETURNING id",
            (email, args.name.strip(), hash_password(password)),
        ).fetchone()[0]
        conn.execute("INSERT INTO audit_log (user_id, action) VALUES (%s, 'auth.admin_created')", (user_id,))
    print(f"Admin account created for {email}. Start the website with: stockai serve")


def cmd_set_password(args) -> None:
    """For when the admin forgets their own password (nobody else can send them a reset link)."""
    import getpass

    from stockai.web.security import hash_password, normalize_email, password_problem

    email = normalize_email(args.email)
    password = getpass.getpass(f"New password for {email} (typing is hidden): ")
    problem = password_problem(password, email)
    if problem:
        raise SystemExit(problem)
    if getpass.getpass("Type it again: ") != password:
        raise SystemExit("The passwords don't match. Nothing was changed.")
    with db.connect() as conn:
        row = conn.execute("UPDATE users SET password_hash = %s, is_active = true WHERE lower(email) = %s RETURNING id",
                           (hash_password(password), email)).fetchone()
        if not row:
            raise SystemExit("No account with that email.")
        conn.execute("DELETE FROM sessions WHERE user_id = %s", (row[0],))
        conn.execute("DELETE FROM login_attempts WHERE lower(email) = %s", (email,))
        conn.execute("INSERT INTO audit_log (user_id, action) VALUES (%s, 'auth.password_set_from_cli')", (row[0],))
    print(f"Password changed for {email}. Sign in again in the browser.")


def cmd_seed_blog(args) -> None:
    import json

    from psycopg.types.json import Jsonb

    from stockai.config import get_settings
    from stockai.web.routes_blog import _published_at

    posts = json.loads((get_settings().web_dir / "sample" / "blog-seeds.json").read_text(encoding="utf-8"))
    added = 0
    with db.connect() as conn:
        for post in posts:
            post_id = post.pop("id")
            added += conn.execute(
                "INSERT INTO blog_posts (id, stock, published_at, body) VALUES (%s, %s, %s, %s)"
                " ON CONFLICT (id) DO NOTHING RETURNING id",
                (post_id, post["stock"], _published_at(post["publishedAt"]), Jsonb(post)),
            ).fetchone() is not None
    print(f"Sample blog posts added: {added} (already there: {len(posts) - added}).")


def cmd_serve(args) -> None:
    import uvicorn

    host = "0.0.0.0" if args.lan else "127.0.0.1"
    print(f"Stock AI is starting. Open http://localhost:{args.port} in your browser. Press Ctrl+C to stop.")
    if args.lan:
        print("Others on the same Wi-Fi can use http://<this PC's IP address>:" + str(args.port))
    uvicorn.run("stockai.web.app:app", host=host, port=args.port, reload=args.reload, proxy_headers=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="stockai", description="Stock AI research engine")
    sub = parser.add_subparsers(required=True)

    sub.add_parser("migrate", help="Create or update database tables").set_defaults(func=cmd_migrate)
    sub.add_parser("universe", help="Download NIFTY 50 / Next 50 / 500 member lists").set_defaults(
        func=cmd_universe)

    p = sub.add_parser("ingest", help="Load one trading day (default: latest weekday)")
    p.add_argument("--date", type=date.fromisoformat)
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("backfill", help="Load every trading day in a date range")
    p.add_argument("--start", type=date.fromisoformat, required=True)
    p.add_argument("--end", type=date.fromisoformat)
    p.add_argument("--force", action="store_true", help="Reload days already loaded")
    p.set_defaults(func=cmd_backfill)

    sub.add_parser("rebuild-adjustments", help="Recompute split/bonus factors from history").set_defaults(
        func=cmd_rebuild_adjustments)
    sub.add_parser("status", help="Summary of what is loaded and any problems").set_defaults(func=cmd_status)

    p = sub.add_parser("show", help="Print recent prices for a stock")
    p.add_argument("symbol")
    p.add_argument("--days", type=int, default=10)
    p.add_argument("--raw", action="store_true", help="Show prices without split/bonus adjustment")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("create-admin", help="Create the admin account (asks for a password)")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_create_admin)

    p = sub.add_parser("set-password", help="Set a new password for an account (also unlocks it)")
    p.add_argument("--email", required=True)
    p.set_defaults(func=cmd_set_password)

    sub.add_parser("seed-blog", help="Add the sample blog posts").set_defaults(func=cmd_seed_blog)

    p = sub.add_parser("serve", help="Start the website on this computer")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--lan", action="store_true", help="Let other devices on the same Wi-Fi open it")
    p.add_argument("--reload", action="store_true", help="Restart automatically when code changes (development)")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
