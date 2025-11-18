"""Job schemas"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreate(BaseModel):
    """Schema for creating a new job"""
    document_type: Optional[str] = Field(None, description="Type of document being processed")
    schema_template: Optional[str] = Field(
        "medical_general",
        description="Schema template to use for extraction"
    )
    webhook_url: Optional[HttpUrl] = Field(None, description="Webhook URL for job completion notification")


class JobResponse(BaseModel):
    """Schema for job response"""
    id: int
    job_id: str
    status: JobStatus
    document_type: Optional[str]
    schema_template: Optional[str]
    total_pages: int
    pages_processed: int
    progress_percentage: float
    extracted_data: Optional[Dict[str, Any]]
    confidence_scores: Optional[Dict[str, float]]
    error_message: Optional[str]
    processing_time_seconds: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Schema for paginated job list"""
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
