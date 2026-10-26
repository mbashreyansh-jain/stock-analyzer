# Run Stock AI on your PC

At the end of this guide, Stock AI runs on this PC at **http://localhost:8000**. You sign in as the **admin** and can invite friends. About 30 minutes.

You'll install one program (PostgreSQL) and paste a few commands. Every command is in a grey box. Copy it exactly, paste it, press **Enter**.

> The website code, the Python environment and all the pages are already set up in this folder. You only need the database and your settings.

---

## Part 1. Install PostgreSQL (the database)

1. Open Chrome or Edge and go to **https://www.postgresql.org/download/windows/**
2. Click **Download the installer**. This opens the EDB website.
3. Find the row for **PostgreSQL 17** (the newest 17.x). In the **Windows x86-64** column, click the **download icon**.
   A file named like `postgresql-17.x-windows-x64.exe` downloads (about 350 MB).
4. Open the downloaded file. If Windows asks **"Do you want to allow this app to make changes?"**, click **Yes**.
5. Go through the setup wizard:
   | Screen | What to do |
   |---|---|
   | Setup – PostgreSQL | Click **Next** |
   | Installation Directory | Leave it as is. Click **Next** |
   | Select Components | Keep **PostgreSQL Server**, **pgAdmin 4** and **Command Line Tools** ticked. **Untick Stack Builder**. Click **Next** |
   | Data Directory | Leave it as is. Click **Next** |
   | Password | Type a password **twice**. This is the database's master password (user `postgres`), not your Stock AI login. **Write it down.** Click **Next** |
   | Port | Leave **5432**. Click **Next** |
   | Advanced Options | Leave **[Default locale]**. Click **Next** |
   | Pre Installation Summary | Click **Next** |
   | Ready to Install | Click **Next** and wait 2 to 5 minutes |
   | Completing the Setup | If you see "Launch Stack Builder at exit", **untick it**. Click **Finish** |

PostgreSQL now runs in the background every time Windows starts.

---

## Part 2. Create the Stock AI database

1. Press the **Windows key**, type **SQL Shell**, and open **SQL Shell (psql)**.
2. It asks five questions. Press **Enter** for the first four (they show the right answers in brackets):
   ```
   Server [localhost]:            ← Enter
   Database [postgres]:           ← Enter
   Port [5432]:                   ← Enter
   Username [postgres]:           ← Enter
   Password for user postgres:    ← type the master password from Part 1, then Enter
   ```
   Nothing appears while you type the password. That's normal.
3. When you see `postgres=#`, paste these lines **one at a time**, pressing Enter after each.
   First choose a **new password for the app** and put it where it says `CHOOSE-A-PASSWORD`. Use letters and numbers only: no spaces, and none of `@ : / ' "`.
   ```sql
   CREATE USER stockai WITH PASSWORD 'CHOOSE-A-PASSWORD';
   ```
   ```sql
   CREATE DATABASE stockai OWNER stockai;
   ```
   ```sql
   CREATE DATABASE stockai_test OWNER stockai;
   ```
   You should see `CREATE ROLE`, then `CREATE DATABASE` twice. (`stockai_test` is a spare database the automatic checks use. Never put real data in it: the checks wipe it.)
4. Type `\q` and press **Enter** to close the window.

---

## Part 3. Put your settings in the `.env` file

