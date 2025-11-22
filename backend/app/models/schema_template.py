"""Schema Template model for custom extraction schemas"""
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class SchemaTemplate(Base, TimestampMixin):
    """Custom schema template for data extraction"""
    __tablename__ = "schema_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # Template metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    document_type = Column(String(100), nullable=True)  # Type of document this schema is for

    # Schema definition (JSON Schema format)
    schema_definition = Column(JSON, nullable=False)

    # Field definitions
    fields = Column(JSON, nullable=False)  # List of field definitions

    # Settings
    is_public = Column(Boolean, default=False, nullable=False)  # Share with other users
    is_active = Column(Boolean, default=True, nullable=False)

    # Version control
    version = Column(String(20), default="1.0", nullable=False)

    # Usage stats
    usage_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User")
    organization = relationship("Organization", back_populates="schema_templates")

    def __repr__(self):
        return f"<SchemaTemplate {self.name} v{self.version}>"


class Batch(Base, TimestampMixin):
    """Batch processing model"""
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(100), unique=True, index=True, nullable=False)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # Batch metadata
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Status: pending, processing, completed, failed
    status = Column(String(50), default="pending", nullable=False, index=True)

    # Job counts
    total_jobs = Column(Integer, default=0, nullable=False)
    completed_jobs = Column(Integer, default=0, nullable=False)
    failed_jobs = Column(Integer, default=0, nullable=False)

    # Settings
    schema_template = Column(String(100), nullable=True)
    document_type = Column(String(100), nullable=True)

    # Webhook
    webhook_url = Column(String(500), nullable=True)
    webhook_sent = Column(Boolean, default=False, nullable=False)

    # Results summary
    results_summary = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")

    def __repr__(self):
        return f"<Batch {self.batch_id} - {self.status}>"

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_jobs == 0:
            return 0.0
        processed = self.completed_jobs + self.failed_jobs
        return (processed / self.total_jobs) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        processed = self.completed_jobs + self.failed_jobs
        if processed == 0:
            return 0.0
        return (self.completed_jobs / processed) * 100
