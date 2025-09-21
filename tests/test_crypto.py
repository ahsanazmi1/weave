"""
Tests for crypto module.
"""


from weave.crypto import VCStubs, hash_payload, verify_hash


class TestHashPayload:
    """Test hash_payload function."""

    def test_hash_payload_basic(self):
        """Test basic hash generation."""
        payload = {"key": "value"}
        hash_result = hash_payload(payload)

        assert hash_result.startswith("sha256:")
        assert len(hash_result) == 71  # "sha256:" + 64 hex chars

    def test_hash_payload_consistent(self):
        """Test that same payload produces same hash."""
        payload = {"user_id": "123", "amount": "99.99"}
        hash1 = hash_payload(payload)
        hash2 = hash_payload(payload)

        assert hash1 == hash2

    def test_hash_payload_different_order(self):
        """Test that different key order produces same hash."""
        payload1 = {"user_id": "123", "amount": "99.99"}
        payload2 = {"amount": "99.99", "user_id": "123"}

        hash1 = hash_payload(payload1)
        hash2 = hash_payload(payload2)

        assert hash1 == hash2

    def test_hash_payload_different_values(self):
        """Test that different values produce different hashes."""
        payload1 = {"user_id": "123"}
        payload2 = {"user_id": "456"}

        hash1 = hash_payload(payload1)
        hash2 = hash_payload(payload2)

        assert hash1 != hash2


class TestVerifyHash:
    """Test verify_hash function."""

    def test_verify_hash_valid(self):
        """Test hash verification with valid hash."""
        payload = {"key": "value"}
        expected_hash = hash_payload(payload)

        assert verify_hash(payload, expected_hash) is True

    def test_verify_hash_with_prefix(self):
        """Test hash verification with sha256: prefix."""
        payload = {"key": "value"}
        expected_hash = hash_payload(payload)

        assert verify_hash(payload, expected_hash) is True

    def test_verify_hash_without_prefix(self):
        """Test hash verification without sha256: prefix."""
        payload = {"key": "value"}
        expected_hash = hash_payload(payload)[7:]  # Remove "sha256:" prefix

        assert verify_hash(payload, expected_hash) is True

    def test_verify_hash_invalid(self):
        """Test hash verification with invalid hash."""
        payload = {"key": "value"}
        invalid_hash = "sha256:invalidhash"

        assert verify_hash(payload, invalid_hash) is False


class TestVCStubs:
    """Test VC (Verifiable Credential) stub functions."""

    def test_sign_receipt(self):
        """Test receipt signing stub."""
        receipt_data = {
            "receipt_id": "receipt_123",
            "trace_id": "trace_456",
            "event_hash": "sha256:abc123"
        }

        signed_receipt = VCStubs.sign_receipt(receipt_data)

        assert "vc_proof" in signed_receipt
        assert signed_receipt["receipt_id"] == "receipt_123"
        assert signed_receipt["trace_id"] == "trace_456"
        assert signed_receipt["event_hash"] == "sha256:abc123"

        vc_proof = signed_receipt["vc_proof"]
        assert vc_proof["type"] == "EcdsaSecp256k1Signature2019"
        assert "created" in vc_proof
        assert "proofPurpose" in vc_proof
        assert "verificationMethod" in vc_proof
        assert "jws" in vc_proof

    def test_sign_receipt_with_private_key(self):
        """Test receipt signing with private key parameter."""
        receipt_data = {"receipt_id": "receipt_123"}

        signed_receipt = VCStubs.sign_receipt(receipt_data, "mock_private_key")

        assert "vc_proof" in signed_receipt

    def test_verify_receipt_valid(self):
        """Test receipt verification with valid proof."""
        receipt_data = {
            "receipt_id": "receipt_123",
            "vc_proof": {
                "type": "EcdsaSecp256k1Signature2019",
                "created": "2024-01-21T12:00:00Z"
            }
        }

        assert VCStubs.verify_receipt(receipt_data) is True

    def test_verify_receipt_with_public_key(self):
        """Test receipt verification with public key parameter."""
        receipt_data = {
            "receipt_id": "receipt_123",
            "vc_proof": {"type": "mock"}
        }

        assert VCStubs.verify_receipt(receipt_data, "mock_public_key") is True

    def test_verify_receipt_no_proof(self):
        """Test receipt verification without VC proof."""
        receipt_data = {"receipt_id": "receipt_123"}

        assert VCStubs.verify_receipt(receipt_data) is False
