"""Celery tasks for async document processing"""
import os
import tempfile
from celery import Task
from celery_app import celery_app
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session"""
    _db = None

    @property
    def db(self) -> Session:
        if self._db is None:
            from app.core.database import SessionLocal
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(base=DatabaseTask, bind=True, max_retries=3)
def process_document_task(self, job_id: int, file_path: str, file_type: str, schema_template: str):
    """
    Async task for processing a document with OCR and LLM extraction

    Args:
        job_id: Database ID of the job
        file_path: Path to the document file
        file_type: File extension/type
        schema_template: Schema template to use

    Returns:
        Dictionary with processing results
    """
    from app.models import Job
    from app.services.ocr_service import get_ocr_service
    from app.services.llm_service import get_llm_service
    from app.services.webhook_service import get_webhook_service
    from app.core.config import settings
    from datetime import datetime
    import asyncio

    logger.info(f"Starting document processing task for job_id={job_id}")

    try:
        # Get job from database
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Update status
        job.status = "processing"
        job.pages_processed = 0
        self.db.commit()

        start_time = datetime.utcnow()

        # Initialize services
        ocr_service = get_ocr_service(
            use_gpu=settings.OCR_USE_GPU,
            language=settings.OCR_LANGUAGE
        )

        llm_service = get_llm_service(
            model_name=settings.LLM_MODEL_NAME,
            use_gpu=settings.LLM_USE_GPU
        )

        # Process with OCR
        logger.info(f"Running OCR on {file_path}")
        ocr_result = ocr_service.process_document(
            file_path=file_path,
            file_type=file_type,
            preprocess=True
        )

        # Update progress
        job.total_pages = ocr_result["total_pages"]
        job.pages_processed = ocr_result["total_pages"]
        job.raw_text = ocr_result["raw_text"]
        self.db.commit()

        # Extract structured data with LLM
        logger.info(f"Extracting structured data with LLM")
        extraction_result = llm_service.extract_structured_data(
            text=ocr_result["raw_text"],
            schema_template=schema_template
        )

        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        # Update job with results
        job.status = "completed"
        job.extracted_data = extraction_result["extracted_data"]
        job.confidence_scores = extraction_result["confidence_scores"]
        job.processing_time_seconds = processing_time
        self.db.commit()

        logger.info(f"Job {job.job_id} completed successfully in {processing_time:.2f}s")

        # Send webhook if configured
        if job.webhook_url and not job.webhook_sent:
            webhook_service = get_webhook_service()
            try:
                success = asyncio.run(webhook_service.send_job_completed_webhook(
                    url=job.webhook_url,
                    job_id=job.job_id,
                    job_data={
                        "extracted_data": job.extracted_data,
                        "confidence_scores": job.confidence_scores,
                        "processing_time": job.processing_time_seconds,
                        "total_pages": job.total_pages
                    }
                ))
                if success:
                    job.webhook_sent = True
                    self.db.commit()
            except Exception as e:
                logger.error(f"Failed to send webhook: {e}")

        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {file_path}: {e}")

        return {
            "job_id": job.job_id,
            "status": "completed",
            "processing_time": processing_time
        }

    except Exception as e:
        logger.error(f"Error processing document for job {job_id}: {e}")

        # Update job status to failed
        try:
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                self.db.commit()

                # Send failure webhook
                if job.webhook_url and not job.webhook_sent:
                    webhook_service = get_webhook_service()
                    try:
                        asyncio.run(webhook_service.send_job_failed_webhook(
                            url=job.webhook_url,
                            job_id=job.job_id,
                            error_message=str(e)
                        ))
                        job.webhook_sent = True
                        self.db.commit()
                    except Exception as webhook_error:
                        logger.error(f"Failed to send failure webhook: {webhook_error}")
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")

        # Retry if this was a transient error
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60)  # Retry after 1 minute

        raise


@celery_app.task(base=DatabaseTask, bind=True)
def process_batch_task(self, batch_id: str, job_ids: list, webhook_url: str = None):
    """
    Async task for processing a batch of documents

    Args:
        batch_id: Unique batch identifier
        job_ids: List of job IDs to process
        webhook_url: Optional webhook URL for batch completion

    Returns:
        Dictionary with batch processing results
    """
    from app.services.webhook_service import get_webhook_service
    import asyncio

    logger.info(f"Starting batch processing task for batch_id={batch_id} with {len(job_ids)} jobs")

    results = {
        "batch_id": batch_id,
        "total_jobs": len(job_ids),
        "successful_jobs": 0,
        "failed_jobs": 0,
        "results": []
    }

    # Process each job
    for job_id in job_ids:
        try:
            from app.models import Job, Document

            job = self.db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.warning(f"Job {job_id} not found in batch {batch_id}")
                results["failed_jobs"] += 1
                continue

            # Get document
            document = self.db.query(Document).filter(Document.job_id == job.id).first()
            if not document:
                logger.warning(f"No document found for job {job_id}")
                results["failed_jobs"] += 1
                continue

            # Process document (synchronously within batch)
            result = process_document_task(
                job_id=job.id,
                file_path=document.storage_path,
                file_type=document.file_type,
                schema_template=job.schema_template or "medical_general"
            )

            results["successful_jobs"] += 1
            results["results"].append({
                "job_id": job.job_id,
                "status": "completed"
            })

        except Exception as e:
            logger.error(f"Error processing job {job_id} in batch {batch_id}: {e}")
            results["failed_jobs"] += 1
            results["results"].append({
                "job_id": job_id,
                "status": "failed",
                "error": str(e)
            })

    logger.info(
        f"Batch {batch_id} completed: {results['successful_jobs']}/{results['total_jobs']} successful"
    )

    # Send batch completion webhook
    if webhook_url:
        webhook_service = get_webhook_service()
        try:
            asyncio.run(webhook_service.send_batch_completed_webhook(
                url=webhook_url,
                batch_id=batch_id,
                total_jobs=results["total_jobs"],
                successful_jobs=results["successful_jobs"],
                failed_jobs=results["failed_jobs"]
            ))
        except Exception as e:
            logger.error(f"Failed to send batch completion webhook: {e}")

    return results


@celery_app.task(base=DatabaseTask)
def cleanup_old_jobs_task(days: int = 90):
    """
    Periodic task to clean up old jobs and files

    Args:
        days: Delete jobs older than this many days
    """
    from app.models import Job, Document
    from app.services.storage_service import get_storage_service
    from datetime import datetime, timedelta

    logger.info(f"Starting cleanup of jobs older than {days} days")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    try:
        # Get old jobs
        old_jobs = self.db.query(Job).filter(Job.created_at < cutoff_date).all()

        storage_service = get_storage_service()
        deleted_count = 0

        for job in old_jobs:
            try:
                # Delete associated documents from storage
                documents = self.db.query(Document).filter(Document.job_id == job.id).all()
                for doc in documents:
                    try:
                        if storage_service.file_exists(doc.storage_path):
                            storage_service.delete_file(doc.storage_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete file {doc.storage_path}: {e}")

                    self.db.delete(doc)

                # Delete job
                self.db.delete(job)
                deleted_count += 1

            except Exception as e:
                logger.error(f"Error deleting job {job.id}: {e}")
                continue

        self.db.commit()
        logger.info(f"Cleanup completed: deleted {deleted_count} old jobs")

        return {"deleted_jobs": deleted_count}

    except Exception as e:
        logger.error(f"Error during cleanup task: {e}")
        self.db.rollback()
        raise


@celery_app.task
def test_task(message: str):
    """Simple test task"""
    logger.info(f"Test task executed with message: {message}")
    return f"Task completed: {message}"
