"""Human-in-the-Loop review service

Provides review queue management, annotation interface, and feedback collection.
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Review status"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"


@dataclass
class ReviewItem:
    """Item for review"""
    id: str
    job_id: str
    field_name: str
    extracted_value: Any
    suggested_value: Optional[Any] = None
    reviewer_notes: str = ""
    status: ReviewStatus = ReviewStatus.PENDING
    confidence: float = 0.0
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "field_name": self.field_name,
            "extracted_value": self.extracted_value,
            "suggested_value": self.suggested_value,
            "reviewer_notes": self.reviewer_notes,
            "status": self.status.value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewer_id": self.reviewer_id
        }


class ReviewQueue:
    """Manages review queue"""

    def __init__(self):
        self.items: List[ReviewItem] = []
        self._next_id = 1

    def add_item(
        self,
        job_id: str,
        field_name: str,
        extracted_value: Any,
        confidence: float = 0.0
    ) -> ReviewItem:
        """Add item to review queue"""
        item = ReviewItem(
            id=f"review-{self._next_id}",
            job_id=job_id,
            field_name=field_name,
            extracted_value=extracted_value,
            confidence=confidence,
            created_at=datetime.now()
        )
        self.items.append(item)
        self._next_id += 1

        logger.info(f"Added review item: {item.id}")
        return item

    def get_pending_items(self, limit: int = 10) -> List[ReviewItem]:
        """Get pending review items"""
        pending = [
            item for item in self.items
            if item.status == ReviewStatus.PENDING
        ]
        return pending[:limit]

    def get_item(self, item_id: str) -> Optional[ReviewItem]:
        """Get review item by ID"""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def update_item(
        self,
        item_id: str,
        suggested_value: Any,
        reviewer_notes: str = "",
        status: ReviewStatus = ReviewStatus.APPROVED,
        reviewer_id: Optional[str] = None
    ) -> bool:
        """Update review item"""
        item = self.get_item(item_id)
        if not item:
            return False

        item.suggested_value = suggested_value
        item.reviewer_notes = reviewer_notes
        item.status = status
        item.reviewed_at = datetime.now()
        item.reviewer_id = reviewer_id

        logger.info(f"Updated review item: {item_id}")
        return True

    def get_statistics(self) -> Dict:
        """Get review queue statistics"""
        total = len(self.items)
        pending = sum(1 for item in self.items if item.status == ReviewStatus.PENDING)
        approved = sum(1 for item in self.items if item.status == ReviewStatus.APPROVED)
        rejected = sum(1 for item in self.items if item.status == ReviewStatus.REJECTED)

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "in_review": sum(1 for item in self.items if item.status == ReviewStatus.IN_REVIEW)
        }


# Singleton
_review_queue = ReviewQueue()


def get_review_queue() -> ReviewQueue:
    """Get review queue singleton"""
    return _review_queue
