"""RBAC Service for role and permission management"""
from typing import List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status
import json

from ..models import (
    User,
    Permission,
    Role,
    ResourcePermission,
    AuditPermission,
    Organization,
    OrganizationMember,
    WorkspaceMember,
    user_roles,
)


class RBACService:
    """Service for managing roles, permissions, and access control"""

    # Define system permissions
    SYSTEM_PERMISSIONS = [
        # Document permissions
        {"name": "read:documents", "resource": "documents", "action": "read", "scope": "organization"},
        {"name": "write:documents", "resource": "documents", "action": "write", "scope": "organization"},
        {"name": "delete:documents", "resource": "documents", "action": "delete", "scope": "organization"},
        {"name": "manage:documents", "resource": "documents", "action": "manage", "scope": "organization"},

        # Job permissions
        {"name": "read:jobs", "resource": "jobs", "action": "read", "scope": "organization"},
        {"name": "write:jobs", "resource": "jobs", "action": "write", "scope": "organization"},
        {"name": "delete:jobs", "resource": "jobs", "action": "delete", "scope": "organization"},
        {"name": "manage:jobs", "resource": "jobs", "action": "manage", "scope": "organization"},

        # User permissions
        {"name": "read:users", "resource": "users", "action": "read", "scope": "organization"},
        {"name": "write:users", "resource": "users", "action": "write", "scope": "organization"},
        {"name": "delete:users", "resource": "users", "action": "delete", "scope": "organization"},
        {"name": "manage:users", "resource": "users", "action": "manage", "scope": "organization"},

        # Organization permissions
        {"name": "read:organization", "resource": "organization", "action": "read", "scope": "organization"},
        {"name": "write:organization", "resource": "organization", "action": "write", "scope": "organization"},
        {"name": "manage:organization", "resource": "organization", "action": "manage", "scope": "organization"},

        # Workspace permissions
        {"name": "read:workspaces", "resource": "workspaces", "action": "read", "scope": "organization"},
        {"name": "write:workspaces", "resource": "workspaces", "action": "write", "scope": "organization"},
        {"name": "delete:workspaces", "resource": "workspaces", "action": "delete", "scope": "organization"},
        {"name": "manage:workspaces", "resource": "workspaces", "action": "manage", "scope": "organization"},

        # API Key permissions
        {"name": "read:api_keys", "resource": "api_keys", "action": "read", "scope": "organization"},
        {"name": "write:api_keys", "resource": "api_keys", "action": "write", "scope": "organization"},
        {"name": "delete:api_keys", "resource": "api_keys", "action": "delete", "scope": "organization"},

        # Schema permissions
        {"name": "read:schemas", "resource": "schemas", "action": "read", "scope": "organization"},
        {"name": "write:schemas", "resource": "schemas", "action": "write", "scope": "organization"},
        {"name": "delete:schemas", "resource": "schemas", "action": "delete", "scope": "organization"},

        # Analytics permissions
        {"name": "read:analytics", "resource": "analytics", "action": "read", "scope": "organization"},

        # Billing permissions
        {"name": "read:billing", "resource": "billing", "action": "read", "scope": "organization"},
        {"name": "manage:billing", "resource": "billing", "action": "manage", "scope": "organization"},

        # Role permissions
        {"name": "read:roles", "resource": "roles", "action": "read", "scope": "organization"},
        {"name": "write:roles", "resource": "roles", "action": "write", "scope": "organization"},
        {"name": "delete:roles", "resource": "roles", "action": "delete", "scope": "organization"},
        {"name": "manage:roles", "resource": "roles", "action": "manage", "scope": "organization"},
    ]

    # Define system roles with their permissions
    SYSTEM_ROLES = {
        "Owner": {
            "description": "Full access to all resources and settings",
            "priority": 100,
            "permissions": ["*"],  # All permissions
        },
        "Admin": {
            "description": "Administrative access to most resources",
            "priority": 90,
            "permissions": [
                "manage:organization", "manage:users", "manage:workspaces",
                "manage:documents", "manage:jobs", "manage:schemas",
                "read:analytics", "read:billing", "manage:roles",
            ],
        },
        "Manager": {
            "description": "Manage day-to-day operations",
            "priority": 70,
            "permissions": [
                "read:organization", "read:users", "write:workspaces",
                "manage:documents", "manage:jobs", "write:schemas",
                "read:analytics",
            ],
        },
        "Member": {
            "description": "Standard access to create and manage own resources",
            "priority": 50,
            "permissions": [
                "read:organization", "read:users",
                "write:documents", "write:jobs", "write:schemas",
                "read:api_keys", "write:api_keys", "delete:api_keys",
            ],
        },
        "Viewer": {
            "description": "Read-only access to resources",
            "priority": 30,
            "permissions": [
                "read:organization", "read:users", "read:workspaces",
                "read:documents", "read:jobs", "read:schemas",
            ],
        },
        "Auditor": {
            "description": "Read-only access with focus on compliance",
            "priority": 40,
            "permissions": [
                "read:organization", "read:users", "read:workspaces",
                "read:documents", "read:jobs", "read:analytics",
                "read:billing",
            ],
        },
    }

    @staticmethod
    def initialize_permissions(db: Session):
        """Initialize system permissions in the database"""
        created_count = 0

        for perm_data in RBACService.SYSTEM_PERMISSIONS:
            # Check if permission already exists
            existing = db.query(Permission).filter(Permission.name == perm_data["name"]).first()

            if not existing:
                permission = Permission(
                    name=perm_data["name"],
                    resource=perm_data["resource"],
                    action=perm_data["action"],
                    scope=perm_data.get("scope", "organization"),
                    is_system=True,
                    description=f"{perm_data['action'].title()} access to {perm_data['resource']}",
                )
                db.add(permission)
                created_count += 1

        db.commit()
        return created_count

    @staticmethod
    def initialize_roles(db: Session, organization_id: Optional[int] = None):
        """Initialize system roles for an organization or globally

        Args:
            db: Database session
            organization_id: If provided, create organization-specific roles
        """
        created_count = 0

        for role_name, role_config in RBACService.SYSTEM_ROLES.items():
            # Check if role already exists
            query = db.query(Role).filter(Role.name == role_name)
            if organization_id:
                query = query.filter(Role.organization_id == organization_id)
            else:
                query = query.filter(Role.organization_id.is_(None))

            existing = query.first()

            if not existing:
                # Get permissions
                permission_names = role_config["permissions"]
                permissions = []

                if "*" in permission_names:
                    # Grant all permissions
                    permissions = db.query(Permission).filter(Permission.is_system == True).all()
                else:
                    # Grant specific permissions
                    permissions = (
                        db.query(Permission)
                        .filter(Permission.name.in_(permission_names))
                        .all()
                    )

                # Create role
                role = Role(
                    name=role_name,
                    description=role_config["description"],
                    organization_id=organization_id,
                    role_type="system" if organization_id is None else "organization",
                    is_system=True,
                    priority=role_config["priority"],
                    permissions=permissions,
                )

                db.add(role)
                created_count += 1

        db.commit()
        return created_count

    @staticmethod
    def get_user_permissions(
        user: User,
        db: Session,
        organization_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
    ) -> Set[str]:
        """Get all permissions for a user in a given context

        Args:
            user: The user to get permissions for
            db: Database session
            organization_id: Optional organization context
            workspace_id: Optional workspace context

        Returns:
            Set of permission names the user has
        """
        permissions = set()

        # Superusers have all permissions
        if user.is_superuser:
            all_perms = db.query(Permission).all()
            return {perm.name for perm in all_perms}

        # Get permissions from organization roles
        if organization_id:
            # Get user's roles in this organization through user_roles table
            user_role_ids = (
                db.query(user_roles.c.role_id)
                .filter(
                    user_roles.c.user_id == user.id,
                    user_roles.c.organization_id == organization_id,
                )
                .all()
            )

            role_ids = [r[0] for r in user_role_ids]

            if role_ids:
                roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
                for role in roles:
                    permissions.update({perm.name for perm in role.permissions})

        # Get permissions from workspace roles
        if workspace_id:
            user_role_ids = (
                db.query(user_roles.c.role_id)
                .filter(
                    user_roles.c.user_id == user.id,
                    user_roles.c.workspace_id == workspace_id,
                )
                .all()
            )

            role_ids = [r[0] for r in user_role_ids]

            if role_ids:
                roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
                for role in roles:
                    permissions.update({perm.name for perm in role.permissions})

        # Get resource-specific permissions
        resource_perms = (
            db.query(ResourcePermission)
            .join(Permission)
            .filter(
                ResourcePermission.user_id == user.id,
                ResourcePermission.is_active == True,
            )
        )

        if organization_id:
            resource_perms = resource_perms.filter(
                or_(
                    ResourcePermission.organization_id == organization_id,
                    ResourcePermission.organization_id.is_(None),
                )
            )

        for rp in resource_perms.all():
            permissions.add(rp.permission.name)

        return permissions

    @staticmethod
    def user_has_permission(
        user: User,
        permission_name: str,
        db: Session,
        organization_id: Optional[int] = None,
        workspace_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
    ) -> bool:
        """Check if a user has a specific permission

        Args:
            user: The user to check
            permission_name: Name of the permission (e.g., "read:documents")
            db: Database session
            organization_id: Optional organization context
            workspace_id: Optional workspace context
            resource_type: Optional specific resource type
            resource_id: Optional specific resource ID

        Returns:
            True if user has the permission, False otherwise
        """
        # Superusers have all permissions
        if user.is_superuser:
            return True

        # Check resource-specific permission first
        if resource_type and resource_id:
            resource_perm = (
                db.query(ResourcePermission)
                .join(Permission)
                .filter(
                    ResourcePermission.user_id == user.id,
                    Permission.name == permission_name,
                    ResourcePermission.resource_type == resource_type,
                    ResourcePermission.resource_id == resource_id,
                    ResourcePermission.is_active == True,
                )
                .first()
            )

            if resource_perm:
                return True

        # Check role-based permissions
        user_permissions = RBACService.get_user_permissions(
            user, db, organization_id, workspace_id
        )

        return permission_name in user_permissions

    @staticmethod
    def assign_role_to_user(
        user_id: int,
        role_id: int,
        organization_id: int,
        db: Session,
        workspace_id: Optional[int] = None,
        assigned_by_id: Optional[int] = None,
    ):
        """Assign a role to a user within an organization/workspace context"""
        # Check if user is member of organization
        org_member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == user_id,
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.is_active == True,
            )
            .first()
        )

        if not org_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not a member of this organization",
            )

        # Check if role exists
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found",
            )

        # Check if assignment already exists
        existing = (
            db.query(user_roles)
            .filter(
                user_roles.c.user_id == user_id,
                user_roles.c.role_id == role_id,
                user_roles.c.organization_id == organization_id,
            )
        )

        if workspace_id:
            existing = existing.filter(user_roles.c.workspace_id == workspace_id)

        if existing.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has this role",
            )

        # Create assignment
        insert_stmt = user_roles.insert().values(
            user_id=user_id,
            role_id=role_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
        )

        db.execute(insert_stmt)

        # Create audit log
        audit = AuditPermission(
            user_id=user_id,
            organization_id=organization_id,
            action="assign_role",
            role_id=role_id,
            target_user_id=user_id,
            performed_by_id=assigned_by_id,
            details=json.dumps({
                "role_name": role.name,
                "workspace_id": workspace_id,
            }),
        )
        db.add(audit)

        db.commit()

    @staticmethod
    def revoke_role_from_user(
        user_id: int,
        role_id: int,
        organization_id: int,
        db: Session,
        workspace_id: Optional[int] = None,
        revoked_by_id: Optional[int] = None,
    ):
        """Revoke a role from a user"""
        # Find and delete the assignment
        delete_stmt = (
            user_roles.delete()
            .where(
                and_(
                    user_roles.c.user_id == user_id,
                    user_roles.c.role_id == role_id,
                    user_roles.c.organization_id == organization_id,
                )
            )
        )

        if workspace_id:
            delete_stmt = delete_stmt.where(user_roles.c.workspace_id == workspace_id)

        result = db.execute(delete_stmt)

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role assignment not found",
            )

        # Create audit log
        role = db.query(Role).filter(Role.id == role_id).first()
        audit = AuditPermission(
            user_id=user_id,
            organization_id=organization_id,
            action="revoke_role",
            role_id=role_id,
            target_user_id=user_id,
            performed_by_id=revoked_by_id,
            details=json.dumps({
                "role_name": role.name if role else None,
                "workspace_id": workspace_id,
            }),
        )
        db.add(audit)

        db.commit()

    @staticmethod
    def grant_resource_permission(
        user_id: int,
        permission_name: str,
        resource_type: str,
        resource_id: int,
        organization_id: int,
        db: Session,
        workspace_id: Optional[int] = None,
        granted_by_id: Optional[int] = None,
    ):
        """Grant a specific permission on a resource to a user"""
        # Get permission
        permission = db.query(Permission).filter(Permission.name == permission_name).first()
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Permission '{permission_name}' not found",
            )

        # Check if already granted
        existing = (
            db.query(ResourcePermission)
            .filter(
                ResourcePermission.user_id == user_id,
                ResourcePermission.permission_id == permission.id,
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id,
            )
            .first()
        )

        if existing:
            if existing.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Permission already granted",
                )
            else:
                # Reactivate
                existing.is_active = True
                db.commit()
                return existing

        # Create resource permission
        resource_perm = ResourcePermission(
            user_id=user_id,
            permission_id=permission.id,
            resource_type=resource_type,
            resource_id=resource_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            granted_by_id=granted_by_id,
        )

        db.add(resource_perm)
        db.commit()
        db.refresh(resource_perm)

        return resource_perm
