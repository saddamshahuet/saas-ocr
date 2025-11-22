"""Permission checking decorators and middleware"""
from typing import Optional, List, Callable
from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import User
from ..services.rbac_service import RBACService
from ..api.dependencies import get_current_user


def require_permission(
    permission: str,
    resource_type: Optional[str] = None,
    resource_id_param: Optional[str] = None,
):
    """Decorator to require a specific permission for an endpoint

    Usage:
        @router.get("/documents")
        @require_permission("read:documents")
        async def list_documents(...):
            ...

        @router.delete("/documents/{doc_id}")
        @require_permission("delete:documents", resource_type="document", resource_id_param="doc_id")
        async def delete_document(doc_id: int, ...):
            ...

    Args:
        permission: The permission name required (e.g., "read:documents")
        resource_type: Optional resource type for resource-level permissions
        resource_id_param: Optional parameter name containing the resource ID
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies from kwargs
            db: Session = kwargs.get("db")
            current_user: User = kwargs.get("current_user")
            organization_id: Optional[int] = kwargs.get("organization_id")
            workspace_id: Optional[int] = kwargs.get("workspace_id")

            if not db or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing required dependencies (db, current_user)",
                )

            # Get resource ID if specified
            resource_id = None
            if resource_id_param and resource_id_param in kwargs:
                resource_id = kwargs[resource_id_param]

            # Check permission
            has_permission = RBACService.user_has_permission(
                user=current_user,
                permission_name=permission,
                db=db,
                organization_id=organization_id,
                workspace_id=workspace_id,
                resource_type=resource_type,
                resource_id=resource_id,
            )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You do not have the required permission: {permission}",
                )

            # Call the original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(permissions: List[str]):
    """Decorator to require at least one of the specified permissions

    Usage:
        @require_any_permission(["read:documents", "write:documents"])
        async def access_documents(...):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: Session = kwargs.get("db")
            current_user: User = kwargs.get("current_user")
            organization_id: Optional[int] = kwargs.get("organization_id")
            workspace_id: Optional[int] = kwargs.get("workspace_id")

            if not db or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing required dependencies",
                )

            # Check if user has any of the permissions
            user_perms = RBACService.get_user_permissions(
                current_user, db, organization_id, workspace_id
            )

            has_any = any(perm in user_perms for perm in permissions)

            if not has_any:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You need at least one of these permissions: {', '.join(permissions)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(permissions: List[str]):
    """Decorator to require all of the specified permissions

    Usage:
        @require_all_permissions(["read:documents", "write:documents"])
        async def complex_operation(...):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            db: Session = kwargs.get("db")
            current_user: User = kwargs.get("current_user")
            organization_id: Optional[int] = kwargs.get("organization_id")
            workspace_id: Optional[int] = kwargs.get("workspace_id")

            if not db or not current_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Missing required dependencies",
                )

            # Check if user has all permissions
            user_perms = RBACService.get_user_permissions(
                current_user, db, organization_id, workspace_id
            )

            missing_perms = [perm for perm in permissions if perm not in user_perms]

            if missing_perms:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {', '.join(missing_perms)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class PermissionChecker:
    """Dependency class for checking permissions in FastAPI endpoints

    Usage:
        @router.get("/documents")
        async def list_documents(
            _: None = Depends(PermissionChecker("read:documents")),
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user),
        ):
            ...
    """

    def __init__(
        self,
        permission: str,
        resource_type: Optional[str] = None,
        organization_required: bool = True,
    ):
        self.permission = permission
        self.resource_type = resource_type
        self.organization_required = organization_required

    async def __call__(
        self,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        # Extract organization_id from path parameters or query
        organization_id = request.path_params.get("organization_id")
        if not organization_id and self.organization_required:
            # Try to get from user's default organization
            organization_id = current_user.default_organization_id

        # Extract workspace_id if present
        workspace_id = request.path_params.get("workspace_id")

        # Extract resource_id if present
        resource_id = None
        if self.resource_type:
            # Try common parameter names
            for param_name in ["id", f"{self.resource_type}_id", "resource_id"]:
                if param_name in request.path_params:
                    resource_id = request.path_params[param_name]
                    break

        # Check permission
        has_permission = RBACService.user_has_permission(
            user=current_user,
            permission_name=self.permission,
            db=db,
            organization_id=organization_id,
            workspace_id=workspace_id,
            resource_type=self.resource_type,
            resource_id=resource_id,
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have the required permission: {self.permission}",
            )

        return True


class PermissionMiddleware:
    """Middleware to add permission checking context to requests"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Add permission checking utilities to the request state
        # This can be used by endpoints to check permissions
        if "state" not in scope:
            scope["state"] = {}

        # Process the request
        await self.app(scope, receive, send)


def check_permission(
    user: User,
    permission: str,
    db: Session,
    organization_id: Optional[int] = None,
    workspace_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    raise_exception: bool = True,
) -> bool:
    """Helper function to check if a user has a permission

    Args:
        user: The user to check
        permission: Permission name
        db: Database session
        organization_id: Optional organization context
        workspace_id: Optional workspace context
        resource_type: Optional resource type
        resource_id: Optional resource ID
        raise_exception: If True, raise HTTPException if permission denied

    Returns:
        True if user has permission, False otherwise

    Raises:
        HTTPException: If raise_exception=True and permission is denied
    """
    has_permission = RBACService.user_has_permission(
        user=user,
        permission_name=permission,
        db=db,
        organization_id=organization_id,
        workspace_id=workspace_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    if not has_permission and raise_exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have the required permission: {permission}",
        )

    return has_permission
