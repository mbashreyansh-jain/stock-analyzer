/* Runs after each approved page has drawn itself. It does not change the page's design. It only:
   1. turns the tab bars into working links (and adds the Time Machine and Blog tabs to pages designed
      before those tabs existed),
   2. adds an account menu to the top bar: other sections, Admin, change password, sign out,
   3. on the Blog page, shows readers the published posts only (writing is for the admin). */
(function () {
  "use strict";

  var SA = window.StockAI;
  if (!SA) return;

  var STOCK_TABS = [["Overview", "overview"], ["Fundamentals", "fundamentals"], ["Technicals", "technicals"],
    ["AI Verdict", "ai-verdict"], ["Time Machine", "time-machine"], ["Sector", "sector"], ["News", "news"], ["Blog", "blog"]];
  var APP_LINKS = { "Stocks": "/stocks/ACME/overview", "Daily picks": "/picks", "Watchlist": "/watchlist", "Portfolio": "/portfolio" };
  var path = window.location.pathname;
  var stockMatch = path.match(/^\/stocks\/([^/]+)\//);
  var symbol = stockMatch ? stockMatch[1] : "ACME";

  function linkify(el, href) {
    el.setAttribute("role", "link");
    el.setAttribute("tabindex", "0");
    el.style.cursor = "pointer";
    el.addEventListener("click", function () { window.location.href = href; });
    el.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); window.location.href = href; } });
  }

  // 1. Tabs
  var tabs = document.querySelector("nav.tabs");
  if (tabs) {
    var current = (tabs.querySelector("span.on") || {}).textContent;
    tabs.innerHTML = "";
    STOCK_TABS.forEach(function (t) {
      var s = document.createElement("span");
      s.textContent = t[0];
      if (t[0] === current) { s.className = "on"; s.setAttribute("aria-current", "page"); }
      else linkify(s, "/stocks/" + symbol + "/" + t[1]);
      tabs.appendChild(s);
    });
  }
  // The stock pages were designed without the app-level bar that Daily picks and Portfolio have.
  // Add the same bar above the stock name so every section is one click away.
  if (tabs && !document.querySelector("nav.apptabs")) {
    var bar = document.createElement("nav");
    bar.className = "apptabs sa-apptabs";
    bar.setAttribute("aria-label", "App sections");
    Object.keys(APP_LINKS).forEach(function (name) {
      var s = document.createElement("span");
      s.textContent = name;
      if (name === "Stocks") { s.className = "on"; s.setAttribute("aria-current", "page"); }
      bar.appendChild(s);
    });
    var head = document.querySelector(".page > .stock") || document.querySelector(".page > *");
    if (head && head.parentNode) head.parentNode.insertBefore(bar, head);
  }
  document.querySelectorAll("nav.apptabs span").forEach(function (s) {
    var href = APP_LINKS[s.textContent.trim()];
    if (href && !s.classList.contains("on")) linkify(s, href);
  });
  var brand = document.querySelector(".brand");
  if (brand) linkify(brand, "/");

  // 2. Account menu
  var css = document.createElement("style");
  css.textContent =
    // Same look as the app bar on the Daily picks and Portfolio pages; the active section is a soft pill so it
    // doesn't compete with the dark stock tab below it.
    ".sa-apptabs{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;margin-bottom:-4px}" +
    ".sa-apptabs span{flex:none;padding:7px 16px;border-radius:999px;color:var(--ink-2,#5E5A7A);font-weight:500;font-size:.94em}" +
    ".sa-apptabs span.on{background:var(--accent-soft,#ECE8FD);color:var(--accent,#5636D3);font-weight:700}" +
    ".sa-apptabs span[role=link]:hover{background:var(--surface,#fff)}" +
    ".sa-acct{position:relative;margin-left:4px}" +
    ".sa-acct>button{border:1px solid var(--line,#E4E1F2);background:var(--surface,#fff);border-radius:999px;padding:5px 12px 5px 5px;display:inline-flex;align-items:center;gap:8px;font:600 .86em var(--f-body,system-ui);color:var(--ink,#1C1838);cursor:pointer}" +
    ".sa-acct>button i{width:26px;height:26px;border-radius:50%;background:var(--accent,#5636D3);color:#fff;display:grid;place-items:center;font:800 12px var(--f-display,system-ui);font-style:normal}" +
    ".sa-menu{position:absolute;right:0;top:calc(100% + 6px);background:var(--surface,#fff);border:1px solid var(--line,#E4E1F2);border-radius:16px;box-shadow:0 18px 40px -18px rgba(28,24,56,.35);padding:6px;min-width:220px;z-index:50;display:grid;gap:2px}" +
    ".sa-menu a,.sa-menu button{border:0;background:transparent;text-align:left;padding:9px 12px;border-radius:10px;font:500 .9em var(--f-body,system-ui);color:var(--ink,#1C1838);text-decoration:none;cursor:pointer}" +
    ".sa-menu a:hover,.sa-menu button:hover{background:var(--surface-2,#EFEDF9)}" +
    ".sa-menu .who{padding:8px 12px 10px;border-bottom:1px solid var(--line,#E4E1F2);margin-bottom:4px;font-size:.82em;color:var(--ink-2,#5E5A7A)}" +
    ".sa-menu .who b{display:block;color:var(--ink,#1C1838);font-size:1.1em}" +
    ".sa-role{display:inline-block;margin-top:4px;border-radius:999px;padding:1px 8px;font:700 .8em var(--f-body,system-ui);background:var(--accent-soft,#ECE8FD);color:var(--accent,#5636D3)}" +
    ".sa-dlg{position:fixed;inset:0;background:rgba(28,24,56,.5);display:grid;place-items:center;z-index:90;padding:16px}" +
    ".sa-dlg form{background:var(--surface,#fff);border-radius:20px;padding:22px;width:min(380px,100%);display:grid;gap:12px;font-family:var(--f-body,system-ui)}" +
    ".sa-dlg h2{font:800 1.2em var(--f-display,system-ui);margin:0}" +
    ".sa-dlg label{display:grid;gap:4px;font-size:.86em;font-weight:700}" +
    ".sa-dlg input{border:1.5px solid var(--line,#E4E1F2);border-radius:12px;padding:10px 12px;font:500 1em var(--f-body,system-ui)}" +
    ".sa-dlg .row{display:flex;gap:8px;justify-content:flex-end}" +
    ".sa-dlg .err{color:var(--bad,#D2433A);font-size:.86em;font-weight:600;margin:0}" +
    ".sa-btn{border:1px solid var(--line,#E4E1F2);background:var(--surface,#fff);border-radius:999px;padding:8px 16px;font-weight:700;cursor:pointer}" +
    ".sa-btn.primary{background:var(--accent,#5636D3);border-color:var(--accent,#5636D3);color:#fff}";
  document.head.appendChild(css);

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function passwordDialog() {
    var wrap = document.createElement("div");
    wrap.className = "sa-dlg";
    wrap.innerHTML = '<form><h2>Change password</h2><label>Current password<input type="password" name="current" autocomplete="current-password" required></label>' +
      '<label>New password (10 characters or more)<input type="password" name="new" autocomplete="new-password" minlength="10" required></label>' +
      '<label>New password again<input type="password" name="again" autocomplete="new-password" required></label><p class="err" hidden></p>' +
      '<div class="row"><button type="button" class="sa-btn" data-x>Cancel</button><button class="sa-btn primary">Save</button></div></form>';
    document.body.appendChild(wrap);
    var form = wrap.querySelector("form"), err = wrap.querySelector(".err");
    wrap.querySelector("[data-x]").onclick = function () { wrap.remove(); };
    form.querySelector("input").focus();
    form.onsubmit = function (e) {
      e.preventDefault();
      if (form.new.value !== form.again.value) { err.textContent = "The new passwords don't match."; err.hidden = false; return; }
      SA.api("POST", "/api/auth/password", { current: form.current.value, new: form.new.value }).then(function () {
        wrap.remove(); alert("Password changed. Other browsers have been signed out.");
      }, function (x) { err.textContent = x.message; err.hidden = false; });
    };
  }

  SA.me().then(function (m) {
    if (!m) { SA.toLogin(); return; }
    var u = m.user, admin = u.role === "admin";
    var bar = document.querySelector(".topbar-in");
    if (bar) {
      var box = document.createElement("div");
      box.className = "sa-acct";
      box.innerHTML = '<button type="button" aria-haspopup="true" aria-expanded="false"><i aria-hidden="true">' + esc((u.name || "?").charAt(0).toUpperCase()) + '</i>' + esc(u.name.split(" ")[0]) + ' ▾</button>' +
        '<div class="sa-menu" role="menu" hidden><div class="who"><b>' + esc(u.name) + '</b>' + esc(u.email) + '<br><span class="sa-role">' + (admin ? "Admin" : "Member") + '</span></div>' +
        '<a role="menuitem" href="/stocks/' + esc(symbol) + '/overview">Stocks</a><a role="menuitem" href="/picks">Daily picks</a><a role="menuitem" href="/watchlist">Watchlist</a><a role="menuitem" href="/portfolio">Portfolio</a>' +
        (admin ? '<a role="menuitem" href="/admin">Admin: people and invites</a>' : "") +
        '<button type="button" role="menuitem" data-pw>Change password</button><button type="button" role="menuitem" data-out>Sign out</button></div>';
      bar.appendChild(box);
      var btn = box.querySelector("button"), menu = box.querySelector(".sa-menu");
      btn.onclick = function (e) { e.stopPropagation(); menu.hidden = !menu.hidden; btn.setAttribute("aria-expanded", String(!menu.hidden)); };
      document.addEventListener("click", function (e) { if (!box.contains(e.target)) { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); } });
      box.querySelector("[data-pw]").onclick = function () { menu.hidden = true; passwordDialog(); };
      box.querySelector("[data-out]").onclick = function () {
        SA.api("POST", "/api/auth/logout").then(function () { window.location.href = "/login"; }, function () { window.location.href = "/login"; });
      };
    }

    // 3. Blog: readers see the published posts only. The server refuses blog writes from non-admins regardless.
    if (/\/blog$/.test(path) && !admin) {
      var hideWrite = function () {
        var postsBtn = document.querySelector('[data-view="posts"]');
        if (postsBtn && postsBtn.getAttribute("aria-pressed") !== "true") postsBtn.click();
        var views = document.getElementById("views");
        if (views) views.hidden = true;
        var write = document.getElementById("v-write");
        if (write) write.hidden = true;
        var draftNote = document.querySelector(".asof");   // "Draft written from every tab…" is about writing
        if (draftNote) draftNote.hidden = true;
      };
      hideWrite();
      // The page redraws its view switch when Simple/Pro changes; keep the writing view hidden.
      document.querySelectorAll("button[data-mode]").forEach(function (b) { b.addEventListener("click", function () { setTimeout(hideWrite, 0); }); });
    }
  });
})();
