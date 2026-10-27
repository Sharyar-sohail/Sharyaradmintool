"""
ApexSys Security & Cryptographic Engine
Handles payload signing, HMAC-SHA256 authentication, replay-attack prevention,
and secure command token verification.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple

# Default server secret key (can be overridden via environment variable)
DEFAULT_SECRET_KEY = os.getenv("APEX_SECRET_KEY", "apexsys-master-commander-ultra-secure-key-2026")
TOKEN_EXPIRY_SECONDS = 300  # 5 minutes window for payload execution


class SecurityEngine:
    def __init__(self, secret_key: str = DEFAULT_SECRET_KEY):
        self.secret_key = secret_key.encode("utf-8")
        self._seen_nonces: Dict[str, float] = {}

    def _cleanup_nonces(self):
        """Purge nonces older than expiration window."""
        now = time.time()
        self._seen_nonces = {k: v for k, v in self._seen_nonces.items() if now - v < TOKEN_EXPIRY_SECONDS}

    def generate_nonce(self) -> str:
        """Generate a cryptographically secure hex nonce."""
        return secrets.token_hex(16)

    def sign_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Signs a command payload with timestamp, nonce, and HMAC-SHA256 signature.
        """
        self._cleanup_nonces()
        timestamp = int(time.time())
        nonce = self.generate_nonce()

        # Enforce timestamp and nonce inside payload metadata
        signed_payload = dict(payload)
        signed_payload["_meta"] = {
            "timestamp": timestamp,
            "nonce": nonce,
            "version": "1.0-apex"
        }

        # Canonical string representation
        canonical_str = self._canonicalize(signed_payload)
        signature = hmac.new(self.secret_key, canonical_str.encode("utf-8"), hashlib.sha256).hexdigest()
        signed_payload["_signature"] = signature
        return signed_payload

    def verify_payload(self, signed_payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verifies that a received payload is authentic, not tampered with, and not a replay.
        """
        self._cleanup_nonces()
        if "_signature" not in signed_payload or "_meta" not in signed_payload:
            return False, "Missing cryptographic signature or metadata."

        meta = signed_payload["_meta"]
        timestamp = meta.get("timestamp", 0)
        nonce = meta.get("nonce", "")
        received_sig = signed_payload["_signature"]

        # Check timestamp window
        now = time.time()
        if abs(now - timestamp) > TOKEN_EXPIRY_SECONDS:
            return False, f"Payload timestamp expired or out of bounds (skew: {abs(now - timestamp):.1f}s)."

        # Check replay nonce
        if nonce in self._seen_nonces:
            return False, "Replay attack detected: nonce already utilized."

        # Compute expected signature
        payload_copy = dict(signed_payload)
        del payload_copy["_signature"]
        canonical_str = self._canonicalize(payload_copy)
        expected_sig = hmac.new(self.secret_key, canonical_str.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(received_sig, expected_sig):
            return False, "Cryptographic signature mismatch. Payload may have been tampered with."

        # Register nonce
        self._seen_nonces[nonce] = now
        return True, "Valid"

    @staticmethod
    def _canonicalize(data: Dict[str, Any]) -> str:
        """Deterministic JSON string sorted by keys."""
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def create_agent_token(self, client_id: str) -> str:
        """Generate an authorization bearer token for a registered agent."""
        token_data = f"{client_id}:{time.time()}:{secrets.token_hex(8)}"
        token_hash = hmac.new(self.secret_key, token_data.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"apex_{client_id}_{token_hash[:32]}"


# Global default instance
security_engine = SecurityEngine()
