"""Job model for document processing tasks"""
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Float, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    """Job model for async document processing"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, index=True, nullable=False)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Job status: pending, processing, completed, failed
    status = Column(String(50), default="pending", nullable=False, index=True)

    # Processing details
    document_type = Column(String(100), nullable=True)  # e.g., "hospice_admission"
    schema_template = Column(String(100), nullable=True)  # Schema to use
    total_pages = Column(Integer, default=0, nullable=False)
    pages_processed = Column(Integer, default=0, nullable=False)

    # Results
    extracted_data = Column(JSON, nullable=True)  # Extracted structured data
    confidence_scores = Column(JSON, nullable=True)  # Per-field confidence scores
    raw_text = Column(Text, nullable=True)  # Raw OCR text

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Performance metrics
    processing_time_seconds = Column(Float, nullable=True)

    # Webhook
    webhook_url = Column(String(500), nullable=True)
    webhook_sent = Column(Integer, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="jobs")
    documents = relationship("Document", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job {self.job_id} - {self.status}>"

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_pages == 0:
            return 0.0
        return (self.pages_processed / self.total_pages) * 100
