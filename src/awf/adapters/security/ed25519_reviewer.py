"""Ed25519 verification; never generates or persists reviewer private keys."""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from awf.domain.evidence import EvidenceIntegrityError


class Ed25519ReviewerVerifier:
    def verify(self, *, public_key_hex: str, signature_hex: str, message: bytes) -> None:
        try:
            public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
            public_key.verify(bytes.fromhex(signature_hex), message)
        except (InvalidSignature, ValueError, TypeError) as exc:
            raise EvidenceIntegrityError("reviewer signature verification failed") from exc
