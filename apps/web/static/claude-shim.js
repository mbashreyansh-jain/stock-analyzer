/* Connects the approved pages to the Stock AI server.

   The pages were designed as claude.ai artifacts, where they ask for features through window.claude.use(name).
   This file provides the same features from our own server, so the page files stay exactly as approved:
     downloads  -> saves the file straight to the computer
     user       -> who is signed in, and whether they are the admin
     db         -> the Blog page's published posts, stored in our database (only the admin can write)
     sample     -> "Rewrite with AI", answered by Gemini on the server (admin only)
   Anything else resolves to null, which the pages already treat as "not available". */
(function () {
  "use strict";

  var mePromise = null;
  function me() {
    if (!mePromise) {
      mePromise = fetch("/api/me", { credentials: "same-origin" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; });
    }
    return mePromise;
  }

  function toLogin() {
    window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
  }

  function codeFor(status) {
    if (status === 401 || status === 403) return "invalid_argument";
    if (status === 413) return "quota_exceeded";
    if (status === 429) return "rate_limited";
    return "unavailable";
  }

  // JSON request to our API. Writes carry the CSRF token from /api/me.
  function api(method, url, body, signal) {
    return me().then(function (m) {
      var headers = { "Content-Type": "application/json" };
      if (m) headers["X-CSRF-Token"] = m.csrf;
      return fetch(url, {
        method: method, headers: headers, credentials: "same-origin", signal: signal,
        body: body === undefined ? undefined : JSON.stringify(body)
      });
    }).then(function (r) {
      if (r.status === 401) { toLogin(); }
      if (r.ok) return r.json();
      return r.json().catch(function () { return {}; }).then(function (j) {
        var d = j.detail;
        throw {
          status: r.status,
          code: (d && d.code) || codeFor(r.status),
          message: (d && d.message) || (typeof d === "string" ? d : "The request didn't work.")
        };
      });
    }, function (e) {
      if (e && e.name === "AbortError") throw { code: "cancelled", message: "Stopped." };
      if (e && e.code) throw e;
      throw { code: "unavailable", message: "Can't reach the Stock AI server." };
    });
  }

  // ---- downloads ----
  var TYPES = { pdf: "application/pdf", csv: "text/csv;charset=utf-8",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", json: "application/json" };
  var downloads = {
    save: function (file) {
      return new Promise(function (ok, fail) {
        try {
          var name = (file && file.filename) || "download";
          var ext = (name.split(".").pop() || "").toLowerCase();
          var data = file.data;
          var blob = data instanceof Blob ? data : new Blob([data], { type: file.mimeType || TYPES[ext] || "application/octet-stream" });
          var a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = name;
          document.body.appendChild(a);
          a.click();
          setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
          ok();
        } catch (e) {
          fail({ code: "unavailable", message: "Couldn't save the file." });
        }
      });
    }
  };

  // ---- user ----
  function userFor(m) {
    var admin = m.user.role === "admin";
    return {
      id: function () { return Promise.resolve(String(m.user.id)); },
      me: function () { return Promise.resolve({ id: String(m.user.id), name: m.user.name }); },
      isOwner: function () { return admin; },
      canEdit: function () { return admin; },
      can: function (name) { return name === "data.write" ? admin : null; },
      profiles: function () { return Promise.resolve({}); },
      search: function () { return Promise.resolve([]); }
    };
  }

  // ---- db: the Blog page's "posts" collection ----
  var listeners = [], poll = null;
  function snapshot(rows) {
    var docs = rows.map(function (r) {
      return { id: r.id, exists: true, data: function () { return r.data; }, metadata: { fromCache: false, hasPendingWrites: false } };
    });
    return { docs: docs, size: docs.length, empty: !docs.length, docChanges: function () { return []; },
      metadata: { fromCache: false, hasPendingWrites: false } };
  }
  function refresh() {
    return api("GET", "/api/blog/posts").then(function (rows) {
      var snap = snapshot(rows);
      listeners.slice().forEach(function (l) { l.next(snap); });
    }, function (err) {
      listeners.slice().forEach(function (l) { if (l.error) l.error(err); });
    });
  }
  function postsQuery() {
    var q = {
      orderBy: function () { return q; },
      limit: function () { return q; },
      where: function () { return q; },
      get: function () { return api("GET", "/api/blog/posts").then(snapshot); },
      onSnapshot: function (next, error) {
        var l = { next: next, error: error };
        listeners.push(l);
        refresh();
        if (!poll) poll = setInterval(refresh, 30000);   // picks up posts the admin publishes elsewhere
        return function () { listeners = listeners.filter(function (x) { return x !== l; }); };
      },
      doc: function (id) {
        var url = "/api/blog/posts/" + encodeURIComponent(id);
        return {
          id: id, path: "posts/" + id,
          get: function () {
            return api("GET", "/api/blog/posts").then(function (rows) {
              var r = rows.filter(function (x) { return x.id === id; })[0];
              return { id: id, exists: !!r, data: function () { return r ? r.data : undefined; } };
            });
          },
          set: function (data) { return api("PUT", url, data).then(function () { refresh(); }); },
          update: function (data) { return api("PUT", url, data).then(function () { refresh(); }); },
          delete: function () { return api("DELETE", url).then(function () { refresh(); }); }
        };
      }
    };
    q.add = function (data) {
      var id = "post-" + Date.now().toString(36);
      return q.doc(id).set(data).then(function () { return q.doc(id); });
    };
    return q;
  }
  var db = {
    collection: function (path) {
      if (path !== "posts") throw new TypeError("Only the blog's 'posts' collection is available on this server.");
      return postsQuery();
    },
    doc: function (path) {
      var parts = String(path).split("/");
      return db.collection(parts[0]).doc(parts[1]);
    }
  };

  // ---- sample: "Rewrite with AI" through Gemini on the server ----
  function sampleFn() {
    var f = function (input, opts) {
      return f.json(input, opts).then(function (v) { return { text: JSON.stringify(v), truncated: false }; });
    };
    f.json = function (input, opts) {
      opts = opts || {};
      if (opts.signal && opts.signal.aborted) return Promise.reject({ code: "cancelled" });
      var prompt = typeof input === "string" ? input : input.map(function (t) { return t.content; }).join("\n\n");
      return api("POST", "/api/ai/json", { prompt: prompt }, opts.signal).then(function (j) {
        if (opts.onText) { try { opts.onText({ text: "…", delta: "…" }); } catch (e) { /* the page's own handler */ } }
        return j.result;
      });
    };
    f.limits = function () { return Promise.resolve({ maxPromptBytes: 60000 }); };
    return f;
  }

  window.claude = {
    use: function (name) {
      if (name === "downloads") return Promise.resolve(downloads);
      if (name === "db") return me().then(function (m) { return m ? db : null; });
      if (name === "user") return me().then(function (m) { return m ? userFor(m) : null; });
      if (name === "sample") return me().then(function (m) { return m && m.user.role === "admin" ? sampleFn() : null; });
      return Promise.resolve(null);
    }
  };

  // Shared with app.js (navigation and the account menu).
  window.StockAI = { me: me, api: api, toLogin: toLogin };
})();
