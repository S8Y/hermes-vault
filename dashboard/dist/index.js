(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;

  var e = SDK.React.createElement;
  var useState = SDK.React.useState;
  var useEffect = SDK.React.useEffect;
  var useCallback = SDK.React.useCallback;

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
      SDK.fetchJSON("/api/plugins/vault/unlock", {
        method: "POST",
        body: JSON.stringify({ password: password }),
        headers: { "Content-Type": "application/json" },
      }).then(function (res) {
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
      }).catch(function (err) {
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
        "Enter your vault password to decrypt and view stored entries. ",
        "The password hash is stored in the HERMES_VAULT_PASS_HASH environment variable."
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
    var _b = useState(false), hasPassword = _b[0], setHasPassword = _b[1];
    var _c = useState(null), vaultPassword = _c[0], setVaultPassword = _c[1];
    var _d = useState([]), entries = _d[0], setEntries = _d[1];
    var _e = useState(0), entryCount = _e[0], setEntryCount = _e[1];
    var _f = useState(""), error = _f[0], setError = _f[1];

    /* Load vault status on mount */
    useEffect(function () {
      SDK.fetchJSON("/api/plugins/vault/status")
        .then(function (res) {
          setHasPassword(res.has_password);
          setEntryCount(res.entry_count);
          if (res.has_password) {
            setStatus("locked");
          } else if (res.vault_exists) {
            /* No password configured — just show entries */
            setVaultPassword("");
            setStatus("loading_entries");
            return SDK.fetchJSON("/api/plugins/vault/entries", {
              method: "POST",
              body: JSON.stringify({ password: "" }),
              headers: { "Content-Type": "application/json" },
            }).then(function (r) {
              if (r.ok) {
                setEntries(r.entries || []);
                setStatus("unlocked");
              } else {
                setStatus("locked");
                setError(r.error || "Failed to load entries");
              }
            });
          } else {
            setStatus("empty");
          }
        })
        .catch(function (err) {
          setStatus("error");
          setError("Failed to load vault status: " + (err.message || err));
        });
    }, []);

    /* Handle unlock */
    var handleUnlock = useCallback(function (password) {
      setStatus("loading_entries");
      setError("");
      setVaultPassword(password);
      SDK.fetchJSON("/api/plugins/vault/entries", {
        method: "POST",
        body: JSON.stringify({ password: password }),
        headers: { "Content-Type": "application/json" },
      }).then(function (res) {
        if (res.ok) {
          setEntries(res.entries || []);
          setEntryCount(res.count || 0);
          setStatus("unlocked");
        } else {
          setStatus("locked");
          setError(res.error || "Failed to load entries");
        }
      }).catch(function (err) {
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

    if (status === "empty" && !hasPassword) {
      return e("div", { className: "vault-page" },
        e("div", { className: "vault-setup-section" },
          e("div", { style: { fontSize: "2.5rem" } }, "\uD83D\uDD12"),
          e("div", { style: { fontSize: "1.2rem", fontWeight: 600 } }, "No Vault Configured"),
          e("div", { style: { fontSize: "0.85rem", color: "var(--color-muted-foreground)", maxWidth: 420, lineHeight: 1.5 } },
            "To set up your vault:", e("br"),
            "1. Set HERMES_VAULT_PASS_HASH in your environment", e("br"),
            "2. Or use the dashboard setup endpoint to generate the hash", e("br"),
            "3. Use /vault in chat to start saving entries"
          )
        )
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
          e("div", { className: "vault-lock-title" }, "Error"),
          e("div", { className: "vault-error" }, error || "Something went wrong")
        )
      );
    }

    /* unlocked */
    return e("div", { className: "vault-page" },
      e(EntryList, { entries: entries, onLock: handleLock })
    );
  };

  /* ──── Register ────────────────────────────────────── */

  window.__HERMES_PLUGINS__.register("vault", VaultPage);

})();
