"""Organization schemas for request/response validation"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re


# ==================== Organization Schemas ====================

class OrganizationBase(BaseModel):
    """Base organization schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    description: Optional[str] = Field(None, description="Organization description")
    contact_email: Optional[str] = Field(None, description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    website: Optional[str] = Field(None, description="Organization website")


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization"""
    slug: Optional[str] = Field(None, min_length=3, max_length=100, description="URL-friendly identifier")
    tier: Optional[str] = Field("starter", description="Subscription tier")

    @validator("slug")
    def validate_slug(cls, v):
        if v is not None:
            if not re.match(r"^[a-z0-9-]+$", v):
                raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    billing_email: Optional[str] = None
    tier: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response"""
    id: int
    slug: str
    is_active: bool
    tier: str
    api_calls_limit: int
    api_calls_used: int
    storage_limit_gb: int
    storage_used_gb: int
    region: str
    settings: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = 0
    workspace_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ==================== Organization Member Schemas ====================

class OrganizationMemberBase(BaseModel):
    """Base organization member schema"""
    role: str = Field("member", description="Role within organization")


class OrganizationMemberCreate(OrganizationMemberBase):
    """Schema for adding a member to an organization"""
    user_email: str = Field(..., description="Email of user to add")


class OrganizationMemberUpdate(BaseModel):
    """Schema for updating an organization member"""
    role: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationMemberResponse(OrganizationMemberBase):
    """Schema for organization member response"""
    id: int
    organization_id: int
    user_id: int
    is_active: bool
    created_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Workspace Schemas ====================

class WorkspaceBase(BaseModel):
    """Base workspace schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")
    description: Optional[str] = Field(None, description="Workspace description")


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a workspace"""
    slug: Optional[str] = Field(None, min_length=3, max_length=100, description="URL-friendly identifier")
    is_default: Optional[bool] = Field(False, description="Make this the default workspace")

    @validator("slug")
    def validate_slug(cls, v):
        if v is not None:
            if not re.match(r"^[a-z0-9-]+$", v):
                raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class WorkspaceUpdate(BaseModel):
    """Schema for updating a workspace"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class WorkspaceResponse(WorkspaceBase):
    """Schema for workspace response"""
    id: int
    organization_id: int
    slug: str
    is_active: bool
    is_default: bool
    settings: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ==================== Workspace Member Schemas ====================

class WorkspaceMemberCreate(BaseModel):
    """Schema for adding a member to a workspace"""
    user_email: str = Field(..., description="Email of user to add")
    role: str = Field("member", description="Role within workspace")


class WorkspaceMemberUpdate(BaseModel):
    """Schema for updating a workspace member"""
    role: Optional[str] = None
    is_active: Optional[bool] = None


class WorkspaceMemberResponse(BaseModel):
    """Schema for workspace member response"""
    id: int
    workspace_id: int
    user_id: int
    role: str
    is_active: bool
    created_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== List Responses ====================

class OrganizationListResponse(BaseModel):
    """Schema for list of organizations"""
    organizations: List[OrganizationResponse]
    total: int
    page: int
    page_size: int


class WorkspaceListResponse(BaseModel):
    """Schema for list of workspaces"""
    workspaces: List[WorkspaceResponse]
    total: int
    page: int
    page_size: int


class MemberListResponse(BaseModel):
    """Schema for list of members"""
    members: List[OrganizationMemberResponse]
    total: int
    page: int
    page_size: int
