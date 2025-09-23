"""
Tests for store module.
"""

import pytest

from weave.store import InMemoryStorage, SQLiteStorage, StorageFactory


class TestInMemoryStorage:
    """Test in-memory storage backend."""

    def test_store_and_retrieve_receipt(self):
        """Test storing and retrieving a receipt."""
        storage = InMemoryStorage()

        # Store a receipt
        receipt_id = storage.store_receipt(
            trace_id="trace_123",
            event_type="ocn.orca.decision.v1",
            event_hash="sha256:abc123",
            metadata={"key": "value"},
        )

        assert receipt_id is not None

        # Retrieve the receipt
        receipt = storage.get_receipt(receipt_id)

        assert receipt is not None
        assert receipt["receipt_id"] == receipt_id
        assert receipt["trace_id"] == "trace_123"
        assert receipt["event_type"] == "ocn.orca.decision.v1"
        assert receipt["event_hash"] == "sha256:abc123"
        assert receipt["metadata"]["key"] == "value"

    def test_get_nonexistent_receipt(self):
        """Test retrieving a non-existent receipt."""
        storage = InMemoryStorage()
        receipt = storage.get_receipt("nonexistent")
        assert receipt is None

    def test_get_receipts_by_trace_id(self):
        """Test retrieving receipts by trace_id."""
        storage = InMemoryStorage()

        # Store multiple receipts with same trace_id
        receipt_id1 = storage.store_receipt(
            trace_id="trace_123", event_type="ocn.orca.decision.v1", event_hash="sha256:hash1"
        )

        receipt_id2 = storage.store_receipt(
            trace_id="trace_123", event_type="ocn.orca.explanation.v1", event_hash="sha256:hash2"
        )

        # Store receipt with different trace_id
        storage.store_receipt(
            trace_id="trace_456", event_type="ocn.orca.decision.v1", event_hash="sha256:hash3"
        )

        # Get receipts for trace_123
        receipts = storage.get_receipts_by_trace_id("trace_123")

        assert len(receipts) == 2
        receipt_ids = [r["receipt_id"] for r in receipts]
        assert receipt_id1 in receipt_ids
        assert receipt_id2 in receipt_ids

    def test_list_receipts(self):
        """Test listing receipts with pagination."""
        storage = InMemoryStorage()

        # Store multiple receipts
        for i in range(5):
            storage.store_receipt(
                trace_id=f"trace_{i}",
                event_type="ocn.orca.decision.v1",
                event_hash=f"sha256:hash{i}",
            )

        # List receipts with pagination
        receipts = storage.list_receipts(limit=3, offset=0)
        assert len(receipts) == 3

        receipts_page2 = storage.list_receipts(limit=3, offset=3)
        assert len(receipts_page2) == 2

    def test_receipt_without_metadata(self):
        """Test storing receipt without metadata."""
        storage = InMemoryStorage()

        receipt_id = storage.store_receipt(
            trace_id="trace_123", event_type="ocn.orca.decision.v1", event_hash="sha256:abc123"
        )

        receipt = storage.get_receipt(receipt_id)
        assert receipt["metadata"] is None


class TestSQLiteStorage:
    """Test SQLite storage backend."""

    @pytest.fixture
    def temp_sqlite_storage(self, tmp_path):
        """Create a temporary SQLite storage for testing."""
        db_path = tmp_path / "test_receipts.db"
        database_url = f"sqlite:///{db_path}"
        return SQLiteStorage(database_url)

    def test_store_and_retrieve_receipt(self, temp_sqlite_storage):
        """Test storing and retrieving a receipt."""
        storage = temp_sqlite_storage

        # Store a receipt
        receipt_id = storage.store_receipt(
            trace_id="trace_123",
            event_type="ocn.orca.decision.v1",
            event_hash="sha256:abc123",
            metadata={"key": "value"},
        )

        assert receipt_id is not None

        # Retrieve the receipt
        receipt = storage.get_receipt(receipt_id)

        assert receipt is not None
        assert receipt["receipt_id"] == receipt_id
        assert receipt["trace_id"] == "trace_123"
        assert receipt["event_type"] == "ocn.orca.decision.v1"
        assert receipt["event_hash"] == "sha256:abc123"
        assert receipt["metadata"]["key"] == "value"

    def test_get_nonexistent_receipt(self, temp_sqlite_storage):
        """Test retrieving a non-existent receipt."""
        storage = temp_sqlite_storage
        receipt = storage.get_receipt("nonexistent")
        assert receipt is None

    def test_get_receipts_by_trace_id(self, temp_sqlite_storage):
        """Test retrieving receipts by trace_id."""
        storage = temp_sqlite_storage

        # Store multiple receipts with same trace_id
        receipt_id1 = storage.store_receipt(
            trace_id="trace_123", event_type="ocn.orca.decision.v1", event_hash="sha256:hash1"
        )

        receipt_id2 = storage.store_receipt(
            trace_id="trace_123", event_type="ocn.orca.explanation.v1", event_hash="sha256:hash2"
        )

        # Store receipt with different trace_id
        storage.store_receipt(
            trace_id="trace_456", event_type="ocn.orca.decision.v1", event_hash="sha256:hash3"
        )

        # Get receipts for trace_123
        receipts = storage.get_receipts_by_trace_id("trace_123")

        assert len(receipts) == 2
        receipt_ids = [r["receipt_id"] for r in receipts]
        assert receipt_id1 in receipt_ids
        assert receipt_id2 in receipt_ids

    def test_list_receipts(self, temp_sqlite_storage):
        """Test listing receipts with pagination."""
        storage = temp_sqlite_storage

        # Store multiple receipts
        for i in range(5):
            storage.store_receipt(
                trace_id=f"trace_{i}",
                event_type="ocn.orca.decision.v1",
                event_hash=f"sha256:hash{i}",
            )

        # List receipts with pagination
        receipts = storage.list_receipts(limit=3, offset=0)
        assert len(receipts) == 3

        receipts_page2 = storage.list_receipts(limit=3, offset=3)
        assert len(receipts_page2) == 2


class TestStorageFactory:
    """Test storage factory."""

    def test_create_memory_storage(self):
        """Test creating in-memory storage."""
        storage = StorageFactory.create_storage("memory")
        assert isinstance(storage, InMemoryStorage)

    def test_create_sqlite_storage(self, tmp_path):
        """Test creating SQLite storage."""
        db_path = tmp_path / "test.db"
        database_url = f"sqlite:///{db_path}"

        storage = StorageFactory.create_storage("sqlite", database_url=database_url)
        assert isinstance(storage, SQLiteStorage)

    def test_create_unknown_storage(self):
        """Test creating unknown storage type."""
        with pytest.raises(ValueError, match="Unknown storage backend"):
            StorageFactory.create_storage("unknown")
