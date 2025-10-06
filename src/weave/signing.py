"""
Digital signing and audit logging for Weave Phase 4.

Provides cryptographic signing, verification, and comprehensive audit logging
for payment instructions, auction results, and processor responses.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from pydantic import BaseModel, Field

from weave.models import (
    PaymentInstruction, 
    ProcessorAuthResult, 
    SignedReceipt, 
    AuctionResult,
    BidRequest,
    BidResponse
)

logger = logging.getLogger(__name__)


class SigningKey(BaseModel):
    """Signing key for receipt verification."""
    
    key_id: str = Field(..., description="Unique key identifier")
    private_key_pem: str = Field(..., description="Private key in PEM format")
    public_key_pem: str = Field(..., description="Public key in PEM format")
    created_at: datetime = Field(default_factory=datetime.now, description="Key creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Key expiration timestamp")
    active: bool = Field(True, description="Whether key is active")


class AuditLog(BaseModel):
    """Audit log entry for transaction tracking."""
    
    log_id: str = Field(..., description="Unique log identifier")
    trace_id: str = Field(..., description="Transaction trace ID")
    event_type: str = Field(..., description="Type of event being logged")
    event_data: Dict[str, Any] = Field(..., description="Event data payload")
    signature: str = Field(..., description="Digital signature of log entry")
    timestamp: datetime = Field(default_factory=datetime.now, description="Log timestamp")
    source: str = Field(..., description="Source component generating the log")


class DigitalSigner:
    """
    Digital signing service for Weave receipts and audit logs.
    
    Provides cryptographic signing, verification, and key management
    for secure audit trails and receipt integrity.
    """
    
    def __init__(self, key_id: str = "weave-main-key"):
        """Initialize digital signer with default key."""
        self.key_id = key_id
        self.signing_key = self._generate_signing_key()
        logger.info(f"Digital signer initialized with key: {key_id}")
    
    def _generate_signing_key(self) -> SigningKey:
        """Generate a new RSA signing key pair."""
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return SigningKey(
            key_id=self.key_id,
            private_key_pem=private_pem,
            public_key_pem=public_pem
        )
    
    def sign_data(self, data: Dict[str, Any]) -> str:
        """
        Sign data using the signing key.
        
        Args:
            data: Data to sign (will be JSON serialized and hashed)
            
        Returns:
            Digital signature as base64 string
        """
        # Serialize data to JSON
        json_data = json.dumps(data, sort_keys=True, default=str)
        
        # Hash the data
        data_hash = hashlib.sha256(json_data.encode('utf-8')).digest()
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            self.signing_key.private_key_pem.encode('utf-8'),
            password=None
        )
        
        # Sign the hash
        signature = private_key.sign(
            data_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Return base64 encoded signature
        import base64
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """
        Verify data signature.
        
        Args:
            data: Original data that was signed
            signature: Signature to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Serialize data to JSON
            json_data = json.dumps(data, sort_keys=True, default=str)
            
            # Hash the data
            data_hash = hashlib.sha256(json_data.encode('utf-8')).digest()
            
            # Load public key
            public_key = serialization.load_pem_public_key(
                self.signing_key.public_key_pem.encode('utf-8')
            )
            
            # Decode signature
            import base64
            signature_bytes = base64.b64decode(signature)
            
            # Verify signature
            public_key.verify(
                signature_bytes,
                data_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


class ReceiptSigner:
    """
    Specialized receipt signing service.
    
    Creates signed receipts that link payment instructions with processor
    authorization results, providing complete audit trails.
    """
    
    def __init__(self, signer: DigitalSigner):
        """Initialize receipt signer."""
        self.signer = signer
        logger.info("Receipt signer initialized")
    
    def create_signed_receipt(
        self,
        payment_instruction: PaymentInstruction,
        processor_auth_result: ProcessorAuthResult,
        auction_result: AuctionResult,
        bid_requests: List[BidRequest],
        bid_responses: List[BidResponse]
    ) -> SignedReceipt:
        """
        Create a signed receipt linking payment instruction and processor result.
        
        Args:
            payment_instruction: Payment instruction from Orca
            processor_auth_result: Processor authorization result
            auction_result: Auction result that led to transaction
            bid_requests: All bid requests sent to processors
            bid_responses: All bid responses received
            
        Returns:
            Signed receipt with complete audit trail
        """
        # Create receipt data for signing
        receipt_data = {
            "instruction_id": payment_instruction.instruction_id,
            "trace_id": payment_instruction.trace_id,
            "processor_id": processor_auth_result.processor_id,
            "status": processor_auth_result.status,
            "amount": payment_instruction.amount,
            "effective_cost": payment_instruction.effective_cost,
            "processor_fee": processor_auth_result.processor_fee,
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate receipt hash
        receipt_hash = hashlib.sha256(
            json.dumps(receipt_data, sort_keys=True).encode('utf-8')
        ).hexdigest()
        
        # Sign the receipt data
        signature = self.signer.sign_data(receipt_data)
        
        # Create signed receipt
        signed_receipt = SignedReceipt(
            receipt_id=str(uuid.uuid4()),
            trace_id=payment_instruction.trace_id,
            payment_instruction=payment_instruction,
            processor_auth_result=processor_auth_result,
            auction_result=auction_result,
            bid_requests=bid_requests,
            bid_responses=bid_responses,
            receipt_hash=receipt_hash,
            signature=signature,
            signing_key_id=self.signer.key_id,
            verified=self.signer.verify_signature(receipt_data, signature)
        )
        
        logger.info(f"Created signed receipt {signed_receipt.receipt_id} for trace {payment_instruction.trace_id}")
        return signed_receipt
    
    def verify_receipt(self, receipt: SignedReceipt) -> bool:
        """
        Verify receipt signature and integrity.
        
        Args:
            receipt: Receipt to verify
            
        Returns:
            True if receipt is valid, False otherwise
        """
        # Recreate receipt data
        receipt_data = {
            "instruction_id": receipt.payment_instruction.instruction_id,
            "trace_id": receipt.payment_instruction.trace_id,
            "processor_id": receipt.processor_auth_result.processor_id,
            "status": receipt.processor_auth_result.status,
            "amount": receipt.payment_instruction.amount,
            "effective_cost": receipt.payment_instruction.effective_cost,
            "processor_fee": receipt.processor_auth_result.processor_fee,
            "timestamp": receipt.created_at.isoformat()
        }
        
        # Verify signature
        is_valid = self.signer.verify_signature(receipt_data, receipt.signature)
        
        # Verify hash
        expected_hash = hashlib.sha256(
            json.dumps(receipt_data, sort_keys=True).encode('utf-8')
        ).hexdigest()
        
        hash_valid = expected_hash == receipt.receipt_hash
        
        logger.info(f"Receipt {receipt.receipt_id} verification: signature={is_valid}, hash={hash_valid}")
        return is_valid and hash_valid


class AuditLogger:
    """
    Comprehensive audit logging service.
    
    Logs all critical events with digital signatures for tamper-proof
    audit trails and compliance requirements.
    """
    
    def __init__(self, signer: DigitalSigner):
        """Initialize audit logger."""
        self.signer = signer
        logger.info("Audit logger initialized")
    
    def log_payment_instruction(
        self,
        payment_instruction: PaymentInstruction,
        source: str = "orca"
    ) -> AuditLog:
        """
        Log payment instruction creation.
        
        Args:
            payment_instruction: Payment instruction to log
            source: Source component (e.g., "orca")
            
        Returns:
            Signed audit log entry
        """
        event_data = payment_instruction.dict()
        signature = self.signer.sign_data(event_data)
        
        audit_log = AuditLog(
            log_id=str(uuid.uuid4()),
            trace_id=payment_instruction.trace_id,
            event_type="payment_instruction_created",
            event_data=event_data,
            signature=signature,
            source=source
        )
        
        logger.info(f"Logged payment instruction {payment_instruction.instruction_id} for trace {payment_instruction.trace_id}")
        return audit_log
    
    def log_auction_result(
        self,
        auction_result: AuctionResult,
        source: str = "weave"
    ) -> AuditLog:
        """
        Log auction result.
        
        Args:
            auction_result: Auction result to log
            source: Source component (e.g., "weave")
            
        Returns:
            Signed audit log entry
        """
        event_data = auction_result.dict()
        signature = self.signer.sign_data(event_data)
        
        audit_log = AuditLog(
            log_id=str(uuid.uuid4()),
            trace_id=auction_result.trace_id,
            event_type="auction_result",
            event_data=event_data,
            signature=signature,
            source=source
        )
        
        logger.info(f"Logged auction result {auction_result.auction_id} for trace {auction_result.trace_id}")
        return audit_log
    
    def log_processor_auth_result(
        self,
        auth_result: ProcessorAuthResult,
        source: str = "processor"
    ) -> AuditLog:
        """
        Log processor authorization result.
        
        Args:
            auth_result: Authorization result to log
            source: Source component (e.g., "processor")
            
        Returns:
            Signed audit log entry
        """
        event_data = auth_result.dict()
        signature = self.signer.sign_data(event_data)
        
        audit_log = AuditLog(
            log_id=str(uuid.uuid4()),
            trace_id=auth_result.auth_id,  # Use auth_id as trace_id for processor events
            event_type="processor_auth_result",
            event_data=event_data,
            signature=signature,
            source=source
        )
        
        logger.info(f"Logged processor auth result {auth_result.auth_id} from {auth_result.processor_id}")
        return audit_log
    
    def log_bid_broadcast(
        self,
        bid_requests: List[BidRequest],
        source: str = "weave"
    ) -> AuditLog:
        """
        Log bid request broadcast to processors.
        
        Args:
            bid_requests: Bid requests that were broadcast
            source: Source component (e.g., "weave")
            
        Returns:
            Signed audit log entry
        """
        event_data = {
            "bid_requests": [bid.dict() for bid in bid_requests],
            "processor_count": len(set(bid.processor_id for bid in bid_requests)),
            "total_bids": len(bid_requests)
        }
        signature = self.signer.sign_data(event_data)
        
        audit_log = AuditLog(
            log_id=str(uuid.uuid4()),
            trace_id=bid_requests[0].trace_id if bid_requests else "unknown",
            event_type="bid_broadcast",
            event_data=event_data,
            signature=signature,
            source=source
        )
        
        logger.info(f"Logged bid broadcast for {len(bid_requests)} requests")
        return audit_log
    
    def verify_audit_log(self, audit_log: AuditLog) -> bool:
        """
        Verify audit log signature and integrity.
        
        Args:
            audit_log: Audit log to verify
            
        Returns:
            True if audit log is valid, False otherwise
        """
        return self.signer.verify_signature(audit_log.event_data, audit_log.signature)


# Global instances
_digital_signer = None
_receipt_signer = None
_audit_logger = None


def get_digital_signer() -> DigitalSigner:
    """Get global digital signer instance."""
    global _digital_signer
    if _digital_signer is None:
        _digital_signer = DigitalSigner()
    return _digital_signer


def get_receipt_signer() -> ReceiptSigner:
    """Get global receipt signer instance."""
    global _receipt_signer
    if _receipt_signer is None:
        _receipt_signer = ReceiptSigner(get_digital_signer())
    return _receipt_signer


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(get_digital_signer())
    return _audit_logger
