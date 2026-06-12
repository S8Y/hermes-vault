(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;

  var e = SDK.React.createElement;
  var useState = SDK.React.useState;
  var useEffect = SDK.React.useEffect;
  var useCallback = SDK.React.useCallback;

  /* ──── Raw API helper (bypasses SDK.fetchJSON auth probe) ── */

  var API = {
    _req: function (path, opts) {
      opts = opts || {};
      var headers = opts.headers || { "Content-Type": "application/json" };
      /* Inject dashboard session token for loopback auth */
      if (window.__HERMES_SESSION_TOKEN__) {
        headers["X-Hermes-Session-Token"] = window.__HERMES_SESSION_TOKEN__;
      }
      return fetch(path, {
        method: opts.method || "GET",
        headers: headers,
        body: opts.body || null,
      }).then(function (r) {
        if (!r.ok) {
          return r.json().then(function (j) {
            throw new Error(j.detail || j.error || (r.status + " " + r.statusText));
          }).catch(function (e) {
            if (e instanceof SyntaxError) throw new Error(r.status + " " + r.statusText);
            throw e;
          });
        }
        return r.json();
      });
    },
    get: function (path) { return API._req(path); },
    post: function (path, body) {
      return API._req(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
    },
  };

  /* ──── Helpers ─────────────────────────────────────── */

  var H = {
    fmtTime: function (ts) {
      if (!ts) return "\u2014";
      try {
        var d = new Date(ts * 1000);
        return d.toLocaleString(undefined, {
          year: "numeric", month: "short", day: "numeric",
          hour: "2-digit", minute: "2-digit",
        });
      } catch (_) { return "\u2014"; }
    },
    tagLabel: function (tag) {
      return tag && tag.trim() ? tag.trim() : "untagged";
    },
  };

  /* ──── Setup Screen ────────────────────────────────── */

  var SetupScreen = function (props) {
    var _a = useState(""), pw1 = _a[0], setPw1 = _a[1];
    var _b = useState(""), pw2 = _b[0], setPw2 = _b[1];
    var _c = useState(""), error = _c[0], setError = _c[1];
    var _d = useState(false), loading = _d[0], setLoading = _d[1];

    var handleSetup = useCallback(function () {
      if (pw1.length < 4) {
        setError("Password must be at least 4 characters");
        return;
      }
      if (pw1 !== pw2) {
        setError("Passwords do not match");
        return;
      }
      setLoading(true);
      setError("");
      API.post("/api/plugins/vault/setup", { password: pw1 })
        .then(function (res) {
          setLoading(false);
          if (res.ok) {
            props.onSetup(pw1);
          } else {
            setError(res.detail || "Failed to set password");
          }
        })
        .catch(function (err) {
          setLoading(false);
          setError("Connection error: " + (err.message || err));
        });
    }, [pw1, pw2, props.onSetup]);

    var handleKey = useCallback(function (ev) {
      if (ev.key === "Enter" && !loading) handleSetup();
    }, [handleSetup, loading]);

    return e("div", { className: "vault-lock-screen" },
      e("div", { className: "vault-lock-icon" }, "\uD83D\uDD10"),
      e("div", { className: "vault-lock-title" }, "Set Up Your Vault"),
      e("div", { className: "vault-lock-desc" },
        "This is your first time opening the vault. ",
        "Choose a password to encrypt and protect your stored entries. ",
        "The password hash is stored locally \u2014 no plaintext ever touches disk."
      ),
      e("div", { style: { display: "flex", flexDirection: "column", gap: "0.6rem", alignItems: "center" } },
        e("input", {
          className: "vault-password-input",
          type: "password",
          placeholder: "Vault password",
          value: pw1,
          onChange: function (ev) { setPw1(ev.target.value); setError(""); },
          onKeyDown: handleKey,
          disabled: loading,
          autoFocus: true,
        }),
        e("input", {
          className: "vault-password-input",
          type: "password",
          placeholder: "Confirm password",
          value: pw2,
          onChange: function (ev) { setPw2(ev.target.value); setError(""); },
          onKeyDown: handleKey,
          disabled: loading,
        }),
        e("button", {
          className: "vault-unlock-btn",
          onClick: handleSetup,
          disabled: loading || !pw1 || !pw2,
          style: { marginTop: "0.25rem" },
        }, loading ? "Setting up\u2026" : "Set Password"),
      ),
      error ? e("div", { className: "vault-error", style: { marginTop: "0.5rem" } }, error) : null
    );
  };

  /* ──── Lock Screen ─────────────────────────────────── */

  var LockScreen = function (props) {
    var passwordRef = SDK.React.useRef(null);
    var _a = useState(""), password = _a[0], setPassword = _a[1];
    var _b = useState(false), loading = _b[0], setLoading = _b[1];
    var _c = useState(""), error = _c[0], setError = _c[1];

    var handleUnlock = useCallback(function () {
      if (!password) return;
      setLoading(true);
      setError("");
      API.post("/api/plugins/vault/unlock", { password: password })
        .then(function (res) {
          setLoading(false);
          if (res.locked === false && res.ok) {
            props.onUnlock(password);
          } else {
            setError(res.error || "Incorrect password");
            if (passwordRef.current) {
              passwordRef.current.value = "";
              passwordRef.current.focus();
            }
          }
        })
        .catch(function (err) {
          setLoading(false);
          setError("Connection error: " + (err.message || err));
        });
    }, [password, props.onUnlock]);

    var handleKey = useCallback(function (ev) {
      if (ev.key === "Enter") handleUnlock();
    }, [handleUnlock]);

    return e("div", { className: "vault-lock-screen" },
      e("div", { className: "vault-lock-icon" }, "\uD83D\uDD12"),
      e("div", { className: "vault-lock-title" }, "Vault Locked"),
      e("div", { className: "vault-lock-desc" },
        "Enter your vault password to decrypt and view stored entries."
      ),
      e("div", { className: "vault-password-form" },
        e("input", {
          ref: passwordRef,
          className: "vault-password-input",
          type: "password",
          placeholder: "Vault password",
          value: password,
          onChange: function (ev) { setPassword(ev.target.value); setError(""); },
          onKeyDown: handleKey,
          disabled: loading,
          autoFocus: true,
        }),
        e("button", {
          className: "vault-unlock-btn",
          onClick: handleUnlock,
          disabled: loading || !password,
        }, loading ? "Unlocking\u2026" : "Unlock")
      ),
      error ? e("div", { className: "vault-error" }, error) : null
    );
  };

  /* ──── Entry Row ───────────────────────────────────── */

  var EntryRow = function (props) {
    var entry = props.entry;
    var idx = props.index;
    var tag = H.tagLabel(entry.tag);
    return e("div", { className: "vault-entry", key: idx },
      e("div", { className: "vault-entry-meta" },
        e("span", { className: "vault-entry-number" }, "#" + (idx + 1)),
        e("span", { className: "vault-entry-tag" }, tag),
        e("span", { className: "vault-entry-ts" }, H.fmtTime(entry.ts)),
      ),
      e("div", { className: "vault-entry-text" }, entry.text || "")
    );
  };

  /* ──── Entry List ──────────────────────────────────── */

  var EntryList = function (props) {
    var entries = props.entries;
    var onLock = props.onLock;

    if (!entries || entries.length === 0) {
      return e("div", { className: "vault-empty" },
        e("div", { className: "vault-empty-icon" }, "\uD83D\uDCED"),
        e("div", null, "Your vault is empty. ",
          "Use /vault in a Hermes chat to save assistant messages here.")
      );
    }

    return e("div", null,
      e("div", { className: "vault-header" },
        e("span", { className: "vault-count" },
          entries.length + " entr" + (entries.length === 1 ? "y" : "ies")
        ),
        e("div", { className: "vault-toolbar" },
          e("button", {
            className: "vault-btn vault-btn-danger",
            onClick: onLock,
          }, "\uD83D\uDD12 Lock")
        )
      ),
      e("div", { className: "vault-entry-list" },
        entries.map(function (entry, i) {
          return e(EntryRow, { entry: entry, index: i, key: i });
        })
      )
    );
  };

  /* ──── Vault Page (Main Component) ─────────────────── */

  var VaultPage = function () {
    var _a = useState("loading"), status = _a[0], setStatus = _a[1];
    var _b = useState(null), vaultPassword = _b[0], setVaultPassword = _b[1];
    var _c = useState([]), entries = _c[0], setEntries = _c[1];
    var _d = useState(""), error = _d[0], setError = _d[1];

    /* Load vault status on mount */
    useEffect(function () {
      API.get("/api/plugins/vault/status")
        .then(function (res) {
          if (res.status === "needs_setup") {
            setStatus("needs_setup");
          } else if (res.status === "locked") {
            setStatus("locked");
          } else if (res.status === "error" || res.error) {
            setStatus("error");
            setError(res.error || res.detail || "Vault unavailable");
          } else {
            /* Fallback: treat any non-matching response as needs_setup
               so the user always sees actionable UI instead of a dead state */
            setStatus("needs_setup");
          }
        })
        .catch(function (err) {
          setStatus("error");
          setError("Vault not reachable: " + (err.message || err));
        });
    }, []);

    /* Handle setup complete */
    var handleSetup = useCallback(function (password) {
      setStatus("loading_entries");
      setError("");
      setVaultPassword(password);
      API.post("/api/plugins/vault/entries", { password: password })
        .then(function (res) {
          if (res.ok) {
            setEntries(res.entries || []);
            setStatus("unlocked");
          } else {
            setStatus("locked");
            setError(res.detail || "Failed to load entries");
          }
        })
        .catch(function (err) {
          setStatus("locked");
          setError("Connection error: " + (err.message || err));
        });
    }, []);

    /* Handle unlock */
    var handleUnlock = useCallback(function (password) {
      setStatus("loading_entries");
      setError("");
      setVaultPassword(password);
      API.post("/api/plugins/vault/entries", { password: password })
        .then(function (res) {
          if (res.ok) {
            setEntries(res.entries || []);
            setStatus("unlocked");
          } else {
            setStatus("locked");
            setError(res.detail || "Failed to load entries");
          }
        })
        .catch(function (err) {
          setStatus("locked");
          setError("Connection error: " + (err.message || err));
        });
    }, []);

    var handleLock = useCallback(function () {
      setVaultPassword(null);
      setStatus("locked");
      setEntries([]);
    }, []);

    /* Render based on status */
    if (status === "loading") {
      return e("div", { className: "vault-page" },
        e("div", { className: "vault-lock-screen" },
          e("div", { className: "vault-lock-icon" }, "\u23F3"),
          e("div", { className: "vault-lock-title" }, "Loading vault\u2026")
        )
      );
    }

    if (status === "needs_setup") {
      return e("div", { className: "vault-page" },
        e(SetupScreen, { onSetup: handleSetup })
      );
    }

    if (status === "locked") {
      return e("div", { className: "vault-page" },
        error ? e("div", { className: "vault-error", style: { textAlign: "center", padding: "0.5rem" } }, error) : null,
        e(LockScreen, { onUnlock: handleUnlock })
      );
    }

    if (status === "error") {
      return e("div", { className: "vault-page" },
        e("div", { className: "vault-lock-screen" },
          e("div", { className: "vault-lock-icon" }, "\u26A0\uFE0F"),
          e("div", { className: "vault-lock-title" }, "Vault Error"),
          e("div", { className: "vault-error", style: { whiteSpace: "pre-wrap", maxWidth: "28rem" } },
            error || "Something went wrong"
          )
        )
      );
    }

    /* unlocked or loading_entries */
    return e("div", { className: "vault-page" },
      e(EntryList, { entries: entries, onLock: handleLock })
    );
  };

  /* ──── Register ────────────────────────────────────── */

  window.__HERMES_PLUGINS__.register("vault", VaultPage);

})();
