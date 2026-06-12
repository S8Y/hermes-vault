#!/usr/bin/env python3
"""
Vault CLI helper — setup and manage the Hermes vault.

Usage:
  python vault_init.py               # Interactive setup (stores hash locally)
  python vault_init.py <password>    # Non-interactive setup
  python vault_init.py --check       # Check if vault is configured
"""
import os
import sys
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vault_crypto import (
    get_password_hash,
    store_password_hash,
    hash_is_configured,
    verify_password,
    HASH_FILE,
    SALT_FILE,
    PLUGIN_DIR,
)


ENV_VAR = "HERMES_VAULT_PASS_HASH"


def cmd_generate(password: str):
    """Store password hash locally (env var free setup)."""
    h = store_password_hash(password)
    print(f"\n  Vault password configured ✓")
    print(f"  Hash stored at: {HASH_FILE}")
    print(f"  Salt stored at: {SALT_FILE}")
    print(f"  You can now use /vault in chat and the dashboard tab.")
    print(f"\n  Advanced: to use env var instead, set:")
    print(f"  export {ENV_VAR}={h}")
    return h


def cmd_check():
    """Check if vault is configured."""
    configured = hash_is_configured()
    if not configured:
        print(f"  Vault password is NOT configured.")
        print(f"  Run `python vault_init.py` or open the dashboard vault tab to set one up.")
        return False

    print(f"  Vault password is configured ✓")
    if HASH_FILE.exists():
        print(f"  Local hash: {HASH_FILE} ✓")
    if ENV_VAR in os.environ:
        print(f"  Env var {ENV_VAR}: set ✓")
    print(f"  Salt file: {SALT_FILE} {'✓' if SALT_FILE.exists() else '✗'}")
    return True


def cmd_interactive():
    """Interactive password setup — stores hash locally."""
    import getpass

    print("\n  ═══ Hermes Vault Setup ═══\n")

    if hash_is_configured():
        print(f"  Vault is already configured.")
        yn = input("  Overwrite? [y/N] ").strip().lower()
        if yn != "y":
            print("  Aborted.")
            return

    pw1 = getpass.getpass("  Enter vault password: ")
    pw2 = getpass.getpass("  Confirm vault password: ")

    if pw1 != pw2:
        print("  Passwords do not match. Aborted.")
        sys.exit(1)

    if len(pw1) < 4:
        print("  Password must be at least 4 characters. Aborted.")
        sys.exit(1)

    cmd_generate(pw1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--check":
            cmd_check()
        elif arg.startswith("--"):
            print(f"Unknown option: {arg}")
            print("Usage: python vault_init.py [password|--check]")
            sys.exit(1)
        else:
            cmd_generate(arg)
    else:
        cmd_interactive()
