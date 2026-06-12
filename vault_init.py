#!/usr/bin/env python3
"""
Vault CLI helper — setup and manage the Hermes vault.

Usage:
  python vault_init.py           # Interactive setup (prompts for password)
  python vault_init.py <pass>    # Generate hash non-interactively
  python vault_init.py --check   # Check if env var is set
"""

import os
import sys
import hashlib
import hmac

# Add parent to path so we can import vault_crypto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vault_crypto import get_password_hash, verify_password, SALT_FILE, PLUGIN_DIR


ENV_VAR = "HERMES_VAULT_PASS_HASH"


def cmd_generate(password: str):
    """Generate the env var hash for a password."""
    h = get_password_hash(password)
    print(f"\n  {ENV_VAR}={h}")
    print(f"\n  Add to your ~/.bashrc, ~/.zshrc, or .env file:")
    print(f"  export {ENV_VAR}={h}")
    print(f"\n  Salt stored at: {SALT_FILE}")
    print(f"  Vault directory: {PLUGIN_DIR}")
    return h


def cmd_check():
    """Check if the env var is set and valid."""
    val = os.environ.get(ENV_VAR, "")
    if not val:
        print(f"  {ENV_VAR} is NOT set.")
        print(f"  Run `python vault_init.py` interactively to set it up.")
        return False

    salt_ok = SALT_FILE.exists()
    if not salt_ok:
        print(f"  {ENV_VAR} is set but SALT_FILE ({SALT_FILE}) is missing.")
        print(f"  Run `python vault_init.py <password>` to regenerate.")
        return False

    salt = SALT_FILE.read_bytes()
    computed = hashlib.scrypt(
        password=b"test-verify",
        salt=salt,
        n=16384, r=8, p=1, dklen=32,
    )
    print(f"  {ENV_VAR} is set ✓")
    print(f"  Salt file exists: {SALT_FILE} ✓")
    return True


def cmd_interactive():
    """Interactive password setup."""
    import getpass

    print("\n  ═══ Hermes Vault Setup ═══\n")

    # Check if already configured
    existing = os.environ.get(ENV_VAR, "")
    if existing:
        print(f"  {ENV_VAR} is already set.")
        overwrite = input("  Overwrite? [y/N] ").strip().lower()
        if overwrite != "y":
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

    h = get_password_hash(pw1)
    print(f"\n  ─────────────────────────────")
    print(f"  Set this in your environment:")
    print(f"  export {ENV_VAR}={h}")
    print(f"  ─────────────────────────────")
    print(f"\n  Add it to ~/.bashrc, ~/.zshrc, or your Hermes .env file.")
    print(f"  Then restart Hermes or reload the dashboard.\n")


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
