"""API Key model"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class APIKey(Base, TimestampMixin):
    """API Key model for authentication"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # The key itself (hashed in production)
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    key_prefix = Column(String(16), nullable=False)  # First few chars for identification

    # Metadata
    name = Column(String(255), nullable=False)  # User-friendly name
    is_active = Column(Boolean, default=True, nullable=False)

    # Optional IP whitelisting
    allowed_ips = Column(String(1000), nullable=True)  # Comma-separated IPs

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")
    organization = relationship("Organization", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.key_prefix}... for user {self.user_id}>"
