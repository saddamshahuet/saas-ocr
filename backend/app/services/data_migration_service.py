"""Data migration service for cross-region transfers"""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging
from datetime import datetime

from ..models import Organization, Document, Job
from ..core.regions import RegionService
from .region_storage_service import RegionStorageService

logger = logging.getLogger(__name__)


class DataMigrationStatus:
    """Migration status constants"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataMigrationService:
    """Service for migrating organization data between regions"""

    @staticmethod
    async def validate_migration(
        organization_id: int,
        target_region: str,
        db: Session,
    ) -> Dict[str, any]:
        """Validate if migration is possible

        Args:
            organization_id: Organization to migrate
            target_region: Target region code
            db: Database session

        Returns:
            Dictionary with validation results
        """
        # Get organization
        org = db.query(Organization).filter(Organization.id == organization_id).first()

        if not org:
            return {
                "valid": False,
                "error": "Organization not found",
            }

        # Check if target region is valid
        if not RegionService.is_valid_region(target_region):
            return {
                "valid": False,
                "error": f"Invalid target region: {target_region}",
            }

        # Check if source and target are the same
        if org.region == target_region:
            return {
                "valid": False,
                "error": "Source and target regions are the same",
            }

        # Check if migration is allowed based on compliance
        if not RegionService.can_migrate_between_regions(org.region, target_region):
            return {
                "valid": False,
                "error": f"Migration from {org.region} to {target_region} is not allowed due to compliance restrictions",
            }

        # Count documents to migrate
        doc_count = (
            db.query(Document)
            .join(Job)
            .filter(Job.organization_id == organization_id)
            .count()
        )

        # Estimate storage size
        total_size = (
            db.query(Document)
            .join(Job)
            .filter(Job.organization_id == organization_id)
        )

        total_bytes = sum(doc.file_size for doc in total_size.all())
        total_gb = total_bytes / (1024 ** 3)

        return {
            "valid": True,
            "source_region": org.region,
            "target_region": target_region,
            "document_count": doc_count,
            "total_size_gb": round(total_gb, 2),
            "estimated_time_hours": round(doc_count / 1000, 2),  # Rough estimate
        }

    @staticmethod
    async def start_migration(
        organization_id: int,
        target_region: str,
        db: Session,
        dry_run: bool = False,
    ) -> Dict[str, any]:
        """Start data migration to a new region

        Args:
            organization_id: Organization to migrate
            target_region: Target region code
            db: Database session
            dry_run: If True, only simulate migration

        Returns:
            Migration result
        """
        # Validate migration
        validation = await DataMigrationService.validate_migration(
            organization_id, target_region, db
        )

        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["error"],
            }

        org = db.query(Organization).filter(Organization.id == organization_id).first()
        source_region = org.region

        logger.info(
            f"Starting {'DRY RUN' if dry_run else ''} migration for org {organization_id} "
            f"from {source_region} to {target_region}"
        )

        # Get all documents for this organization
        documents = (
            db.query(Document)
            .join(Job)
            .filter(Job.organization_id == organization_id)
            .all()
        )

        migrated_count = 0
        failed_count = 0
        errors = []

        for doc in documents:
            try:
                if not dry_run:
                    # Copy file to new region
                    await RegionStorageService.copy_file_between_regions(
                        source_region=source_region,
                        target_region=target_region,
                        object_name=doc.storage_path,
                        bucket_type=doc.storage_bucket.replace(f"{source_region}-", ""),
                    )

                    # Update document storage bucket
                    old_bucket = doc.storage_bucket
                    new_bucket = old_bucket.replace(source_region, target_region)
                    doc.storage_bucket = new_bucket

                migrated_count += 1

                if migrated_count % 100 == 0:
                    logger.info(f"Migrated {migrated_count}/{len(documents)} documents")

            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to migrate document {doc.id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

                # Stop if too many failures
                if failed_count > 10:
                    logger.error("Too many failures, stopping migration")
                    break

        # Update organization region if successful
        if not dry_run and failed_count == 0:
            org.region = target_region
            db.commit()
            logger.info(f"Updated organization {organization_id} region to {target_region}")
        else:
            db.rollback()

        return {
            "success": failed_count == 0,
            "dry_run": dry_run,
            "source_region": source_region,
            "target_region": target_region,
            "total_documents": len(documents),
            "migrated_count": migrated_count,
            "failed_count": failed_count,
            "errors": errors[:10],  # Return first 10 errors
        }

    @staticmethod
    async def rollback_migration(
        organization_id: int,
        original_region: str,
        db: Session,
    ) -> Dict[str, any]:
        """Rollback a migration to the original region

        Args:
            organization_id: Organization to rollback
            original_region: Original region code
            db: Database session

        Returns:
            Rollback result
        """
        org = db.query(Organization).filter(Organization.id == organization_id).first()

        if not org:
            return {
                "success": False,
                "error": "Organization not found",
            }

        current_region = org.region

        if current_region == original_region:
            return {
                "success": False,
                "error": "Organization is already in the original region",
            }

        logger.info(
            f"Rolling back migration for org {organization_id} "
            f"from {current_region} to {original_region}"
        )

        # Use the same migration logic but in reverse
        result = await DataMigrationService.start_migration(
            organization_id=organization_id,
            target_region=original_region,
            db=db,
            dry_run=False,
        )

        return result

    @staticmethod
    async def cleanup_old_region_data(
        organization_id: int,
        old_region: str,
        db: Session,
    ) -> Dict[str, any]:
        """Clean up data from the old region after successful migration

        Args:
            organization_id: Organization ID
            old_region: Old region to clean up
            db: Database session

        Returns:
            Cleanup result
        """
        org = db.query(Organization).filter(Organization.id == organization_id).first()

        if not org:
            return {
                "success": False,
                "error": "Organization not found",
            }

        # Verify org is not in the old region anymore
        if org.region == old_region:
            return {
                "success": False,
                "error": "Organization is still in the old region, cannot cleanup",
            }

        logger.info(
            f"Cleaning up data for org {organization_id} from old region {old_region}"
        )

        # Get all documents
        documents = (
            db.query(Document)
            .join(Job)
            .filter(Job.organization_id == organization_id)
            .all()
        )

        deleted_count = 0
        failed_count = 0

        for doc in documents:
            try:
                # Extract bucket type from old bucket name
                old_bucket_parts = doc.storage_bucket.split('-')
                if len(old_bucket_parts) >= 2:
                    bucket_type = '-'.join(old_bucket_parts[1:])

                    # Delete from old region
                    await RegionStorageService.delete_file(
                        region=old_region,
                        object_name=doc.storage_path,
                        bucket_type=bucket_type,
                    )

                    deleted_count += 1

            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to delete document {doc.id} from old region: {e}")

        return {
            "success": failed_count == 0,
            "old_region": old_region,
            "deleted_count": deleted_count,
            "failed_count": failed_count,
        }

    @staticmethod
    def estimate_migration_cost(
        total_size_gb: float,
        source_region: str,
        target_region: str,
    ) -> Dict[str, float]:
        """Estimate the cost of migrating data between regions

        Args:
            total_size_gb: Total data size in GB
            source_region: Source region
            target_region: Target region

        Returns:
            Dictionary with cost estimates
        """
        # Rough cost estimates (these would be actual cloud provider costs)
        # Cost per GB transferred
        transfer_cost_per_gb = 0.09  # USD

        # Storage cost difference (monthly)
        storage_cost_per_gb_month = {
            "us-east-1": 0.023,
            "us-west-1": 0.026,
            "eu-west-1": 0.024,
            "ap-southeast-1": 0.025,
        }

        source_storage_cost = storage_cost_per_gb_month.get(source_region, 0.023)
        target_storage_cost = storage_cost_per_gb_month.get(target_region, 0.023)

        transfer_cost = total_size_gb * transfer_cost_per_gb
        monthly_storage_diff = (target_storage_cost - source_storage_cost) * total_size_gb

        return {
            "one_time_transfer_cost_usd": round(transfer_cost, 2),
            "monthly_storage_cost_difference_usd": round(monthly_storage_diff, 2),
            "source_monthly_storage_usd": round(source_storage_cost * total_size_gb, 2),
            "target_monthly_storage_usd": round(target_storage_cost * total_size_gb, 2),
        }
