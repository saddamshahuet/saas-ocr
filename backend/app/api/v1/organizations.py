"""Organization management API endpoints"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import re

from ...core.database import get_db
from ...models import (
    User,
    Organization,
    OrganizationMember,
    Workspace,
    WorkspaceMember,
)
from ...schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationListResponse,
    OrganizationMemberCreate,
    OrganizationMemberUpdate,
    OrganizationMemberResponse,
    MemberListResponse,
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
    WorkspaceListResponse,
    WorkspaceMemberCreate,
    WorkspaceMemberUpdate,
    WorkspaceMemberResponse,
)
from ...api.dependencies import get_current_user
from ...middleware import (
    verify_organization_access,
    verify_workspace_access,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name"""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')
    return slug


# ==================== Organization Endpoints ====================

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new organization

    The current user will be added as the owner of the organization.
    """
    # Generate slug if not provided
    slug = org_data.slug or generate_slug(org_data.name)

    # Check if slug already exists
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with slug '{slug}' already exists",
        )

    # Create organization
    organization = Organization(
        name=org_data.name,
        slug=slug,
        description=org_data.description,
        contact_email=org_data.contact_email or current_user.email,
        contact_phone=org_data.contact_phone,
        website=org_data.website,
        tier=org_data.tier or "starter",
    )

    db.add(organization)
    db.flush()  # Get the organization ID

    # Add current user as owner
    membership = OrganizationMember(
        organization_id=organization.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(membership)

    # Set as user's default organization if they don't have one
    if not current_user.default_organization_id:
        current_user.default_organization_id = organization.id

    # Create default workspace
    default_workspace = Workspace(
        organization_id=organization.id,
        name="Default",
        slug="default",
        description="Default workspace for the organization",
        is_default=True,
    )
    db.add(default_workspace)
    db.flush()

    # Add owner to default workspace
    workspace_member = WorkspaceMember(
        workspace_id=default_workspace.id,
        user_id=current_user.id,
        role="manager",
    )
    db.add(workspace_member)

    db.commit()
    db.refresh(organization)

    # Add counts
    organization.member_count = 1
    organization.workspace_count = 1

    return organization


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all organizations the current user has access to"""
    # Get organizations where user is a member
    query = (
        db.query(Organization)
        .join(OrganizationMember)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
        .order_by(Organization.name)
    )

    total = query.count()
    organizations = query.offset((page - 1) * page_size).limit(page_size).all()

    # Add member and workspace counts
    for org in organizations:
        org.member_count = (
            db.query(func.count(OrganizationMember.id))
            .filter(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.is_active == True,
            )
            .scalar()
        )
        org.workspace_count = (
            db.query(func.count(Workspace.id))
            .filter(Workspace.organization_id == org.id)
            .scalar()
        )

    return OrganizationListResponse(
        organizations=organizations,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific organization"""
    # Verify access
    verify_organization_access(current_user, organization_id, db)

    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Add counts
    organization.member_count = (
        db.query(func.count(OrganizationMember.id))
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,
        )
        .scalar()
    )
    organization.workspace_count = (
        db.query(func.count(Workspace.id))
        .filter(Workspace.organization_id == organization_id)
        .scalar()
    )

    return organization


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: int,
    org_data: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an organization (requires admin or owner role)"""
    # Verify access with required role
    verify_organization_access(current_user, organization_id, db, required_role="admin")

    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Update fields
    update_data = org_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)

    db.commit()
    db.refresh(organization)

    return organization


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an organization (requires owner role)"""
    # Verify access with owner role
    verify_organization_access(current_user, organization_id, db, required_role="owner")

    organization = db.query(Organization).filter(Organization.id == organization_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Delete organization (cascade will handle members, workspaces, etc.)
    db.delete(organization)
    db.commit()

    return None


# ==================== Organization Member Endpoints ====================

@router.get("/{organization_id}/members", response_model=MemberListResponse)
async def list_organization_members(
    organization_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all members of an organization"""
    # Verify access
    verify_organization_access(current_user, organization_id, db)

    query = (
        db.query(OrganizationMember)
        .join(User)
        .filter(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.created_at)
    )

    total = query.count()
    members = query.offset((page - 1) * page_size).limit(page_size).all()

    # Enrich with user data
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            member.user_email = user.email
            member.user_name = user.full_name

    return MemberListResponse(
        members=members,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{organization_id}/members", response_model=OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    organization_id: int,
    member_data: OrganizationMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member to an organization (requires admin or owner role)"""
    # Verify access
    verify_organization_access(current_user, organization_id, db, required_role="admin")

    # Find user by email
    user = db.query(User).filter(User.email == member_data.user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{member_data.user_email}' not found",
        )

    # Check if already a member
    existing = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization",
            )
        else:
            # Reactivate membership
            existing.is_active = True
            existing.role = member_data.role
            db.commit()
            db.refresh(existing)
            return existing

    # Create membership
    membership = OrganizationMember(
        organization_id=organization_id,
        user_id=user.id,
        role=member_data.role,
        invited_by_id=current_user.id,
    )

    db.add(membership)
    db.commit()
    db.refresh(membership)

    membership.user_email = user.email
    membership.user_name = user.full_name

    return membership


@router.patch("/{organization_id}/members/{member_id}", response_model=OrganizationMemberResponse)
async def update_organization_member(
    organization_id: int,
    member_id: int,
    member_data: OrganizationMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an organization member (requires admin or owner role)"""
    # Verify access
    verify_organization_access(current_user, organization_id, db, required_role="admin")

    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == organization_id,
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Update fields
    update_data = member_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(membership, field, value)

    db.commit()
    db.refresh(membership)

    return membership


@router.delete("/{organization_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    organization_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from an organization (requires admin or owner role)"""
    # Verify access
    verify_organization_access(current_user, organization_id, db, required_role="admin")

    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == organization_id,
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Don't allow removing the last owner
    if membership.role == "owner":
        owner_count = (
            db.query(func.count(OrganizationMember.id))
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == "owner",
                OrganizationMember.is_active == True,
            )
            .scalar()
        )

        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner of an organization",
            )

    # Soft delete by deactivating
    membership.is_active = False
    db.commit()

    return None


