# Hermes Vault Plugin

Encrypted message vault for Hermes Agent. Save assistant messages with `/vault`,
view them in the dashboard with password-protected decryption.

**The agent can only write to the vault — it cannot read entries back.**
Only the web dashboard (with your password) can decrypt and display vault contents.

## How It Works

```
┌──────────────────────────────────────────────────┐
│  Agent Chat                                       │
│  ┌──────────────────────────────────────────┐    │
│  │ User: save that to the vault              │    │
│  │ Agent: *calls vault_store tool*          │    │  WRITE ONLY
│  │ User: /vault my-tag                       │    │  (agent can't read)
│  └──────────────────────────────────────────┘    │
│         │                                         │
│         ▼                                         │
│  ┌──────────────────┐     ┌──────────────────┐   │
│  │ vault_crypto.py  │────▶│ vault.enc        │   │
│  │ AES-256-GCM      │     │ (quantum-proof   │   │
│  │ encrypt/decrypt  │     │  encrypted)       │   │
│  └──────────────────┘     └──────────────────┘   │
│         │                                         │
│         ▼                                         │
│  ┌──────────────────────────────────────────┐    │
│  │ Dashboard Tab (localhost:9119/vault)      │    │
│  │ 1. Setup: create password (first visit)   │    │
│  │ 2. Unlock: enter password                 │    │
│  │ 3. Decrypt & view entries                 │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

- **Encryption:** AES-256-GCM (256-bit symmetric key, post-quantum resistant)
- **Key storage:** Random 256-bit key at `secret.key` (chmod 400)
- **Password:** SCRYPT memory-hard KDF; hash stored locally in `vault.hash` or via `HERMES_VAULT_PASS_HASH` env var
- **Salt:** 256-bit random at `salt.bin` (chmod 400)
- **Vault file:** `vault.enc` — length-prefixed encrypted entries

## Quick Start

```bash
# 1. Install
./install.sh

# 2. Enable
hermes plugins enable vault

# 3. Restart Hermes + dashboard reload
hermes dashboard --force-discover

# 4. Open http://localhost:9119/vault
#    → First visit: set your vault password in the UI
#    → Done. Use /vault in chat to start saving entries.
```

No env var editing needed — the password hash is stored locally during first-run setup.

## Usage

### In CLI / Chat (Write Only)

| Command | Description |
|---------|-------------|
| `/vault [tag]` | Save the last assistant message with optional tag |
| "save that to the vault" | Agent calls `vault_store` tool automatically |

The agent will **never** read or list vault entries. Contents are only viewable
from the dashboard with the correct password.

### In Dashboard

Open `http://localhost:9119/vault`:
1. **First visit** — setup screen: choose your vault password
2. **Subsequent visits** — unlock screen: enter password to decrypt entries
3. Browse all stored entries with full text

## Security

- AES-256-GCM provides post-quantum security (Grover's → 2^128 ops)
- Encryption key file is `chmod 400` (owner read-only)
- SCRYPT memory-hard KDF resists GPU/ASIC brute-force
- Password is never stored in plaintext — only `scrypt(password, salt)` hex
- Password hash stored at `vault.hash` (chmod 400) or `HERMES_VAULT_PASS_HASH` env var
- Dashboard API binds to localhost only (inherited from Hermes dashboard)

## File Structure

```
~/.hermes/plugins/vault/
├── plugin.yaml          # Plugin manifest
├── __init__.py          # /vault command + vault_store tool
├── vault_crypto.py      # AES-256-GCM + SCRYPT primitives
├── vault_init.py        # CLI setup tool
├── install.sh           # One-command installer
├── secret.key           # AES-256 key (auto-generated, chmod 400)
├── salt.bin             # SCRYPT salt (auto-generated, chmod 400)
├── vault.hash           # Password hash (auto-generated, chmod 400)
├── vault.enc            # Encrypted entries
└── dashboard/
    ├── manifest.json    # Tab config
    ├── plugin_api.py    # FastAPI routes
    └── dist/
        ├── index.js     # React UI
        └── style.css    # Styles
```
