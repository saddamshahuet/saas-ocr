"""Role-Based Access Control (RBAC) models"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Table
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


# Association table for Role <-> Permission many-to-many relationship
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
)


# Association table for User <-> Role many-to-many relationship (organization-scoped)
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE')),
    Column('organization_id', Integer, ForeignKey('organizations.id', ondelete='CASCADE')),
    Column('workspace_id', Integer, ForeignKey('workspaces.id', ondelete='SET NULL'), nullable=True),
)


class Permission(Base, TimestampMixin):
    """Permission model for fine-grained access control

    Permissions define specific actions that can be performed on resources.
    Examples: read:documents, write:documents, delete:jobs, manage:users
    """
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "read:documents"
    description = Column(Text, nullable=True)

    # Permission categorization
    resource = Column(String(50), nullable=False, index=True)  # e.g., "documents", "jobs", "users"
    action = Column(String(50), nullable=False, index=True)  # e.g., "read", "write", "delete", "manage"

    # Permission scope
    scope = Column(String(50), default="organization", nullable=False)  # organization, workspace, user

    # System permission (cannot be deleted)
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission {self.name}>"


class Role(Base, TimestampMixin):
    """Role model for grouping permissions

    Roles are collections of permissions that can be assigned to users.
    Roles can be system-defined (e.g., Admin, Viewer) or custom.
    """
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Organization-specific roles (NULL means system-wide role)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # Role categorization
    role_type = Column(String(50), default="custom", nullable=False)  # system, organization, workspace, custom

    # System role (cannot be deleted or modified)
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Priority level (higher = more powerful, for conflict resolution)
    priority = Column(Integer, default=0, nullable=False)

    # Relationships
    organization = relationship("Organization")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    def __repr__(self):
        return f"<Role {self.name}>"


class ResourcePermission(Base, TimestampMixin):
    """Resource-level permissions for fine-grained access control

    This table allows for instance-level permissions, where a user can have
    specific permissions on a particular resource (e.g., can edit job #123).
    """
    __tablename__ = "resource_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Resource identification
    resource_type = Column(String(50), nullable=False, index=True)  # e.g., "job", "document", "schema_template"
    resource_id = Column(Integer, nullable=False, index=True)  # ID of the specific resource

    # Context
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)

    # Grant details
    granted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Expiration (optional)
    expires_at = Column(Integer, nullable=True)  # Unix timestamp

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    permission = relationship("Permission")
    granted_by = relationship("User", foreign_keys=[granted_by_id])
    organization = relationship("Organization")
    workspace = relationship("Workspace")

    def __repr__(self):
        return f"<ResourcePermission user={self.user_id} perm={self.permission_id} resource={self.resource_type}:{self.resource_id}>"


class AuditPermission(Base, TimestampMixin):
    """Audit log for permission changes

    Tracks all permission grants, revocations, and role changes for compliance.
    """
    __tablename__ = "audit_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # Action details
    action = Column(String(50), nullable=False, index=True)  # grant_role, revoke_role, grant_permission, etc.
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)

    # What was changed
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="SET NULL"), nullable=True)
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Metadata
    details = Column(Text, nullable=True)  # JSON string with additional details
    performed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization")
    role = relationship("Role")
    permission = relationship("Permission")
    target_user = relationship("User", foreign_keys=[target_user_id])
    performed_by = relationship("User", foreign_keys=[performed_by_id])

    def __repr__(self):
        return f"<AuditPermission {self.action} by user={self.performed_by_id}>"
