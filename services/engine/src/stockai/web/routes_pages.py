"""Serves the approved pages exactly as designed, plus the sign-in, invite and admin pages.

The design pages in apps/web/pages are the same files as design/*.html. The server only wraps each one in the
standard HTML document shell and adds two scripts: claude-shim.js first (connects the page to this server) and
app.js last (links the tabs and adds the account menu). The page files themselves are never changed.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from stockai.config import get_settings
from stockai.web.deps import CurrentUser, optional_user

router = APIRouter()

STOCK_TABS = {
    "overview": "overview-tab.html", "fundamentals": "fundamentals-tab.html", "technicals": "technicals-tab.html",
    "ai-verdict": "ai-verdict-tab.html", "time-machine": "time-machine-tab.html", "sector": "sector-tab.html",
    "news": "news-tab.html", "blog": "blog-tab.html",
}
APP_PAGES = {"picks": "daily-picks.html", "portfolio": "portfolio.html", "watchlist": "watchlist.html"}
SAMPLE_STOCKS = {"ACME"}  # Until real data is connected, only the sample stock has pages.
HOME = "/stocks/ACME/overview"

SHELL_HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
              '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
              '<script src="/static/claude-shim.js?v={v}"></script></head><body>')
SHELL_TAIL = '<script src="/static/app.js?v={v}" defer></script></body></html>'
NO_STORE = {"Cache-Control": "no-store"}


def _read(path: Path) -> str:
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Page not found.")
    return path.read_text(encoding="utf-8")


def _script_version() -> int:
    """Changes whenever the two scripts change, so browsers never run an old copy after an update."""
    static = get_settings().web_dir / "static"
    return max(int((static / name).stat().st_mtime) for name in ("claude-shim.js", "app.js"))


def wrap(page_html: str) -> str:
    v = _script_version()
    return SHELL_HEAD.format(v=v) + page_html + SHELL_TAIL.format(v=v)


def _page(name: str) -> HTMLResponse:
    return HTMLResponse(wrap(_read(get_settings().web_dir / "pages" / name)), headers=NO_STORE)


def _standalone(name: str) -> HTMLResponse:
    return HTMLResponse(_read(get_settings().web_dir / "static" / name), headers=NO_STORE)


def _to_login(next_path: str) -> RedirectResponse:
    return RedirectResponse(f"/login?next={next_path}", status_code=303)


@router.get("/", include_in_schema=False)
def home(user: CurrentUser | None = Depends(optional_user)):
    return RedirectResponse(HOME if user else "/login", status_code=303)


@router.get("/stocks/{symbol}/{tab}", include_in_schema=False)
def stock_tab(symbol: str, tab: str, user: CurrentUser | None = Depends(optional_user)):
    if user is None:
        return _to_login(f"/stocks/{symbol}/{tab}")
    if symbol.upper() not in SAMPLE_STOCKS or tab not in STOCK_TABS:
        raise HTTPException(status_code=404, detail="Only the sample stock ACME has pages until real data arrives.")
    return _page(STOCK_TABS[tab])


@router.get("/stocks/{symbol}", include_in_schema=False)
def stock_home(symbol: str):
    return RedirectResponse(f"/stocks/{symbol}/overview", status_code=303)


def _app_route(slug: str):
    def handler(user: CurrentUser | None = Depends(optional_user)):
        if user is None:
            return _to_login(f"/{slug}")
        return _page(APP_PAGES[slug])
    handler.__name__ = f"page_{slug}"
    return handler


for _slug in APP_PAGES:
    router.add_api_route(f"/{_slug}", _app_route(_slug), methods=["GET"], include_in_schema=False)


@router.get("/login", include_in_schema=False)
def login_page(user: CurrentUser | None = Depends(optional_user)):
    if user is not None:
        return RedirectResponse(HOME, status_code=303)
    return _standalone("login.html")


@router.get("/invite/{token}", include_in_schema=False)
def invite_page(token: str):
    return _standalone("invite.html")


@router.get("/admin", include_in_schema=False)
def admin_page(user: CurrentUser | None = Depends(optional_user)):
    if user is None:
        return _to_login("/admin")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Only the admin can open this page.")
    return _standalone("admin.html")
