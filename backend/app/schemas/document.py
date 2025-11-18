"""Document schemas"""
from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):
    """Schema for document response"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    mime_type: str
    is_processed: bool
    created_at: datetime

    class Config:
        from_attributes = True
