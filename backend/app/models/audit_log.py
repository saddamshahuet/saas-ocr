"""Audit Log model for HIPAA compliance"""
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, Text
from datetime import datetime
from .base import Base


class AuditLog(Base):
    """Audit log for tracking all data access and modifications"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # User information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_email = Column(String(255), nullable=True)
    api_key_id = Column(Integer, nullable=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # e.g., "document_upload", "data_access"
    resource_type = Column(String(100), nullable=False)  # e.g., "job", "document", "user"
    resource_id = Column(String(100), nullable=True)

    # Request details
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, etc.
    request_path = Column(String(500), nullable=True)

    # Additional metadata
    metadata = Column(JSON, nullable=True)

    # Result
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AuditLog {self.action} by user {self.user_id} at {self.timestamp}>"
