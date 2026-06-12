"""
Hermes Vault Plugin — encrypted message vault with /vault command and dashboard.

Registration wiring:
- Slash command `/vault [tag]` — saves the last assistant message to the vault
- Tool `vault_store` — tool-callable version (agent uses when it decides to)
- Hook `post_llm_call` — caches the last assistant response
"""

import json
import logging
from datetime import datetime

# Try relative import (when loaded as package), fall back to absolute
try:
    from . import vault_crypto
except ImportError:
    import vault_crypto

logger = logging.getLogger(__name__)

# Last assistant message cache: (session_id, text, timestamp)
_last_assistant: dict[str, tuple[str, float]] = {}
"""Maps session_id -> (message_text, timestamp)."""


def _on_post_llm_call(
    tool_name=None,
    args=None,
    result=None,
    task_id=None,
    duration_ms=None,
    **kwargs,
):
    """Post-LLM hook — we use the post_tool_call hook instead for caching."""
    pass


def _cache_assistant_response(
    session_id: str | None = None,
    user_message: str | None = None,
    response: str | None = None,
    history: list | None = None,
    model: str | None = None,
    platform: str | None = None,
    **kwargs,
):
    """
    Cache the last assistant response per session.
    Registered as post_llm_call hook.
    """
    if response and session_id:
        import time
        _last_assistant[session_id] = (response, time.time())
        # Keep cache bounded
        if len(_last_assistant) > 100:
            oldest = min(_last_assistant.keys(), key=lambda k: _last_assistant[k][1])
            del _last_assistant[oldest]
    return None


def _cmd_vault(raw_args: str) -> str:
    """
    Slash command handler for /vault.
    Saves the last assistant message in the current session to the encrypted vault.
    Usage: /vault [optional tag/note]
    """
    # The handler doesn't receive session_id directly, so we grab it
    # from the most recent cached message
    import os

    # Find the most recent session in our cache
    if not _last_assistant:
        return json.dumps({
            "error": "No assistant message cached yet. The agent needs to send a message first before using /vault.",
        })

    # Get the most recent entry (any session)
    session_id = max(_last_assistant.keys(), key=lambda k: _last_assistant[k][1])
    text, ts = _last_assistant[session_id]

    tag = raw_args.strip() if raw_args.strip() else ""

    try:
        count = vault_crypto.append_to_vault(text, tag=tag)
        ts_human = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        parts = [
            f"✓ Saved to vault (entry #{count})",
            f"  Tag: {'untagged' if not tag else tag}",
            f"  From: {ts_human}",
            f"  Length: {len(text)} chars",
        ]
        return json.dumps({"ok": True, "count": count, "message": "\n".join(parts)})
    except Exception as e:
        logger.exception("vault save failed")
        return json.dumps({"error": f"Failed to save to vault: {e}"})


def _tool_vault_store(args: dict, **kwargs) -> str:
    """
    Tool handler: vault_store.
    Saves provided text to the encrypted vault.
    Parameters:
      - text: The text content to store (required)
      - tag: Optional tag/category for the entry
    """
    text = args.get("text", "").strip()
    if not text:
        return json.dumps({"error": "No text provided"})

    tag = args.get("tag", "").strip() or ""

    try:
        count = vault_crypto.append_to_vault(text, tag=tag)
        return json.dumps({
            "ok": True,
            "count": count,
            "text": f"Saved to vault (entry #{count})",
        })
    except Exception as e:
        logger.exception("vault_store failed")
        return json.dumps({"error": str(e)})


def _tool_vault_list(args: dict, **kwargs) -> str:
    """
    Tool handler: vault_list.
    Lists entries from the vault. Only returns count and tags — full content
    requires the dashboard with password.
    Parameters:
      - limit: Max entries to show (default 10)
    """
    limit = max(1, min(int(args.get("limit", 10)), 100))

    try:
        entries = vault_crypto.read_vault()
        summary = []
        for i, e in enumerate(entries[:limit], 1):
            tag = e.get("tag", "") or "untagged"
            ts = datetime.fromtimestamp(e.get("ts", 0)).strftime("%Y-%m-%d %H:%M")
            preview = e.get("text", "")[:80]
            summary.append(f"{i}. [{ts}] [{tag}] {preview}...")

        return json.dumps({
            "ok": True,
            "total": len(entries),
            "shown": min(limit, len(entries)),
            "entries": summary,
        })
    except Exception as e:
        logger.exception("vault_list failed")
        return json.dumps({"error": str(e)})


def register(ctx):
    """
    Plugin registration entry point.
    Called by Hermes plugin loader at startup.
    """
    # Register slash command: /vault [tag]
    ctx.register_command(
        name="vault",
        handler=_cmd_vault,
        description="Save the last assistant message to the encrypted vault. "
                    "Usage: /vault [optional tag/note]",
    )

    # Register tool for the agent to store to vault
    ctx.register_tool(
        name="vault_store",
        toolset="vault",
        schema={
            "name": "vault_store",
            "description": "Store text content in the encrypted vault. "
                           "Use this when the user asks you to save something to the vault.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text content to store in the vault",
                    },
                    "tag": {
                        "type": "string",
                        "description": "Optional tag or category for this entry",
                    },
                },
                "required": ["text"],
            },
        },
        handler=_tool_vault_store,
    )

    # Register hook to cache assistant responses
    ctx.register_hook("post_llm_call", _cache_assistant_response)

    logger.info("vault plugin registered — /vault, vault_store")
