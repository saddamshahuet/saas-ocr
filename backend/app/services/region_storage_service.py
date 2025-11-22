"""Region-aware storage service for data residency compliance"""
from typing import Optional, Dict
import logging
from io import BytesIO

from ..core.regions import RegionService, DataRegion
from ..core.config import settings

logger = logging.getLogger(__name__)


class RegionStorageService:
    """Storage service with multi-region support for data residency

    This service routes storage operations to the correct regional storage
    based on the organization's data residency requirements.
    """

    # Storage clients per region (initialized lazily)
    _clients: Dict[str, any] = {}

    @classmethod
    def get_client(cls, region: str):
        """Get or create a storage client for a specific region

        Args:
            region: Region code (e.g., "us-east-1")

        Returns:
            Storage client for the region
        """
        if region not in cls._clients:
            # Import here to avoid circular dependencies
            try:
                from minio import Minio
                from minio.error import S3Error

                # Get region-specific configuration
                endpoint = cls._get_endpoint_for_region(region)
                access_key = cls._get_access_key_for_region(region)
                secret_key = cls._get_secret_key_for_region(region)
                secure = cls._is_secure_for_region(region)

                client = Minio(
                    endpoint=endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    secure=secure,
                )

                cls._clients[region] = client
                logger.info(f"Initialized storage client for region: {region}")

            except ImportError:
                logger.warning("MinIO not installed, using fallback storage")
                cls._clients[region] = None

        return cls._clients[region]

    @staticmethod
    def _get_endpoint_for_region(region: str) -> str:
        """Get storage endpoint for a region

        In production, this would return different endpoints per region.
        For development, we use the same MinIO instance with region-prefixed buckets.
        """
        # Check if region-specific endpoint is configured
        region_endpoint_env = f"MINIO_ENDPOINT_{region.upper().replace('-', '_')}"

        # Try to get region-specific endpoint from environment
        import os
        endpoint = os.getenv(region_endpoint_env)

        if endpoint:
            return endpoint

        # Fallback to default endpoint
        return getattr(settings, 'MINIO_ENDPOINT', 'localhost:9000')

    @staticmethod
    def _get_access_key_for_region(region: str) -> str:
        """Get access key for a region"""
        import os
        region_key_env = f"MINIO_ACCESS_KEY_{region.upper().replace('-', '_')}"
        return os.getenv(region_key_env, getattr(settings, 'MINIO_ACCESS_KEY', 'minioadmin'))

    @staticmethod
    def _get_secret_key_for_region(region: str) -> str:
        """Get secret key for a region"""
        import os
        region_secret_env = f"MINIO_SECRET_KEY_{region.upper().replace('-', '_')}"
        return os.getenv(region_secret_env, getattr(settings, 'MINIO_SECRET_KEY', 'minioadmin'))

    @staticmethod
    def _is_secure_for_region(region: str) -> bool:
        """Check if HTTPS is used for a region"""
        import os
        region_secure_env = f"MINIO_SECURE_{region.upper().replace('-', '_')}"
        return os.getenv(region_secure_env, 'false').lower() == 'true'

    @classmethod
    def get_bucket_name(cls, region: str, bucket_type: str = "documents") -> str:
        """Get the bucket name for a region and type

        Args:
            region: Region code
            bucket_type: Type of bucket (documents, backups, etc.)

        Returns:
            Bucket name with region prefix
        """
        # Format: region-buckettype (e.g., us-east-1-documents)
        return f"{region}-{bucket_type}".lower()

    @classmethod
    async def upload_file(
        cls,
        region: str,
        file_data: bytes,
        object_name: str,
        bucket_type: str = "documents",
        content_type: str = "application/octet-stream",
    ) -> Dict[str, str]:
        """Upload a file to regional storage

        Args:
            region: Region code
            file_data: File content as bytes
            object_name: Object name/path in storage
            bucket_type: Type of bucket
            content_type: MIME type of the file

        Returns:
            Dictionary with storage information
        """
        client = cls.get_client(region)
        bucket_name = cls.get_bucket_name(region, bucket_type)

        if not client:
            raise Exception("Storage client not available")

        # Ensure bucket exists
        try:
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
        except Exception as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise

        # Upload file
        try:
            file_stream = BytesIO(file_data)
            client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_stream,
                length=len(file_data),
                content_type=content_type,
            )

            logger.info(f"Uploaded file to {region}/{bucket_name}/{object_name}")

            return {
                "region": region,
                "bucket": bucket_name,
                "object_name": object_name,
                "size": len(file_data),
                "content_type": content_type,
            }

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise

    @classmethod
    async def download_file(
        cls,
        region: str,
        object_name: str,
        bucket_type: str = "documents",
    ) -> bytes:
        """Download a file from regional storage

        Args:
            region: Region code
            object_name: Object name/path in storage
            bucket_type: Type of bucket

        Returns:
            File content as bytes
        """
        client = cls.get_client(region)
        bucket_name = cls.get_bucket_name(region, bucket_type)

        if not client:
            raise Exception("Storage client not available")

        try:
            response = client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            logger.info(f"Downloaded file from {region}/{bucket_name}/{object_name}")
            return data

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise

    @classmethod
    async def delete_file(
        cls,
        region: str,
        object_name: str,
        bucket_type: str = "documents",
    ) -> bool:
        """Delete a file from regional storage

        Args:
            region: Region code
            object_name: Object name/path in storage
            bucket_type: Type of bucket

        Returns:
            True if successful
        """
        client = cls.get_client(region)
        bucket_name = cls.get_bucket_name(region, bucket_type)

        if not client:
            raise Exception("Storage client not available")

        try:
            client.remove_object(bucket_name, object_name)
            logger.info(f"Deleted file from {region}/{bucket_name}/{object_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise

    @classmethod
    async def copy_file_between_regions(
        cls,
        source_region: str,
        target_region: str,
        object_name: str,
        bucket_type: str = "documents",
    ) -> Dict[str, str]:
        """Copy a file from one region to another

        Args:
            source_region: Source region code
            target_region: Target region code
            object_name: Object name/path
            bucket_type: Type of bucket

        Returns:
            Dictionary with target storage information
        """
        # Validate migration is allowed
        if not RegionService.can_migrate_between_regions(source_region, target_region):
            raise Exception(
                f"Migration from {source_region} to {target_region} is not allowed due to compliance restrictions"
            )

        # Download from source
        logger.info(f"Copying file {object_name} from {source_region} to {target_region}")
        file_data = await cls.download_file(source_region, object_name, bucket_type)

        # Upload to target
        result = await cls.upload_file(
            region=target_region,
            file_data=file_data,
            object_name=object_name,
            bucket_type=bucket_type,
        )

        logger.info(f"Successfully copied file to {target_region}")
        return result

    @classmethod
    async def get_presigned_url(
        cls,
        region: str,
        object_name: str,
        bucket_type: str = "documents",
        expiry_seconds: int = 3600,
    ) -> str:
        """Get a presigned URL for temporary access to a file

        Args:
            region: Region code
            object_name: Object name/path
            bucket_type: Type of bucket
            expiry_seconds: URL expiry time in seconds

        Returns:
            Presigned URL
        """
        client = cls.get_client(region)
        bucket_name = cls.get_bucket_name(region, bucket_type)

        if not client:
            raise Exception("Storage client not available")

        try:
            from datetime import timedelta

            url = client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expiry_seconds),
            )

            return url

        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise

    @classmethod
    async def list_files(
        cls,
        region: str,
        bucket_type: str = "documents",
        prefix: Optional[str] = None,
    ) -> list:
        """List files in regional storage

        Args:
            region: Region code
            bucket_type: Type of bucket
            prefix: Optional prefix to filter objects

        Returns:
            List of object information
        """
        client = cls.get_client(region)
        bucket_name = cls.get_bucket_name(region, bucket_type)

        if not client:
            raise Exception("Storage client not available")

        try:
            objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)
            result = []

            for obj in objects:
                result.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })

            return result

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise

    @classmethod
    def validate_region(cls, region: str) -> bool:
        """Validate that a region is supported"""
        return RegionService.is_valid_region(region)