1. Open **File Explorer** and go to `C:\Users\Shreyansh\Downloads\Stock Analyzer\stcok`.
2. If you can't see files starting with a dot: click **View** → **Show** → tick **Hidden items** and **File name extensions**.
3. Right-click **`.env.example`** → **Open with** → **Notepad**. Press **Ctrl+A**, then **Ctrl+C**, and close it.
4. Right-click **`.env`** → **Open with** → **Notepad**. (If there's no `.env`, right-click an empty space → **New** → **Text Document**, name it `.env` exactly, and click **Yes** when Windows asks about the extension.)
5. Press **Ctrl+A**, then **Ctrl+V**. The old Mac settings are replaced with the new template.
6. Change these lines:
   - `DATABASE_URL=postgresql://stockai:CHANGE-ME@localhost:5432/stockai`: replace `CHANGE-ME` with the **app password from Part 2**.
   - `GEMINI_API_KEY=`: paste your Gemini key straight after the `=` (no spaces). Leave it empty to skip AI for now.
7. Press **Ctrl+S** to save and close Notepad.

> `.env` holds your passwords and keys. It is never uploaded anywhere and never shared. Don't send it to anyone.

---

## Part 4. Open PowerShell in the project folder

1. Press the **Windows key**, type **PowerShell**, and open **Windows PowerShell**.
2. Paste this and press Enter:
   ```powershell
   cd "C:\Users\Shreyansh\Downloads\Stock Analyzer\stcok"
   ```
3. Check the program is installed (it already is on this PC):
   ```powershell
   .\.venv\Scripts\stockai.exe --help
   ```
   You should see a list of commands. If you see "not recognized", go to **Troubleshooting** at the end.

---

## Part 5. Create the tables, your admin account and the sample posts

Run these in the same PowerShell window, one at a time.

1. **Create the database tables:**
   ```powershell
   .\.venv\Scripts\stockai.exe migrate
   ```
   Expected: `Applied: 0001_core, 0002_corporate_actions, 0003_users_auth, 0004_blog`

2. **Create your admin account.** Put in your own email and name:
   ```powershell
   .\.venv\Scripts\stockai.exe create-admin --email "you@example.com" --name "Shreyansh"
   ```
   It asks for a password twice (typing is hidden). **This is your Stock AI sign-in password**: at least 10 characters. A short sentence works well.
   Expected: `Admin account created for you@example.com.`

3. **Add the 5 sample blog posts:**
   ```powershell
   .\.venv\Scripts\stockai.exe seed-blog
   ```
   Expected: `Sample blog posts added: 5`

---

## Part 6. Start Stock AI

1. In PowerShell:
   ```powershell
   .\.venv\Scripts\stockai.exe serve
   ```
   Expected: `Stock AI is starting. Open http://localhost:8000 in your browser.`
   **Leave this window open.** Stock AI runs while it's open. To stop it, click in the window and press **Ctrl+C**.
2. Open Chrome or Edge and go to **http://localhost:8000**
3. Sign in with the email and password from Part 5.

You'll land on ACME's Overview. Every tab, Daily picks and Portfolio work exactly like the approved designs. Your name is at the top right: click it for **Admin**, **Change password** and **Sign out**.

---

## Part 7. Invite someone (and see what a reader sees)

1. Click your name (top right) → **Admin: people and invites**.
2. Type their email, keep **Member**, and click **Create invite link**.
3. Click **Copy link** and send it to them yourself, for example on WhatsApp. It works once and expires in 7 days.

To see the member view yourself:

1. Open a private window: **Ctrl+Shift+N** in Chrome, or **Ctrl+Shift+P** in Edge.
2. Paste the link, set a name and password, and look around.
3. On the **Blog** tab a member sees only the published posts. There's no draft and no Publish button, and the server refuses blog changes from members even if someone tries.

> Right now the link only works **on this PC**. To let someone on the **same Wi-Fi** in, do Part 8. For friends anywhere, the next step is the cloud server.

---

## Part 8 (optional). Let others on the same Wi-Fi use it

1. Find this PC's address. In PowerShell, run `ipconfig` and look for **IPv4 Address** under your Wi-Fi or Ethernet adapter, for example `192.168.1.23`.
2. Open `.env` in Notepad and change `STOCKAI_PUBLIC_URL=http://localhost:8000` to `STOCKAI_PUBLIC_URL=http://192.168.1.23:8000` (your address). Save. Invite links will now use this address.
3. Stop the server (**Ctrl+C**) and start it in Wi-Fi mode:
   ```powershell
   .\.venv\Scripts\stockai.exe serve --lan
   ```
4. If Windows Firewall asks about Python, tick **Private networks** only (not Public) and click **Allow access**.
5. On their phone or laptop, on the same Wi-Fi, open `http://192.168.1.23:8000`.

> Don't open ports on your home router to put this PC on the internet. It has no padlock (HTTPS) and isn't built for that. The cloud server is the safe way to reach friends outside your home.

---

## Every day after this

After a restart, open PowerShell and run:
```powershell
cd "C:\Users\Shreyansh\Downloads\Stock Analyzer\stcok"
```
```powershell
.\.venv\Scripts\stockai.exe serve
```
Then open http://localhost:8000.

---

## Optional: run the full automatic checks

These sign in, send invites and try to publish as a member, using the spare `stockai_test` database (everything in it is wiped first). Put your app password in place of `CHOOSE-A-PASSWORD`:
```powershell
$env:STOCKAI_TEST_DATABASE_URL = "postgresql://stockai:CHOOSE-A-PASSWORD@localhost:5432/stockai_test"
```
```powershell
cd services\engine; ..\..\.venv\Scripts\python.exe -m pytest -q; cd ..\..
```
Expected: `56 passed`.

---

## Troubleshooting

| You see | Fix |
|---|---|
| `password authentication failed for user "stockai"` | The password in `DATABASE_URL` in `.env` doesn't match the one from Part 2. Fix `.env`, save, run the command again. |
| `connection refused` or `could not connect to server` | PostgreSQL isn't running. Windows key → type **Services** → find **postgresql-x64-17** → right-click → **Start**. |
| `stockai.exe is not recognized` | You're in the wrong folder. Run the `cd` line from Part 4 first. If it's still missing, run `python -m venv .venv` and then `.\.venv\Scripts\python.exe -m pip install -e .\services\engine`. |
| `[Errno 10048] ... only one usage of each socket address` | Something else uses port 8000. Run `.\.venv\Scripts\stockai.exe serve --port 8001` and open http://localhost:8001. |
| `Too many attempts. Wait 15 minutes` | 5 wrong passwords in a row. Wait, or reset it with the next row. |
| You forgot your admin password | `.\.venv\Scripts\stockai.exe set-password --email "you@example.com"` (asks for a new one). |
| A member forgot their password | Admin page → **Password reset link** next to their name → send them the link. |
| "Rewrite with AI" says it isn't available | No Gemini key, or a wrong one, in `.env`. Fix it, then stop (**Ctrl+C**) and start the server again. |
| `Gemini has no model called ...` | Google renamed its models. In `.env`, set `GEMINI_MODEL=` to a current "Flash" model name from aistudio.google.com, then restart. |
| Pages look plain, without the usual fonts | Fonts and chart libraries load from the internet. Check your connection. |

---

## What's in the project

Everything lives in `C:\Users\Shreyansh\Downloads\Stock Analyzer\stcok`.

### Frontend: what you see in the browser (`apps/web`)
| File | What it is |
|---|---|
| `apps/web/pages/overview-tab.html` … `portfolio.html` | The **10 approved pages, byte-for-byte copies** of `design/*.html`: Overview, Fundamentals, Technicals, AI Verdict, Time Machine, Sector, News, Blog, Daily picks, Portfolio |
| `apps/web/pages/watchlist.html` | A "coming next" placeholder (Watchlist isn't designed yet) |
| `apps/web/static/claude-shim.js` | Connects the pages to the server: downloads, who's signed in, blog posts, Rewrite with AI |
| `apps/web/static/app.js` | Makes the tabs real links, adds the account menu, and shows readers the blog's published posts only |
| `apps/web/static/login.html`, `invite.html`, `admin.html`, `auth.css` | Sign-in, invite/reset and admin pages, in the same style |
| `apps/web/sample/blog-seeds.json` | The 5 sample blog posts |

### Backend: the server (`services/engine/src/stockai`)
| File | What it does |
|---|---|
| `web/app.py` | Builds the website: security headers, friendly error pages |
| `web/routes_pages.py` | Serves the pages. Sends signed-out people to sign in; admin page for the admin only |
| `web/routes_auth.py` | Sign in and out, "who am I", change password, accept invite and reset links |
| `web/routes_admin.py` | Admin only: people, invite links, reset links, switch accounts off and on, roles |
| `web/routes_blog.py` | Blog: signed-in people read; **only the admin can publish or unpublish** |
| `web/routes_ai.py`, `web/gemini.py` | Rewrite with AI through your Gemini key (admin only; the key stays on the server) |
| `web/deps.py` | Database connection, who's signed in, the security check on every change |
| `web/security.py` | Password scrambling (Argon2id), sign-in tokens, password rules |
| `cli.py` | The `stockai` commands: `migrate`, `create-admin`, `set-password`, `seed-blog`, `serve`, plus the NSE data commands |
| `config.py` | Reads your settings from `.env` |
| `data/`, `ingest/`, `prices/`, `api/main.py` | The NSE data engine from the Mac (downloads, split adjustments, quality checks). Not wired into the pages yet |

### Database: tables (`db/migrations`)
| File | Tables |
|---|---|
| `0001_core.sql`, `0002_corporate_actions.sql` | Stocks, daily prices, index data, corporate actions (uses TimescaleDB if installed, plain PostgreSQL otherwise) |
| `0003_users_auth.sql` | `users`, `sessions`, `invites`, `login_attempts`, `audit_log` |
| `0004_blog.sql` | `blog_posts` |

### Settings and checks
| File | What it is |
|---|---|
| `.env` | **Your** settings and secrets (database password, Gemini key). Never shared |
| `.env.example` | The template for `.env` |
| `services/engine/tests/test_web.py` | 50 automatic checks that run without a database |
| `services/engine/tests/test_web_db.py` | 6 checks for sign-in, invites and blog rules against the test database |

### Same as the prototypes, and what's different
- **Identical:** every page's layout, colours, charts, Simple/Pro, and all the sample numbers.
- **Different:**
  - The tabs are real links.
  - Six older pages also show the Time Machine and Blog tabs.
  - There's an account menu at the top right.
  - Blog posts are saved in your database.
  - Downloads save straight to your computer.
  - "Rewrite with AI" uses Gemini.
- **Still sample data:** the numbers are ACME's made-up figures until the real data step (NSE prices every evening, INDmoney live prices).
- **Still saved in the browser only:** paper trades, starred stocks and your Simple/Pro choice, as in the prototypes. Moving these to your account (so they follow you between devices) is a later step.
