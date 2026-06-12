# Hermes Vault Plugin

Encrypted message vault for Hermes Agent. Save assistant messages with `/vault`,
view them in the dashboard with password-protected decryption.

## How It Works

```
┌──────────────────────────────────────────────────┐
│  Agent Chat                                       │
│  ┌──────────────────────────────────────────┐    │
│  │ User: save that to the vault              │    │
│  │ Agent: *calls vault_store tool*           │    │
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
│  │ - Enter password                          │    │
│  │ - SCRYPT hash matches env var?            │    │
│  │ - Decrypt & display entries               │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

- **Encryption:** AES-256-GCM (quantum-resistant 256-bit symmetric key)
- **Key storage:** Random 256-bit key at `~/.hermes/plugins/vault/secret.key` (chmod 400)
- **Password verification:** SCRYPT memory-hard KDF, hash stored as `HERMES_VAULT_PASS_HASH` env var
- **Salt:** 256-bit random, stored at `salt.bin` (chmod 400)
- **Vault file:** `vault.enc` — length-prefixed encrypted entries

## Quick Start

```bash
# 1. Install the plugin (from the vault plugin directory)
./install.sh

# 2. Enable it
hermes plugins enable vault

# 3. Set up your vault password
python3 ~/.hermes/plugins/vault/vault_init.py
# → Follow the interactive prompts, then add the export to your shell rc

# 4. Restart Hermes and the dashboard
hermes dashboard --force-discover
```

## Usage

### In CLI / Chat

| Command | Description |
|---------|-------------|
| `/vault [tag]` | Save the last assistant message with optional tag |
| Agent: "save that to the vault" | Agent uses the `vault_store` tool automatically |
| Agent: "what's in the vault?" | Agent uses `vault_list` for summary |

### In Dashboard

Open `http://localhost:9119/vault` → enter vault password → browse entries.

## Security

- AES-256-GCM provides post-quantum security (Grover's algorithm halves effective key size to 128-bit, still infeasible at 2^128 ops)
- Encryption key file is `chmod 400` (owner read-only)
- SCRYPT memory-hard KDF resists GPU/ASIC brute-force
- Password is never stored in plaintext — only `scrypt(password, salt)` hex in env var
- Dashboard API binds to localhost only (inherited from Hermes dashboard)
