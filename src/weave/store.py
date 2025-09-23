"""
Pluggable storage backends for Weave receipt storage.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ocn_common.trace import new_trace_id

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .settings import settings

Base = declarative_base()


class Receipt(Base):
    """SQLAlchemy model for receipt storage."""

    __tablename__ = "receipts"

    receipt_id = Column(String(36), primary_key=True)
    trace_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_hash = Column(String(70), nullable=False, index=True)  # sha256: prefix + 64 chars
    time = Column(DateTime, nullable=False, default=datetime.utcnow)
    receipt_metadata = Column(Text)  # JSON string


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def store_receipt(
        self,
        trace_id: str,
        event_type: str,
        event_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a receipt and return receipt_id."""
        pass

    @abstractmethod
    def get_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a receipt by ID."""
        pass

    @abstractmethod
    def get_receipts_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """Retrieve all receipts for a trace_id."""
        pass

    @abstractmethod
    def list_receipts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List receipts with pagination."""
        pass


class InMemoryStorage(StorageBackend):
    """In-memory storage backend for testing and development."""

    def __init__(self):
        self._receipts: Dict[str, Dict[str, Any]] = {}

    def store_receipt(
        self,
        trace_id: str,
        event_type: str,
        event_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a receipt in memory."""
        receipt_id = new_trace_id()

        receipt_data = {
            "receipt_id": receipt_id,
            "trace_id": trace_id,
            "event_type": event_type,
            "event_hash": event_hash,
            "time": datetime.now(timezone.utc).isoformat(),
            "metadata": json.dumps(metadata) if metadata else None,
        }

        self._receipts[receipt_id] = receipt_data
        return receipt_id

    def get_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a receipt by ID."""
        receipt_data = self._receipts.get(receipt_id)
        if receipt_data and receipt_data["metadata"] and isinstance(receipt_data["metadata"], str):
            receipt_data["metadata"] = json.loads(receipt_data["metadata"])
        return receipt_data

    def get_receipts_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """Retrieve all receipts for a trace_id."""
        receipts = []
        for receipt_data in self._receipts.values():
            if receipt_data["trace_id"] == trace_id:
                if receipt_data["metadata"] and isinstance(receipt_data["metadata"], str):
                    receipt_data["metadata"] = json.loads(receipt_data["metadata"])
                receipts.append(receipt_data)
        return sorted(receipts, key=lambda x: x["time"])

    def list_receipts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List receipts with pagination."""
        all_receipts = list(self._receipts.values())
        all_receipts.sort(key=lambda x: x["time"], reverse=True)

        # Process metadata
        for receipt_data in all_receipts:
            if receipt_data["metadata"] and isinstance(receipt_data["metadata"], str):
                receipt_data["metadata"] = json.loads(receipt_data["metadata"])

        return all_receipts[offset : offset + limit]


class SQLiteStorage(StorageBackend):
    """SQLite storage backend for persistent storage."""

    def __init__(self, database_url: str = None):
        if database_url is None:
            database_url = settings.database_url

        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables
        Base.metadata.create_all(bind=self.engine)

    def store_receipt(
        self,
        trace_id: str,
        event_type: str,
        event_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a receipt in SQLite."""
        receipt_id = new_trace_id()

        receipt = Receipt(
            receipt_id=receipt_id,
            trace_id=trace_id,
            event_type=event_type,
            event_hash=event_hash,
            time=datetime.now(timezone.utc),
            receipt_metadata=json.dumps(metadata) if metadata else None,
        )

        session = self.SessionLocal()
        try:
            session.add(receipt)
            session.commit()
            return receipt_id
        finally:
            session.close()

    def get_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a receipt by ID."""
        session = self.SessionLocal()
        try:
            receipt = session.query(Receipt).filter(Receipt.receipt_id == receipt_id).first()
            if receipt:
                return self._receipt_to_dict(receipt)
            return None
        finally:
            session.close()

    def get_receipts_by_trace_id(self, trace_id: str) -> List[Dict[str, Any]]:
        """Retrieve all receipts for a trace_id."""
        session = self.SessionLocal()
        try:
            receipts = (
                session.query(Receipt)
                .filter(Receipt.trace_id == trace_id)
                .order_by(Receipt.time.asc())
                .all()
            )
            return [self._receipt_to_dict(receipt) for receipt in receipts]
        finally:
            session.close()

    def list_receipts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List receipts with pagination."""
        session = self.SessionLocal()
        try:
            receipts = (
                session.query(Receipt)
                .order_by(Receipt.time.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [self._receipt_to_dict(receipt) for receipt in receipts]
        finally:
            session.close()

    def _receipt_to_dict(self, receipt: Receipt) -> Dict[str, Any]:
        """Convert Receipt model to dictionary."""
        result = {
            "receipt_id": receipt.receipt_id,
            "trace_id": receipt.trace_id,
            "event_type": receipt.event_type,
            "event_hash": receipt.event_hash,
            "time": receipt.time.isoformat(),
        }

        if receipt.receipt_metadata:
            result["metadata"] = json.loads(receipt.receipt_metadata)
        else:
            result["metadata"] = None

        return result


class StorageFactory:
    """Factory for creating storage backends."""

    @staticmethod
    def create_storage(backend_type: str = "sqlite", **kwargs) -> StorageBackend:
        """
        Create a storage backend.

        Args:
            backend_type: Type of storage backend ('memory' or 'sqlite')
            **kwargs: Additional arguments for the storage backend

        Returns:
            Storage backend instance
        """
        if backend_type == "memory":
            return InMemoryStorage()
        elif backend_type == "sqlite":
            return SQLiteStorage(**kwargs)
        else:
            raise ValueError(f"Unknown storage backend: {backend_type}")


# Global storage instance
def get_storage() -> StorageBackend:
    """Get the configured storage backend."""
    # For now, use SQLite by default
    # In production, this could be configured via environment variables
    return StorageFactory.create_storage("sqlite")
