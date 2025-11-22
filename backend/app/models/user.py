"""User model"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User account model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    # Default organization (for backward compatibility)
    # Users can belong to multiple organizations via organization_memberships
    default_organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Subscription tier (deprecated - now at organization level, kept for backward compatibility)
    tier = Column(String(50), default="starter", nullable=False)  # starter, pro, enterprise

    # Usage limits (deprecated - now at organization level, kept for backward compatibility)
    api_calls_remaining = Column(Integer, default=10000, nullable=False)
    api_calls_total = Column(Integer, default=10000, nullable=False)

    # Relationships
    default_organization = relationship("Organization", foreign_keys=[default_organization_id])
    organization_memberships = relationship("OrganizationMember", back_populates="user", foreign_keys="OrganizationMember.user_id", cascade="all, delete-orphan")
    workspace_memberships = relationship("WorkspaceMember", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"
