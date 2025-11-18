"""Analytics service for usage metrics and reporting"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from app.models import Job, User, Document, AuditLog

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics and reporting"""

    def __init__(self, db: Session):
        """
        Initialize analytics service

        Args:
            db: Database session
        """
        self.db = db

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get usage statistics for a user

        Args:
            user_id: User ID

        Returns:
            Dictionary with user statistics
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        # Job statistics
        total_jobs = self.db.query(Job).filter(Job.user_id == user_id).count()

        completed_jobs = self.db.query(Job).filter(
            Job.user_id == user_id,
            Job.status == "completed"
        ).count()

        failed_jobs = self.db.query(Job).filter(
            Job.user_id == user_id,
            Job.status == "failed"
        ).count()

        pending_jobs = self.db.query(Job).filter(
            Job.user_id == user_id,
            Job.status.in_(["pending", "processing"])
        ).count()

        # API calls
        api_calls_used = user.api_calls_total - user.api_calls_remaining
        usage_percentage = (api_calls_used / user.api_calls_total * 100) if user.api_calls_total > 0 else 0

        # Pages processed
        total_pages = self.db.query(func.sum(Job.total_pages)).filter(
            Job.user_id == user_id,
            Job.status == "completed"
        ).scalar() or 0

        # Average processing time
        avg_processing_time = self.db.query(func.avg(Job.processing_time_seconds)).filter(
            Job.user_id == user_id,
            Job.status == "completed",
            Job.processing_time_seconds.isnot(None)
        ).scalar() or 0

        # Success rate
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0

        return {
            "user_id": user_id,
            "tier": user.tier,
            "api_calls": {
                "total": user.api_calls_total,
                "remaining": user.api_calls_remaining,
                "used": api_calls_used,
                "usage_percentage": round(usage_percentage, 2)
            },
            "jobs": {
                "total": total_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs,
                "pending": pending_jobs,
                "success_rate": round(success_rate, 2)
            },
            "processing": {
                "total_pages": int(total_pages),
                "avg_processing_time_seconds": round(float(avg_processing_time), 2)
            }
        }

    def get_jobs_over_time(
        self,
        user_id: int,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get job statistics over time

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            List of daily statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query jobs grouped by date
        results = self.db.query(
            func.date(Job.created_at).label("date"),
            func.count(Job.id).label("total"),
            func.sum(func.case((Job.status == "completed", 1), else_=0)).label("completed"),
            func.sum(func.case((Job.status == "failed", 1), else_=0)).label("failed")
        ).filter(
            Job.user_id == user_id,
            Job.created_at >= cutoff_date
        ).group_by(
            func.date(Job.created_at)
        ).order_by(
            func.date(Job.created_at)
        ).all()

        return [
            {
                "date": str(row.date),
                "total": row.total,
                "completed": row.completed or 0,
                "failed": row.failed or 0
            }
            for row in results
        ]

    def get_accuracy_by_document_type(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get average confidence scores by document type

        Args:
            user_id: User ID

        Returns:
            List of document types with average confidence
        """
        # Get completed jobs with confidence scores
        jobs = self.db.query(Job).filter(
            Job.user_id == user_id,
            Job.status == "completed",
            Job.confidence_scores.isnot(None)
        ).all()

        # Group by document type
        type_stats = {}

        for job in jobs:
            doc_type = job.document_type or "unknown"

            if doc_type not in type_stats:
                type_stats[doc_type] = {
                    "document_type": doc_type,
                    "count": 0,
                    "total_confidence": 0.0
                }

            # Calculate average confidence for this job
            if job.confidence_scores:
                confidences = list(job.confidence_scores.values())
                if confidences:
                    avg_conf = sum(confidences) / len(confidences)
                    type_stats[doc_type]["count"] += 1
                    type_stats[doc_type]["total_confidence"] += avg_conf

        # Calculate averages
        results = []
        for doc_type, stats in type_stats.items():
            if stats["count"] > 0:
                results.append({
                    "document_type": doc_type,
                    "count": stats["count"],
                    "average_confidence": round(stats["total_confidence"] / stats["count"], 4)
                })

        return sorted(results, key=lambda x: x["count"], reverse=True)

    def get_error_analysis(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent errors with analysis

        Args:
            user_id: User ID
            limit: Maximum number of errors to return

        Returns:
            List of error details
        """
        failed_jobs = self.db.query(Job).filter(
            Job.user_id == user_id,
            Job.status == "failed"
        ).order_by(
            desc(Job.created_at)
        ).limit(limit).all()

        return [
            {
                "job_id": job.job_id,
                "created_at": job.created_at.isoformat(),
                "error_message": job.error_message,
                "document_type": job.document_type,
                "retry_count": job.retry_count
            }
            for job in failed_jobs
        ]

    def get_cost_analysis(self, user_id: int) -> Dict[str, Any]:
        """
        Get cost analysis for user

        Args:
            user_id: User ID

        Returns:
            Dictionary with cost metrics
        """
        from app.services.payment_service import get_payment_service

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        payment_service = get_payment_service()

        # Get tier info
        try:
            tier_info = payment_service.get_tier_info(user.tier)
        except:
            tier_info = {"price": 0, "api_calls": 0}

        # Calculate costs
        api_calls_used = user.api_calls_total - user.api_calls_remaining
        cost_per_call = payment_service.calculate_usage_cost(
            api_calls=user.api_calls_total,
            tier=user.tier
        )

        total_cost = cost_per_call * api_calls_used

        # Get documents processed
        total_documents = self.db.query(Job).filter(
            Job.user_id == user_id,
            Job.status == "completed"
        ).count()

        total_pages = self.db.query(func.sum(Job.total_pages)).filter(
            Job.user_id == user_id,
            Job.status == "completed"
        ).scalar() or 0

        cost_per_document = total_cost / total_documents if total_documents > 0 else 0
        cost_per_page = total_cost / total_pages if total_pages > 0 else 0

        return {
            "tier": user.tier,
            "api_calls_used": api_calls_used,
            "cost_per_call": round(cost_per_call, 4),
            "total_cost": round(total_cost, 2),
            "documents_processed": total_documents,
            "pages_processed": int(total_pages),
            "cost_per_document": round(cost_per_document, 4),
            "cost_per_page": round(cost_per_page, 4)
        }

    def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top users by API usage (admin only)

        Args:
            limit: Maximum number of users to return

        Returns:
            List of top users
        """
        users = self.db.query(
            User.id,
            User.email,
            User.organization,
            User.tier,
            User.api_calls_total,
            User.api_calls_remaining,
            func.count(Job.id).label("total_jobs")
        ).outerjoin(
            Job, Job.user_id == User.id
        ).group_by(
            User.id
        ).order_by(
            desc(func.count(Job.id))
        ).limit(limit).all()

        return [
            {
                "user_id": user.id,
                "email": user.email,
                "organization": user.organization,
                "tier": user.tier,
                "api_calls_used": user.api_calls_total - user.api_calls_remaining,
                "total_jobs": user.total_jobs
            }
            for user in users
        ]

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system-wide statistics (admin only)

        Returns:
            Dictionary with system metrics
        """
        # User statistics
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()

        # Job statistics
        total_jobs = self.db.query(Job).count()
        completed_jobs = self.db.query(Job).filter(Job.status == "completed").count()
        failed_jobs = self.db.query(Job).filter(Job.status == "failed").count()

        # Pages processed
        total_pages = self.db.query(func.sum(Job.total_pages)).filter(
            Job.status == "completed"
        ).scalar() or 0

        # Average processing time
        avg_processing_time = self.db.query(func.avg(Job.processing_time_seconds)).filter(
            Job.status == "completed",
            Job.processing_time_seconds.isnot(None)
        ).scalar() or 0

        # Storage usage (approximate)
        total_file_size = self.db.query(func.sum(Document.file_size)).scalar() or 0

        return {
            "users": {
                "total": total_users,
                "active": active_users
            },
            "jobs": {
                "total": total_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs,
                "success_rate": round((completed_jobs / total_jobs * 100) if total_jobs > 0 else 0, 2)
            },
            "processing": {
                "total_pages": int(total_pages),
                "avg_processing_time_seconds": round(float(avg_processing_time), 2)
            },
            "storage": {
                "total_bytes": int(total_file_size),
                "total_mb": round(int(total_file_size) / (1024 * 1024), 2)
            }
        }


def get_analytics_service(db: Session) -> AnalyticsService:
    """Get analytics service instance"""
    return AnalyticsService(db)
