"""
Cryptographic utilities for Weave receipt storage.
"""

import hashlib
import json
from typing import Any, Dict, Optional


def hash_payload(payload: Dict[str, Any]) -> str:
    """
    Generate a SHA-256 hash of a JSON payload.

    Args:
        payload: The payload to hash (dict or JSON-serializable object)

    Returns:
        SHA-256 hash as hex string with 'sha256:' prefix
    """
    # Convert to JSON string with sorted keys for consistent hashing
    json_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    # Generate SHA-256 hash
    hash_obj = hashlib.sha256(json_str.encode("utf-8"))
    hash_hex = hash_obj.hexdigest()

    return f"sha256:{hash_hex}"


def verify_hash(payload: Dict[str, Any], expected_hash: str) -> bool:
    """
    Verify that a payload matches an expected hash.

    Args:
        payload: The payload to verify
        expected_hash: The expected hash (with or without 'sha256:' prefix)

    Returns:
        True if the payload hash matches the expected hash
    """
    # Remove 'sha256:' prefix if present
    if expected_hash.startswith("sha256:"):
        expected_hash = expected_hash[7:]

    # Generate hash for the payload
    actual_hash = hash_payload(payload)
    actual_hash = actual_hash[7:]  # Remove 'sha256:' prefix

    return actual_hash == expected_hash


# VC (Verifiable Credential) signing stubs
class VCStubs:
    """Stub implementations for Verifiable Credential operations."""

    @staticmethod
    def sign_receipt(
        receipt_data: Dict[str, Any], private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sign a receipt with a Verifiable Credential proof (stub).

        Args:
            receipt_data: The receipt data to sign
            private_key: Private key for signing (optional, stub uses mock)

        Returns:
            Receipt data with VC proof attached
        """
        # Stub implementation - in real implementation this would:
        # 1. Create a VC with the receipt data
        # 2. Sign it with the private key
        # 3. Attach the proof to the receipt

        proof = {
            "type": "EcdsaSecp256k1Signature2019",
            "created": "2024-01-21T12:00:00Z",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "did:weave:key#mock-key-id",
            "jws": "mock-jws-signature-stub",
        }

        return {**receipt_data, "vc_proof": proof}

    @staticmethod
    def verify_receipt(receipt_data: Dict[str, Any], public_key: Optional[str] = None) -> bool:
        """
        Verify a receipt's Verifiable Credential proof (stub).

        Args:
            receipt_data: The receipt data with VC proof
            public_key: Public key for verification (optional, stub uses mock)

        Returns:
            True if verification passes (always True in stub)
        """
        # Stub implementation - in real implementation this would:
        # 1. Extract the VC proof
        # 2. Verify the signature against the public key
        # 3. Validate the proof structure

        vc_proof = receipt_data.get("vc_proof")
        if not vc_proof:
            return False

        # Mock verification - always returns True for stub
        return True
