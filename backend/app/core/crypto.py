"""Cryptographic primitives: Canonical JSON, SHA-256 hashing, Ed25519 signatures, and QR generation."""

import base64
import hashlib
import io
import json
from datetime import datetime, timezone
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import qrcode
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.config import get_settings


def normalize_for_canonical(value: Any) -> Any:
    """Convert Python primitives (Decimal, datetime) deterministically for canonical JSON."""
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        dt = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if isinstance(value, dict):
        return {str(k): normalize_for_canonical(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_for_canonical(item) for item in value]
    return value


def canonical_json(obj: Any) -> str:
    """Serialize any JSON-compatible object into deterministic canonical JSON."""
    normalized = normalize_for_canonical(obj)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_sha256_hex(data: str) -> str:
    """Compute lowercase SHA-256 hex digest of UTF-8 text."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _load_or_create_private_key() -> Ed25519PrivateKey:
    settings = get_settings()
    if settings.ED25519_PRIVATE_KEY_B64.strip():
        raw_bytes = base64.b64decode(settings.ED25519_PRIVATE_KEY_B64.strip())
        return Ed25519PrivateKey.from_private_bytes(raw_bytes)

    key_dir = Path(settings.DEV_KEY_DIR)
    key_dir.mkdir(parents=True, exist_ok=True)
    key_file = key_dir / "ed25519_dev.key"
    if key_file.exists():
        raw_bytes = base64.b64decode(key_file.read_text(encoding="utf-8").strip())
        return Ed25519PrivateKey.from_private_bytes(raw_bytes)

    private_key = Ed25519PrivateKey.generate()
    raw_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_file.write_text(base64.b64encode(raw_bytes).decode("ascii"), encoding="utf-8")
    return private_key


@lru_cache(maxsize=1)
def get_signing_key() -> Ed25519PrivateKey:
    """Cached Ed25519 signing key for the running process."""
    return _load_or_create_private_key()


def get_public_key_b64(private_key: Ed25519PrivateKey | None = None) -> str:
    """Return base64-encoded raw 32-byte Ed25519 public key."""
    key = private_key or get_signing_key()
    pub_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(pub_bytes).decode("ascii")


def get_public_key_fingerprint(public_key_b64: str) -> str:
    """Return SHA-256 fingerprint of the public key."""
    return compute_sha256_hex(public_key_b64)[:16]


def sign_hash_ed25519(sha256_hex: str) -> tuple[str, str, str]:
    """Sign a SHA-256 hex digest using Ed25519. Returns (signature_b64, public_key_b64, fingerprint)."""
    private_key = get_signing_key()
    signature_bytes = private_key.sign(sha256_hex.encode("utf-8"))
    sig_b64 = base64.b64encode(signature_bytes).decode("ascii")
    pub_b64 = get_public_key_b64(private_key)
    return sig_b64, pub_b64, get_public_key_fingerprint(pub_b64)


def verify_hash_ed25519(sha256_hex: str, signature_b64: str, public_key_b64: str) -> bool:
    """Verify an Ed25519 signature over a SHA-256 hex digest."""
    try:
        pub_bytes = base64.b64decode(public_key_b64)
        sig_bytes = base64.b64decode(signature_b64)
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, sha256_hex.encode("utf-8"))
        return True
    except (InvalidSignature, ValueError):
        return False


def generate_qr_png_bytes(url: str) -> bytes:
    """Generate a high-contrast QR code PNG for a passport verification URL."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0B0B0D", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_data_uri(url: str) -> str:
    """Generate a base64 PNG data URI for embedding QR codes directly in JSON responses."""
    raw = generate_qr_png_bytes(url)
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
