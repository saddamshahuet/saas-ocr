"""Webhook service for sending event notifications"""
import hmac
import hashlib
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for sending webhook notifications"""

    def __init__(self):
        """Initialize webhook service"""
        self.timeout = 10.0  # seconds
        self.max_retries = 3
        self.retry_delays = [2, 4, 8]  # seconds (exponential backoff)

    def generate_signature(self, payload: str, secret: Optional[str] = None) -> str:
        """
        Generate HMAC signature for webhook payload

        Args:
            payload: JSON payload as string
            secret: Secret key for signature (defaults to app secret)

        Returns:
            HMAC signature as hex string
        """
        secret_key = secret or settings.SECRET_KEY
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def send_webhook(
        self,
        url: str,
        event_type: str,
        data: Dict[str, Any],
        secret: Optional[str] = None,
        retry: bool = True
    ) -> bool:
        """
        Send webhook notification to specified URL

        Args:
            url: Webhook endpoint URL
            event_type: Type of event (job.completed, job.failed, etc.)
            data: Event data dictionary
            secret: Optional secret for signature
            retry: Whether to retry on failure

        Returns:
            True if webhook delivered successfully, False otherwise
        """
        # Prepare payload
        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        import json
        payload_str = json.dumps(payload, default=str)

        # Generate signature
        signature = self.generate_signature(payload_str, secret)

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": event_type,
            "User-Agent": f"SaaS-OCR-Webhook/{settings.APP_VERSION}"
        }

        # Send webhook with retries
        attempt = 0
        max_attempts = self.max_retries + 1 if retry else 1

        async with httpx.AsyncClient() as client:
            while attempt < max_attempts:
                try:
                    logger.info(f"Sending webhook to {url} (attempt {attempt + 1}/{max_attempts})")

                    response = await client.post(
                        url,
                        content=payload_str,
                        headers=headers,
                        timeout=self.timeout
                    )

                    # Check response
                    if response.status_code >= 200 and response.status_code < 300:
                        logger.info(f"Webhook delivered successfully to {url}")
                        return True
                    else:
                        logger.warning(
                            f"Webhook returned status {response.status_code} from {url}"
                        )

                except httpx.TimeoutException:
                    logger.warning(f"Webhook timeout to {url} (attempt {attempt + 1})")

                except httpx.RequestError as e:
                    logger.error(f"Webhook request error to {url}: {e}")

                except Exception as e:
                    logger.error(f"Unexpected error sending webhook to {url}: {e}")

                # Retry logic
                attempt += 1
                if attempt < max_attempts:
                    import asyncio
                    delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                    logger.info(f"Retrying webhook in {delay} seconds...")
                    await asyncio.sleep(delay)

        logger.error(f"Failed to deliver webhook to {url} after {max_attempts} attempts")
        return False

    async def send_job_completed_webhook(
        self,
        url: str,
        job_id: str,
        job_data: Dict[str, Any]
    ) -> bool:
        """
        Send job.completed webhook

        Args:
            url: Webhook endpoint URL
            job_id: Job ID
            job_data: Job data including extracted results

        Returns:
            True if delivered successfully
        """
        return await self.send_webhook(
            url=url,
            event_type="job.completed",
            data={
                "job_id": job_id,
                "status": "completed",
                **job_data
            }
        )

    async def send_job_failed_webhook(
        self,
        url: str,
        job_id: str,
        error_message: str
    ) -> bool:
        """
        Send job.failed webhook

        Args:
            url: Webhook endpoint URL
            job_id: Job ID
            error_message: Error description

        Returns:
            True if delivered successfully
        """
        return await self.send_webhook(
            url=url,
            event_type="job.failed",
            data={
                "job_id": job_id,
                "status": "failed",
                "error": error_message
            }
        )

    async def send_batch_completed_webhook(
        self,
        url: str,
        batch_id: str,
        total_jobs: int,
        successful_jobs: int,
        failed_jobs: int
    ) -> bool:
        """
        Send batch.completed webhook

        Args:
            url: Webhook endpoint URL
            batch_id: Batch ID
            total_jobs: Total number of jobs in batch
            successful_jobs: Number of successful jobs
            failed_jobs: Number of failed jobs

        Returns:
            True if delivered successfully
        """
        return await self.send_webhook(
            url=url,
            event_type="batch.completed",
            data={
                "batch_id": batch_id,
                "total_jobs": total_jobs,
                "successful_jobs": successful_jobs,
                "failed_jobs": failed_jobs,
                "success_rate": successful_jobs / total_jobs if total_jobs > 0 else 0
            }
        )


# Singleton instance
_webhook_service_instance = None


def get_webhook_service() -> WebhookService:
    """Get or create webhook service singleton"""
    global _webhook_service_instance
    if _webhook_service_instance is None:
        _webhook_service_instance = WebhookService()
    return _webhook_service_instance
