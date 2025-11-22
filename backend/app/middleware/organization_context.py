"""Organization context middleware for tenant isolation

This middleware ensures that all requests are scoped to a specific organization,
providing multi-tenancy isolation at the application level.
"""
from typing import Optional
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from contextvars import ContextVar

# Context variable to store current organization ID for the request
current_organization_id: ContextVar[Optional[int]] = ContextVar("current_organization_id", default=None)
current_workspace_id: ContextVar[Optional[int]] = ContextVar("current_workspace_id", default=None)


def get_current_organization_id() -> Optional[int]:
    """Get the current organization ID from context"""
    return current_organization_id.get()


def get_current_workspace_id() -> Optional[int]:
    """Get the current workspace ID from context"""
    return current_workspace_id.get()


def set_organization_context(organization_id: Optional[int], workspace_id: Optional[int] = None):
    """Set the organization and workspace context for the current request"""
    current_organization_id.set(organization_id)
    current_workspace_id.set(workspace_id)


def clear_organization_context():
    """Clear the organization context"""
    current_organization_id.set(None)
    current_workspace_id.set(None)


class OrganizationContextMiddleware:
    """Middleware to set organization context from user or headers"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Clear any previous context
        clear_organization_context()

        # Process the request
        await self.app(scope, receive, send)

        # Clear context after request
        clear_organization_context()


def get_user_organization(user, organization_id: Optional[int] = None, db: Session = None):
    """Get the organization for the current user

    Args:
        user: The authenticated user object
        organization_id: Optional specific organization ID to use
        db: Database session (required if organization_id is provided)

    Returns:
        The organization ID to use for the request

    Raises:
        HTTPException: If the user doesn't have access to the requested organization
    """
    from ..models import OrganizationMember

    # If organization_id is explicitly provided, verify user has access
    if organization_id is not None:
        if db is None:
            raise ValueError("Database session required when organization_id is provided")

        # Check if user is a member of this organization
        membership = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active == True,
            )
            .first()
        )

        if not membership and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization",
            )

        return organization_id

    # Otherwise, use the user's default organization
    if user.default_organization_id:
        return user.default_organization_id

    # If no default, try to get first active organization membership
    if db:
        first_membership = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == user.id,
                OrganizationMember.is_active == True,
            )
            .first()
        )
        if first_membership:
            return first_membership.organization_id

    # User has no organization (might be newly created)
    return None


def verify_organization_access(user, organization_id: int, db: Session, required_role: Optional[str] = None):
    """Verify that a user has access to an organization and optionally check their role

    Args:
        user: The authenticated user
        organization_id: The organization to check access for
        db: Database session
        required_role: Optional role requirement (owner, admin, manager, member, viewer)

    Returns:
        OrganizationMember: The membership record if access is granted

    Raises:
        HTTPException: If access is denied
    """
    from ..models import OrganizationMember

    # Superusers have access to everything
    if user.is_superuser:
        # Create a fake membership for superusers
        class SuperuserMembership:
            role = "owner"
            organization_id = organization_id
            is_active = True

        return SuperuserMembership()

    # Check membership
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization",
        )

    # Check role if required
    if required_role:
        role_hierarchy = {
            "owner": 5,
            "admin": 4,
            "manager": 3,
            "member": 2,
            "viewer": 1,
        }

        user_role_level = role_hierarchy.get(membership.role, 0)
        required_role_level = role_hierarchy.get(required_role, 0)

        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires {required_role} role or higher",
            )

    return membership


def verify_workspace_access(user, workspace_id: int, db: Session, required_role: Optional[str] = None):
    """Verify that a user has access to a workspace

    Args:
        user: The authenticated user
        workspace_id: The workspace to check access for
        db: Database session
        required_role: Optional role requirement (manager, member, viewer)

    Returns:
        WorkspaceMember: The membership record if access is granted

    Raises:
        HTTPException: If access is denied
    """
    from ..models import WorkspaceMember, Workspace, OrganizationMember

    # Get the workspace
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Superusers have access to everything
    if user.is_superuser:
        class SuperuserMembership:
            role = "manager"
            workspace_id = workspace_id
            is_active = True

        return SuperuserMembership()

    # Organization owners and admins have access to all workspaces in their org
    org_membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == workspace.organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if org_membership and org_membership.role in ["owner", "admin"]:
        class OrgAdminMembership:
            role = "manager"
            workspace_id = workspace_id
            is_active = True

        return OrgAdminMembership()

    # Check workspace membership
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.is_active == True,
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace",
        )

    # Check role if required
    if required_role:
        role_hierarchy = {
            "manager": 3,
            "member": 2,
            "viewer": 1,
        }

        user_role_level = role_hierarchy.get(membership.role, 0)
        required_role_level = role_hierarchy.get(required_role, 0)

        if user_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires {required_role} role or higher in this workspace",
            )

    return membership
