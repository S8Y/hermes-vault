"""
Vault Dashboard Plugin API.

FastAPI routes mounted at /api/plugins/vault/ by the Hermes dashboard.
Provides:
  - GET  /status    — vault status (needs_setup / locked / unlocked, entry count)
  - POST /setup     — first-run: set vault password (generates salt, stores hash)
  - POST /unlock    — verify vault password
  - POST /entries   — return decrypted vault entries (requires valid password)
"""

import os
import sys
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

# Ensure the parent plugin dir is on the path for vault_crypto import
_plugin_dir = Path(__file__).resolve().parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from vault_crypto import (  # noqa: E402
    read_vault,
    verify_password,
    hash_is_configured,
    store_password_hash,
    VAULT_FILE,
)

router = APIRouter()


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/status")
async def status():
    """Check vault status."""
    configured = hash_is_configured()
    vault_exists = VAULT_FILE.exists() and VAULT_FILE.stat().st_size > 0
    entry_count = 0
    if vault_exists:
        try:
            entries = read_vault()
            entry_count = len(entries)
        except Exception as e:
            logger.warning(f"vault status read failed: {e}")

    if not configured:
        return {
            "ok": True,
            "status": "needs_setup",
            "has_password": False,
            "vault_exists": vault_exists,
            "entry_count": entry_count,
        }

    return {
        "ok": True,
        "status": "locked",
        "has_password": True,
        "vault_exists": vault_exists,
        "entry_count": entry_count,
    }


@router.post("/setup")
async def setup(body: dict):
    """
    First-run setup: set the vault password.
    Body: {"password": "..."}
    Generates salt, stores the scrypt hash locally.
    Returns ok=True on success.
    """
    password = body.get("password", "")
    if not password:
        raise HTTPException(status_code=400, detail="Password required")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    # Prevent overwriting an existing configuration
    if hash_is_configured():
        raise HTTPException(status_code=409, detail="Vault password already configured")

    try:
        store_password_hash(password)
        return {"ok": True, "status": "locked"}
    except Exception as e:
        logger.exception("vault setup failed")
        raise HTTPException(status_code=500, detail=f"Failed to save vault password: {e}")


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
    Requires valid password if the vault hash is configured.
    """
    if body is None:
        body = {}

    if not hash_is_configured():
        raise HTTPException(status_code=400, detail="Vault not configured — set a password first")

    password = body.get("password", "")
    if not password or not verify_password(password):
        raise HTTPException(status_code=401, detail="Invalid vault password")

    entries_list = read_vault()
    return {
        "ok": True,
        "count": len(entries_list),
        "entries": entries_list,
    }
