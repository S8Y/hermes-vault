# Hermes Vault Plugin — Fixed Release

Two bugs fixed:

## 1. "Vault not reachable: Unauthorized" (dashboard/auth)

**dashboard/dist/index.js** — the React UI's `API._req` helper now reads
`window.__HERMES_SESSION_TOKEN__` (injected into the SPA HTML by the Hermes
dashboard) and passes it as the `X-Hermes-Session-Token` header on every API
request. Previously raw `fetch()` calls without auth headers hit the dashboard's
auth middleware and returned 401.

## 2. vault_list tool not registered

**__init__.py** — `_tool_vault_list` was fully implemented but never wired up
in `register()`. Added `ctx.register_tool(...)` call for `vault_list`.

## Install

```bash
hermes plugin uninstall vault   # if already installed
cd ~/.hermes/plugins
tar xzf /path/to/hermes-vault-fixed.tar.gz
mv hermes-vault-archive vault
hermes plugins enable vault
python3 ~/.hermes/plugins/vault/vault_init.py
hermes dashboard --force-discover
```
