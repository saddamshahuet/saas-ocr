"""Document model"""
from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    """Document model for uploaded files"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # in bytes
    file_type = Column(String(50), nullable=False)  # e.g., "pdf", "png"
    mime_type = Column(String(100), nullable=False)

    # Storage location
    storage_path = Column(String(500), nullable=False)  # Path in MinIO/S3
    storage_bucket = Column(String(100), nullable=False)

    # Processing status
    is_processed = Column(Integer, default=False, nullable=False)

    # Relationships
    job = relationship("Job", back_populates="documents")
    organization = relationship("Organization", back_populates="documents")

    def __repr__(self):
        return f"<Document {self.filename}>"