# ==================== Workspace Endpoints ====================

@router.post("/{organization_id}/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    organization_id: int,
    workspace_data: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workspace in an organization"""
    # Verify access
    verify_organization_access(current_user, organization_id, db, required_role="admin")

    # Generate slug
    slug = workspace_data.slug or generate_slug(workspace_data.name)

    # Check if slug exists in this organization
    existing = (
        db.query(Workspace)
        .filter(
            Workspace.organization_id == organization_id,
            Workspace.slug == slug,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace with slug '{slug}' already exists in this organization",
        )

    # Create workspace
    workspace = Workspace(
        organization_id=organization_id,
        name=workspace_data.name,
        slug=slug,
        description=workspace_data.description,
        is_default=workspace_data.is_default,
    )

    db.add(workspace)
    db.flush()

    # Add current user as manager
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role="manager",
    )
    db.add(member)

    db.commit()
    db.refresh(workspace)

    workspace.member_count = 1

    return workspace


@router.get("/{organization_id}/workspaces", response_model=WorkspaceListResponse)
async def list_workspaces(
    organization_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all workspaces in an organization"""
    # Verify access
    verify_organization_access(current_user, organization_id, db)

    query = (
        db.query(Workspace)
        .filter(Workspace.organization_id == organization_id)
        .order_by(Workspace.is_default.desc(), Workspace.name)
    )

    total = query.count()
    workspaces = query.offset((page - 1) * page_size).limit(page_size).all()

    # Add member counts
    for workspace in workspaces:
        workspace.member_count = (
            db.query(func.count(WorkspaceMember.id))
            .filter(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.is_active == True,
            )
            .scalar()
        )

    return WorkspaceListResponse(
        workspaces=workspaces,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{organization_id}/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    organization_id: int,
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific workspace"""
    # Verify workspace access
    verify_workspace_access(current_user, workspace_id, db)

    workspace = (
        db.query(Workspace)
        .filter(
            Workspace.id == workspace_id,
            Workspace.organization_id == organization_id,
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    workspace.member_count = (
        db.query(func.count(WorkspaceMember.id))
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.is_active == True,
        )
        .scalar()
    )

    return workspace


@router.patch("/{organization_id}/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    organization_id: int,
    workspace_id: int,
    workspace_data: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a workspace (requires manager role in workspace or admin role in organization)"""
    # Check if user is org admin or workspace manager
    try:
        verify_workspace_access(current_user, workspace_id, db, required_role="manager")
    except HTTPException:
        # Fallback to org admin check
        verify_organization_access(current_user, organization_id, db, required_role="admin")

    workspace = (
        db.query(Workspace)
        .filter(
            Workspace.id == workspace_id,
            Workspace.organization_id == organization_id,
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Update fields
    update_data = workspace_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workspace, field, value)

    db.commit()
    db.refresh(workspace)

    return workspace


@router.delete("/{organization_id}/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    organization_id: int,
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a workspace (requires admin role in organization)"""
    # Verify org admin access
    verify_organization_access(current_user, organization_id, db, required_role="admin")

    workspace = (
        db.query(Workspace)
        .filter(
            Workspace.id == workspace_id,
            Workspace.organization_id == organization_id,
        )
        .first()
    )

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # Don't allow deleting the default workspace
    if workspace.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the default workspace",
        )

    db.delete(workspace)
    db.commit()

    return None


# ==================== Workspace Member Endpoints ====================

@router.post("/{organization_id}/workspaces/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    organization_id: int,
    workspace_id: int,
    member_data: WorkspaceMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member to a workspace"""
    # Verify workspace access
    verify_workspace_access(current_user, workspace_id, db, required_role="manager")

    # Find user
    user = db.query(User).filter(User.email == member_data.user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{member_data.user_email}' not found",
        )

    # Check if user is member of organization
    org_membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if not org_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be a member of the organization first",
        )

    # Check if already a member
    existing = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
        .first()
    )

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this workspace",
            )
        else:
            existing.is_active = True
            existing.role = member_data.role
            db.commit()
            db.refresh(existing)
            return existing

    # Create membership
    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user.id,
        role=member_data.role,
    )

    db.add(membership)
    db.commit()
    db.refresh(membership)

    membership.user_email = user.email
    membership.user_name = user.full_name

    return membership


@router.delete("/{organization_id}/workspaces/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    organization_id: int,
    workspace_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a workspace"""
    # Verify workspace access
    verify_workspace_access(current_user, workspace_id, db, required_role="manager")

    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.id == member_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    # Soft delete
    membership.is_active = False
    db.commit()

    return None
