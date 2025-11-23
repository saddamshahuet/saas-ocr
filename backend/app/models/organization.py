"""Organization and Workspace models for multi-tenancy"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    """Organization model for multi-tenancy

    An organization represents a company or entity that uses the platform.
    Each organization has its own isolated data, users, and settings.
    """
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text, nullable=True)

    # Organization settings
    is_active = Column(Boolean, default=True, nullable=False)
    tier = Column(String(50), default="starter", nullable=False)  # starter, pro, enterprise

    # Contact information
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)

    # Billing information
    billing_email = Column(String(255), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)

    # Usage limits (organization-level)
    api_calls_limit = Column(Integer, default=10000, nullable=False)
    api_calls_used = Column(Integer, default=0, nullable=False)
    storage_limit_gb = Column(Integer, default=10, nullable=False)  # Storage limit in GB
    storage_used_gb = Column(Integer, default=0, nullable=False)

    # Data residency (to be used in Phase 3)
    region = Column(String(50), default="us-east-1", nullable=False)  # us-east-1, eu-west-1, etc.

    # Custom settings (JSON field for extensibility)
    settings = Column(JSON, nullable=True, default={})

    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="organization", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan")
    schema_templates = relationship("SchemaTemplate", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.name} ({self.slug})>"


class OrganizationMember(Base, TimestampMixin):
    """Association table for Organization <-> User relationship with roles

    This table tracks which users belong to which organizations and their role
    within that organization.
    """
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Role within the organization (will be enhanced with RBAC)
    role = Column(String(50), default="member", nullable=False)  # owner, admin, manager, member, viewer

    # Member status
    is_active = Column(Boolean, default=True, nullable=False)
    invited_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], back_populates="organization_memberships")
    invited_by = relationship("User", foreign_keys=[invited_by_id])

    def __repr__(self):
        return f"<OrganizationMember org={self.organization_id} user={self.user_id} role={self.role}>"


class Workspace(Base, TimestampMixin):
    """Workspace model for team/project organization within an organization

    Workspaces allow organizations to segment their work into different teams,
    projects, or departments. Each workspace can have its own members and settings.
    """
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Workspace settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)  # Default workspace for new members

    # Custom settings
    settings = Column(JSON, nullable=True, default={})

    # Relationships
    organization = relationship("Organization", back_populates="workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace {self.name} in org={self.organization_id}>"


class WorkspaceMember(Base, TimestampMixin):
    """Association table for Workspace <-> User relationship

    Tracks which users have access to which workspaces within an organization.
    """
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Role within the workspace (will be enhanced with RBAC)
    role = Column(String(50), default="member", nullable=False)  # manager, member, viewer

    # Member status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")

    def __repr__(self):
        return f"<WorkspaceMember workspace={self.workspace_id} user={self.user_id}>"
