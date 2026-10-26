# Project map: what every folder and file is for

Each file has a tag:

- **USED**: the website or its setup needs it today.
- **LATER**: for a step that hasn't happened yet (real NSE data, cloud server).
- **MAC ONLY**: left from when the project ran on the Mac. Not used on Windows; safe to ignore.
- **REFERENCE**: for reading only, never run.

```
stockai\
├── apps\web\              FRONTEND: what you see in the browser
├── services\engine\       BACKEND: the server, sign-in, and the NSE data engine
├── db\migrations\         DATABASE: the tables, created by "stockai migrate"
├── design\                the approved prototypes (the originals of apps\web\pages)
├── docs\                  decisions and data sources
├── packages\ui\           colours and fonts kept as one file
├── .vscode\               VS Code settings for this project
├── .github\               automatic checks on GitHub
├── .venv\                 Python packages (you create it in step 3; not in the ZIP)
├── .env                   YOUR passwords and keys (you create it in step 5; never share it)
└── guides and settings files at the top (see the last section)
```

---

## 1. Frontend: `apps\web\`

What the browser shows. Served by the backend; never opened directly.

### `apps\web\pages\`: the screens you approved (USED)
Each file is a complete page: design (CSS), layout (HTML) and behaviour (JavaScript), with ACME's sample numbers built in. They are **byte-for-byte copies** of the files in `design\`. Don't edit or auto-format them.

| File | Screen | Opens at |
|---|---|---|
| `overview-tab.html` | Overview: verdict rings, your call vs AI, price ladder, key points | /stocks/ACME/overview |
| `fundamentals-tab.html` | Fundamentals: health score, ratios, fair value, shareholding | /stocks/ACME/fundamentals |
| `technicals-tab.html` | Technicals: TradingView charts, 60 indicators, candle patterns, drawing tools | /stocks/ACME/technicals |
| `ai-verdict-tab.html` | AI Verdict: the four pillars, market mood, bull/bear case, your view vs AI | /stocks/ACME/ai-verdict |
| `time-machine-tab.html` | Time Machine: 10,000 simulated futures for a trade, plus the look-back | /stocks/ACME/time-machine |
| `sector-tab.html` | Sector: industry strength, heatmap, rotation | /stocks/ACME/sector |
| `news-tab.html` | News: mood, filterable feed, effect on signals | /stocks/ACME/news |
| `blog-tab.html` | Blog: AI-written post, publish (admin only), published posts | /stocks/ACME/blog |
| `daily-picks.html` | Daily picks: today's ideas from the NIFTY 500 | /picks |
| `portfolio.html` | Portfolio: real holdings, health check, paper trading | /portfolio |
| `watchlist.html` | Placeholder: "Watchlist is coming next" (not designed yet) | /watchlist |

### `apps\web\static\`: files I wrote to connect the pages to the server (USED)
| File | What it does |
|---|---|
| `claude-shim.js` | **The connector.** Loads before each page. It gives the page downloads, who's signed in, the Blog's posts from the database, and "Rewrite with AI" through Gemini, so the page files didn't need editing. It also attaches the security token to every change. |
| `app.js` | Runs after each page. It makes the tabs real links (and adds Time Machine and Blog to older pages), adds your name menu at the top right, and on the Blog shows members the published posts only. |
| `login.html` | The sign-in page (/login) |
| `invite.html` | Where invite and password-reset links open: set name and password (/invite/…) |
| `admin.html` | Admin only (/admin): invite people, switch accounts off and on, reset links, roles |
| `auth.css` | The shared look for the sign-in, invite and admin pages |

### `apps\web\sample\` (USED once)
| File | What it is |
|---|---|
| `blog-seeds.json` | The 5 sample blog posts. `stockai seed-blog` copies them into the database. |

---

## 2. Backend: `services\engine\`

The Python program that runs the website and the NSE data engine.

| File | Tag | What it is |
|---|---|---|
| `pyproject.toml` | USED | The backend's "shopping list": its name, the packages it needs (FastAPI, PostgreSQL driver, Argon2…), and the `stockai` command. Step 3 installs from it. |
| `uv.lock` | MAC ONLY | Exact package versions for the `uv` installer used on the Mac. On Windows we install with pip instead. |

### `services\engine\src\stockai\`: the code

