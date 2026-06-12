"""
Vault Dashboard Plugin API.

FastAPI routes mounted at /api/plugins/vault/ by the Hermes dashboard.
Provides:
  - GET  /status    — vault status (locked/unlocked/empty, entry count)
  - POST /unlock    — verify vault password
  - POST /entries   — return decrypted vault entries (requires password)
  - GET  /setup-hash?password=... — generate env var hash (localhost only)
"""

import os
import sys
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

# Ensure the parent plugin dir is on the path for vault_crypto import
_plugin_dir = Path(__file__).resolve().parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from vault_crypto import read_vault, verify_password, get_password_hash, VAULT_FILE  # noqa: E402

router = APIRouter()

VAULT_PASS_HASH_VAR = "HERMES_VAULT_PASS_HASH"


def _has_password() -> bool:
    return bool(os.environ.get(VAULT_PASS_HASH_VAR, ""))


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/status")
async def status():
    """Check vault status — whether password is configured and entry count."""
    pw = _has_password()
    vault_exists = VAULT_FILE.exists() and VAULT_FILE.stat().st_size > 0
    entry_count = 0
    if vault_exists:
        try:
            entries = read_vault()
            entry_count = len(entries)
        except Exception as e:
            logger.warning(f"vault status read failed: {e}")

    return {
        "ok": True,
        "has_password": pw,
        "vault_exists": vault_exists,
        "entry_count": entry_count,
        "locked": pw,  # locked if password is configured
    }


@router.post("/unlock")
async def unlock(body: dict):
    """
    Unlock the vault with a password.
    Body: {"password": "..."}
    """
    password = body.get("password", "")
    if not password:
        return {"ok": False, "locked": True, "error": "Password required"}

    if verify_password(password):
        return {"ok": True, "locked": False}
    else:
        return {"ok": False, "locked": True, "error": "Incorrect password"}


@router.post("/entries")
async def entries(body: dict = None):
    """
    Return decrypted vault entries.
    Body: {"password": "..."}
    Requires valid password if HERMES_VAULT_PASS_HASH is set.
    """
    if body is None:
        body = {}

    pw = _has_password()
    if pw:
        password = body.get("password", "")
        if not password or not verify_password(password):
            raise HTTPException(status_code=401, detail="Invalid vault password")

    entries_list = read_vault()
    return {
        "ok": True,
        "count": len(entries_list),
        "entries": entries_list,
    }


@router.get("/setup-hash")
async def setup_hash(password: str = ""):
    """
    Generate the env var hash for a given password.
    Returns the value to set as HERMES_VAULT_PASS_HASH.
    WARNING: Only use this over localhost!
    """
    if not password:
        raise HTTPException(status_code=400, detail="password query param required")
    h = get_password_hash(password)
    return {
        "ok": True,
        "env_var": VAULT_PASS_HASH_VAR,
        "value": h,
        "instruction": f"Add this to your shell rc or .env: export {VAULT_PASS_HASH_VAR}={h}",
    }
