"""
Vault cryptographic primitives.

Quantum-resistant symmetric encryption with AES-256-GCM.
Key is a random 256-bit value, generated once and stored at rest.
"""

import os
import json
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path(__file__).parent
KEY_FILE = PLUGIN_DIR / "secret.key"
SALT_FILE = PLUGIN_DIR / "salt.bin"
VAULT_FILE = PLUGIN_DIR / "vault.enc"
HASH_FILE = PLUGIN_DIR / "vault.hash"

KEY_SIZE = 32  # 256-bit AES key
NONCE_SIZE = 12  # 96-bit GCM nonce
SALT_SIZE = 32  # 256-bit salt for password hashing
HASH_DKLEN = 32  # 256-bit derived hash
SCRYPT_N = 16384  # CPU/memory cost (2^14)
SCRYPT_R = 8      # block size
SCRYPT_P = 1      # parallelization


def _ensure_dir():
    """Ensure plugin data directory exists with restricted permissions."""
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
    if PLUGIN_DIR.stat().st_mode & 0o777 != 0o700:
        PLUGIN_DIR.chmod(0o700)


def _aes256_gcm_encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt plaintext with AES-256-GCM. Returns nonce || ciphertext || tag."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    # AESGCM.encrypt returns ciphertext || tag in one blob
    return nonce + ciphertext


def _aes256_gcm_decrypt(key: bytes, data: bytes) -> bytes:
    """Decrypt data produced by _aes256_gcm_encrypt. Expects nonce || ciphertext || tag."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = data[:NONCE_SIZE]
    ciphertext = data[NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def _scrypt_hash(password: str, salt: bytes) -> bytes:
    """Derive a verifiable hash from password + salt using SCRYPT (memory-hard, quantum-resistant)."""
    return hashlib.scrypt(
        password=password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=HASH_DKLEN,
    )


# ── Public API ──────────────────────────────────────────────────────────────


def ensure_key() -> bytes:
    """Return the AES-256-GCM key, generating and persisting it on first call."""
    _ensure_dir()
    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes()
        if len(key) == KEY_SIZE:
            return key
        logger.warning("vault key file has unexpected size, regenerating")

    key = os.urandom(KEY_SIZE)
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o400)  # read-only for owner
    logger.info("generated new vault encryption key")
    return key


def hash_is_configured() -> bool:
    """
    Check whether a vault password hash is configured — either via env var
    or local hash file. Used by the dashboard to decide if setup is needed.
    """
    if os.environ.get("HERMES_VAULT_PASS_HASH", ""):
        return True
    if HASH_FILE.exists():
        raw = HASH_FILE.read_bytes().strip()
        return len(raw) > 0
    return False


def store_password_hash(password: str) -> str:
    """
    Generate salt + hash for a password, persist the salt and hash file.
    Intended for first-run setup from the dashboard.
    Returns the hex hash (also stored to HASH_FILE).
    """
    h = get_password_hash(password)  # generates salt too
    _ensure_dir()
    HASH_FILE.write_text(h + "\n")
    HASH_FILE.chmod(0o400)
    logger.info("vault password hash stored locally")
    return h


def get_stored_hash() -> str | None:
    """
    Read the configured password hash from env var or local file.
    Returns the hex string or None if not configured.
    """
    h = os.environ.get("HERMES_VAULT_PASS_HASH", "")
    if h:
        return h.strip().lower()
    if HASH_FILE.exists():
        raw = HASH_FILE.read_bytes().strip()
        if raw:
            return raw.decode("utf-8").strip().lower()
    return None


def verify_password(password: str) -> bool:
    """
    Check a password against the configured hash (env var or local file).
    The hash stores hex(scrypt(password, salt=salt)).
    The salt is read from SALT_FILE (generated on first get_password_hash call).
    Returns True if the password matches, False otherwise.
    """
    stored = get_stored_hash()
    if not stored:
        return False  # no password configured at all

    if not SALT_FILE.exists():
        return False

    salt = SALT_FILE.read_bytes()
    if len(salt) != SALT_SIZE:
        return False

    computed = _scrypt_hash(password, salt)
    return computed.hex() == stored


def get_password_hash(password: str) -> str:
    """
    Generate the hash string that should be set as HERMES_VAULT_PASS_HASH.
    Returns the env var value: hex(scrypt(password, salt)).
    Persists the salt to SALT_FILE on first call.
    """
    _ensure_dir()
    if not SALT_FILE.exists():
        salt = os.urandom(SALT_SIZE)
        SALT_FILE.write_bytes(salt)
        SALT_FILE.chmod(0o400)
    else:
        salt = SALT_FILE.read_bytes()

    return _scrypt_hash(password, salt).hex()


# ── Entry serialisation ─────────────────────────────────────────────────────


def encode_entry(text: str, tag: str = "", timestamp: float | None = None) -> bytes:
    """
    Encrypt a single vault entry (text + optional tag + timestamp) into bytes.
    Returns encrypted blob suitable for append-only storage.
    """
    import time

    payload = json.dumps({
        "text": text,
        "tag": tag,
        "ts": timestamp or time.time(),
    }).encode("utf-8")

    key = ensure_key()
    return _aes256_gcm_encrypt(key, payload)


def decode_entry(data: bytes) -> dict:
    """Decrypt a single vault entry blob into {'text', 'tag', 'ts'}."""
    key = ensure_key()
    plain = _aes256_gcm_decrypt(key, data)
    return json.loads(plain.decode("utf-8"))


# ── Vault file operations ───────────────────────────────────────────────────


def read_vault() -> list[dict]:
    """
    Read and decrypt all entries from the vault file.
    Returns list of {'text', 'tag', 'ts'} dicts, newest first.
    """
    if not VAULT_FILE.exists():
        return []

    raw = VAULT_FILE.read_bytes()
    if not raw:
        return []

    # Format: [4-byte entry_length][encrypted_blob][4-byte entry_length]...
    entries = []
    offset = 0
    while offset < len(raw):
        if offset + 4 > len(raw):
            break
        length = int.from_bytes(raw[offset : offset + 4], "big")
        offset += 4
        if offset + length > len(raw):
            break
        blob = raw[offset : offset + length]
        offset += length
        try:
            entry = decode_entry(blob)
            entries.append(entry)
        except Exception as e:
            logger.warning(f"failed to decrypt vault entry: {e}")

    # newest first
    entries.sort(key=lambda e: e.get("ts", 0), reverse=True)
    return entries


def append_to_vault(text: str, tag: str = "") -> int:
    """
    Encrypt and append a new entry to the vault file.
    Returns the total number of entries in the vault.
    """
    blob = encode_entry(text, tag)
    length_bytes = len(blob).to_bytes(4, "big")

    _ensure_dir()
    with open(VAULT_FILE, "ab") as f:
        f.write(length_bytes + blob)

    entries = read_vault()
    return len(entries)