**Core**
| File | Tag | What it does |
|---|---|---|
| `__init__.py` | USED | Marks the folder as the `stockai` Python package (Python needs these; there's one in every code folder). |
| `cli.py` | USED | **The `stockai` command.** Every command you type lives here: `migrate`, `create-admin`, `set-password`, `seed-blog`, `serve`, plus the data commands `universe`, `ingest`, `backfill`, `rebuild-adjustments`, `status` and `show`. |
| `config.py` | USED | Reads your settings from `.env` (database address, Gemini key, website address…). |
| `db.py` | USED | Connects to PostgreSQL and applies the table files from `db\migrations` in order, remembering which are done. |

**`web\`: the website (USED)**
| File | What it does |
|---|---|
| `app.py` | **Builds the website.** Joins all the parts below, adds security headers to every response, and shows friendly error pages. |
| `routes_pages.py` | Serves the pages. Sends signed-out people to /login, and lets only the admin open /admin. Wraps each approved page with the two connector scripts. |
| `routes_auth.py` | **Sign-in:** sign in, sign out, "who am I", change password, accept invite and reset links. Locks sign-in for 15 minutes after 5 wrong passwords. |
| `routes_admin.py` | **Admin only:** list people, create and cancel invite links, password-reset links, switch accounts off and on, change roles. |
| `routes_blog.py` | **Blog:** every signed-in person can read; only the admin can publish or unpublish. The server enforces this, not just the buttons. |
| `routes_ai.py` | "Rewrite with AI": admin only, passes the request to Gemini. |
| `gemini.py` | Talks to Google Gemini with your key. The key never leaves the server. If Gemini fails, the page falls back to the free templates. |
| `deps.py` | Shared checks used on every request: open a database connection, work out who's signed in, and require the security token for any change. It also creates sessions and writes the audit log. |
| `security.py` | Password safety: scrambling (Argon2id), checking, password rules (10+ characters, not common), random sign-in tokens. |

**`data\nse\`: downloading NSE files (LATER, the real-data step)**
| File | What it does |
|---|---|
| `client.py` | A polite downloader for NSE's website: waits between requests and keeps a copy of every file so nothing downloads twice. |
| `bhavcopy.py` | Reads NSE's daily price file (open, high, low, close, volume for every stock). |
| `delivery.py` | Reads the delivery % file (shares actually taken home vs traded within the day). |
| `indices.py` | Reads index prices (NIFTY, sector indices, with P/E) and index member lists (NIFTY 50, 500). |
| `corporate_actions.py` | Reads NSE's splits, bonuses and demergers, so old prices can be adjusted. |

**`ingest\`: loading those files into the database (LATER)**
| File | What it does |
|---|---|
| `pipeline.py` | Runs one trading day (or a range): download → check → save. Used by `stockai ingest` and `backfill`. |
| `store.py` | Saves prices, index data and member lists into the tables. |
| `quality.py` | Daily sanity checks: impossible prices, missing stocks, suspicious 20%+ moves. |

**`prices\`: using the stored prices (LATER)**
| File | What it does |
|---|---|
| `adjustments.py` | Works out the split/bonus factors so a 1-for-5 split doesn't look like an 80% crash. |
| `series.py` | Loads a stock's price history, adjusted or raw. Used by `stockai show`. |

**`api\` (LATER)**
| File | What it does |
|---|---|
| `main.py` | The engine's first API (prices, stock list) from the Mac. Not part of the website yet; it will feed real data to the pages later. |

### `services\engine\tests\`: automatic checks (USED)
| File | What it checks |
|---|---|
| `test_web.py` | **The website, without a database (50 checks).** Passwords, sign-in redirects, pages served unchanged, members blocked from publishing, admin needs the security token, Gemini errors. |
| `test_web_db.py` | **The website with a real database.** Sign-in and lockout, invite links work once, member vs admin on the blog, reset links, switching accounts off. Needs `stockai_test`. |
| `test_bhavcopy.py`, `test_delivery_and_indices.py`, `test_corporate_actions.py` | Reading each NSE file type correctly. |
| `test_adjustments.py` | Split/bonus maths. |
| `test_quality.py` | The daily sanity checks. |
| `test_pipeline_db.py` | A full day's download-to-database run, against `stockai_test`. |

---

## 3. Database: `db\migrations\`

Each file creates tables. `stockai migrate` runs them in number order, once each. Never edit a file that has already run; add a new numbered file instead.

| File | Tag | Tables it creates |
|---|---|---|
| `0001_core.sql` | LATER | `instruments` (stocks), `index_members`, `prices_daily`, `index_daily`, `price_adjustments`, `ingest_runs`, `data_quality_issues`. Uses TimescaleDB if installed (cloud server), plain tables otherwise (your PC). |
| `0002_corporate_actions.sql` | LATER | `corporate_actions` (splits, bonuses), and rebuilds `price_adjustments` |
| `0003_users_auth.sql` | USED | `users` (name, email, scrambled password, admin/member), `sessions` (who's signed in), `invites` (invite and reset links), `login_attempts` (wrong passwords), `audit_log` (who did what) |
| `0004_blog.sql` | USED | `blog_posts` |

The database itself (the actual data) lives inside PostgreSQL on your PC, not in this folder.

---

## 4. Other folders

| Folder / file | Tag | What it is |
|---|---|---|
| `design\*.html` | REFERENCE | **The original approved prototypes.** `apps\web\pages` holds copies; if a page ever needs a design change, it starts here. |
| `design\fundamentals-styles.html` | REFERENCE | The three looks you compared on day one (you chose style C, "Friendly & bold"). |
| `design\fundamentals-tab-simple-for-everyone.html` | REFERENCE | A stricter Simple mode you tried and turned down; kept in case parts are useful. |
| `docs\decisions.md` | REFERENCE | **Every decision with its date and reason** (D1–D23): what each tab shows, the scoring rules, the website stack, sign-in. |
| `docs\data-sources.md` | REFERENCE | Every NSE address the engine downloads from, plus notes on INDmoney's API. |
| `packages\ui\tokens.css`, `packages\ui\package.json` | LATER | The colours and fonts as one shared file, for a future app. The current pages carry their own copy. |
| `.vscode\extensions.json` | USED | Makes VS Code offer the right extensions (Python, Ruff, PostgreSQL…). |
| `.vscode\settings.json` | USED | Points VS Code at `.venv`, sets up the Testing panel, and turns off auto-formatting for the approved pages. |
| `.vscode\launch.json` | USED | Lets **F5** start the server ("Stock AI server", or the Wi-Fi version). |
| `.github\workflows\ci.yml` | LATER | Runs the tests automatically on GitHub whenever code is uploaded, once the project is on GitHub. |

---

## 5. Files at the top of the project folder

| File | Tag | What it is |
|---|---|---|
| `.env` | USED, SECRET | **Your settings: the database password, Gemini key, website address.** You create it in step 5. Never share it; it's left out of every ZIP. |
| `.env.example` | USED | The template for `.env`, with an explanation of every setting. |
| `LOCAL-SERVER-SETUP.md` | USED | The click-by-click guide for running the website on your PC. |
| `PROJECT-MAP.md` | USED | This note. |
| `README.md` | REFERENCE | A short technical overview and quick start. |
| `START-HERE.md` | MAC ONLY | The plain-English guide from the Mac days (Docker, double-click scripts). The Windows guide replaces it. |
| `.gitignore` | USED | Tells Git which files never to save (`.env`, `.venv`, caches, downloaded data). |
| `docker-compose.yml` | MAC ONLY | Started the database inside Docker on the Mac. On Windows, PostgreSQL is installed directly. The cloud server may use Docker again. |
| `package.json`, `pnpm-workspace.yaml` | MAC ONLY | Shortcuts for Node.js tools on the Mac (start Docker, run the engine). Not needed now. |
| `Update Stock Data.command` | MAC ONLY | Double-click script on the Mac that downloaded the latest NSE prices. The Windows version comes with the real-data step. |
| `Check Stock Data.command` | MAC ONLY | Double-click script on the Mac that showed what data was loaded. |

### Created on your PC (not in the ZIP)
| Folder | What it is |
|---|---|
| `.venv\` | The Python packages for the backend (made in step 3). Delete it and redo step 3 if it ever breaks. |
| `data\` | Downloaded NSE files, once the real-data step starts. Safe to delete; it re-downloads. |
| `dist\` | ZIPs I make for you. |

---

## How the pieces connect

```
Browser (Chrome/Edge)
   │  opens http://localhost:8000/stocks/ACME/blog
   ▼
Backend: services\engine\src\stockai\web\
   │  routes_pages.py  → are you signed in?  no → /login (static\login.html)
   │                                        yes → send pages\blog-tab.html + claude-shim.js + app.js
   │  routes_blog.py   ← the page asks for posts / the admin publishes
   │  routes_auth.py   ← sign in, sign out, invite links
   ▼
Database: PostgreSQL on your PC (tables from db\migrations\)
   users · sessions · invites · blog_posts · audit_log …
```

The server reads its passwords and keys from `.env`, and you start it with `.venv\Scripts\stockai.exe serve`.
