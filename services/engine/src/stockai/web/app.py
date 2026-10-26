"""The website. Run with `stockai serve` (or `uvicorn stockai.web.app:app`)."""

import html

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from stockai.config import get_settings
from stockai.web import routes_admin, routes_ai, routes_auth, routes_blog, routes_pages

# The pages load fonts from Google and two chart/PDF libraries from public CDNs, and use inline scripts and styles.
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
])

ERROR_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#F6F5FC;color:#1C1838;
font:16px/1.5 "Segoe UI",system-ui,sans-serif}}main{{background:#fff;border-radius:20px;padding:32px;max-width:420px;
box-shadow:0 8px 24px -16px rgba(40,30,90,.3);text-align:center}}h1{{font-size:1.4em;margin:0 0 8px}}
a{{color:#5636D3;font-weight:700}}</style></head>
<body><main><h1>{title}</h1><p>{message}</p><p><a href="/">Go to Stock AI</a></p></main></body></html>"""
ERROR_TITLES = {401: "Please sign in", 403: "Not allowed", 404: "Not found"}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Stock AI", version="0.2.0", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if settings.cookie_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        # API calls get JSON; people opening a page get a friendly page.
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        title = ERROR_TITLES.get(exc.status_code, "Something went wrong")
        message = exc.detail if isinstance(exc.detail, str) else "Please try again."
        return HTMLResponse(ERROR_PAGE.format(title=title, message=html.escape(message)), status_code=exc.status_code)

    for module in (routes_auth, routes_admin, routes_blog, routes_ai, routes_pages):
        app.include_router(module.router)
    app.mount("/static", StaticFiles(directory=settings.web_dir / "static"), name="static")
    return app


app = create_app()
