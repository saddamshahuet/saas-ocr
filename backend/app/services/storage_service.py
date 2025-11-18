"""Storage service for MinIO/S3 file management"""
import os
import io
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
import boto3
from botocore.exceptions import ClientError
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage (MinIO or S3)"""

    def __init__(self):
        """Initialize storage client based on configuration"""
        self.storage_type = settings.STORAGE_TYPE

        if self.storage_type == "minio":
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            self.bucket_name = settings.MINIO_BUCKET_NAME
            self._ensure_bucket_exists()

        elif self.storage_type == "s3":
            self.client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.bucket_name = settings.S3_BUCKET_NAME
            self._ensure_bucket_exists()

        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")

        logger.info(f"Storage service initialized ({self.storage_type}, bucket: {self.bucket_name})")

    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists, create if not"""
        try:
            if self.storage_type == "minio":
                if not self.client.bucket_exists(self.bucket_name):
                    self.client.make_bucket(self.bucket_name)
                    logger.info(f"Created MinIO bucket: {self.bucket_name}")
            elif self.storage_type == "s3":
                try:
                    self.client.head_bucket(Bucket=self.bucket_name)
                except ClientError:
                    self.client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created S3 bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {e}")
            raise

    def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to storage

        Args:
            file_data: File data as binary stream
            object_name: Name/path for the object in storage
            content_type: MIME type of the file
            metadata: Optional metadata dictionary

        Returns:
            Storage path/key of uploaded file
        """
        try:
            # Get file size
            file_data.seek(0, os.SEEK_END)
            file_size = file_data.tell()
            file_data.seek(0)

            if self.storage_type == "minio":
                self.client.put_object(
                    self.bucket_name,
                    object_name,
                    file_data,
                    file_size,
                    content_type=content_type,
                    metadata=metadata or {}
                )
            elif self.storage_type == "s3":
                extra_args = {'ContentType': content_type}
                if metadata:
                    extra_args['Metadata'] = metadata

                self.client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    object_name,
                    ExtraArgs=extra_args
                )

            logger.info(f"Uploaded file to {self.storage_type}: {object_name}")
            return object_name

        except Exception as e:
            logger.error(f"Error uploading file {object_name}: {e}")
            raise

    def download_file(self, object_name: str) -> bytes:
        """
        Download a file from storage

        Args:
            object_name: Name/path of the object in storage

        Returns:
            File data as bytes
        """
        try:
            if self.storage_type == "minio":
                response = self.client.get_object(self.bucket_name, object_name)
                data = response.read()
                response.close()
                response.release_conn()
                return data

            elif self.storage_type == "s3":
                buffer = io.BytesIO()
                self.client.download_fileobj(self.bucket_name, object_name, buffer)
                buffer.seek(0)
                return buffer.read()

        except Exception as e:
            logger.error(f"Error downloading file {object_name}: {e}")
            raise

    def download_to_file(self, object_name: str, file_path: str):
        """
        Download a file from storage to local filesystem

        Args:
            object_name: Name/path of the object in storage
            file_path: Local file path to save to
        """
        try:
            if self.storage_type == "minio":
                self.client.fget_object(self.bucket_name, object_name, file_path)
            elif self.storage_type == "s3":
                self.client.download_file(self.bucket_name, object_name, file_path)

            logger.info(f"Downloaded {object_name} to {file_path}")

        except Exception as e:
            logger.error(f"Error downloading file {object_name} to {file_path}: {e}")
            raise

    def delete_file(self, object_name: str):
        """
        Delete a file from storage

        Args:
            object_name: Name/path of the object to delete
        """
        try:
            if self.storage_type == "minio":
                self.client.remove_object(self.bucket_name, object_name)
            elif self.storage_type == "s3":
                self.client.delete_object(Bucket=self.bucket_name, Key=object_name)

            logger.info(f"Deleted file from {self.storage_type}: {object_name}")

        except Exception as e:
            logger.error(f"Error deleting file {object_name}: {e}")
            raise

    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in storage

        Args:
            object_name: Name/path of the object

        Returns:
            True if file exists, False otherwise
        """
        try:
            if self.storage_type == "minio":
                self.client.stat_object(self.bucket_name, object_name)
                return True
            elif self.storage_type == "s3":
                self.client.head_object(Bucket=self.bucket_name, Key=object_name)
                return True
        except Exception:
            return False

    def get_presigned_url(
        self,
        object_name: str,
        expires_seconds: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        Generate a presigned URL for temporary access to a file

        Args:
            object_name: Name/path of the object
            expires_seconds: URL expiration time in seconds (default 1 hour)
            method: HTTP method (GET or PUT)

        Returns:
            Presigned URL as string
        """
        try:
            if self.storage_type == "minio":
                from datetime import timedelta
                if method == "GET":
                    url = self.client.presigned_get_object(
                        self.bucket_name,
                        object_name,
                        expires=timedelta(seconds=expires_seconds)
                    )
                else:  # PUT
                    url = self.client.presigned_put_object(
                        self.bucket_name,
                        object_name,
                        expires=timedelta(seconds=expires_seconds)
                    )
                return url

            elif self.storage_type == "s3":
                url = self.client.generate_presigned_url(
                    'get_object' if method == "GET" else 'put_object',
                    Params={'Bucket': self.bucket_name, 'Key': object_name},
                    ExpiresIn=expires_seconds
                )
                return url

        except Exception as e:
            logger.error(f"Error generating presigned URL for {object_name}: {e}")
            raise

    def list_files(self, prefix: str = "", max_files: int = 1000) -> list:
        """
        List files in storage with optional prefix filter

        Args:
            prefix: Filter files by prefix/path
            max_files: Maximum number of files to return

        Returns:
            List of file names/paths
        """
        try:
            files = []

            if self.storage_type == "minio":
                objects = self.client.list_objects(
                    self.bucket_name,
                    prefix=prefix,
                    recursive=True
                )
                for obj in objects:
                    files.append(obj.object_name)
                    if len(files) >= max_files:
                        break

            elif self.storage_type == "s3":
                paginator = self.client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

                for page in pages:
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            files.append(obj['Key'])
                            if len(files) >= max_files:
                                break
                    if len(files) >= max_files:
                        break

            return files

        except Exception as e:
            logger.error(f"Error listing files with prefix {prefix}: {e}")
            raise


# Singleton instance
_storage_service_instance = None


def get_storage_service() -> StorageService:
    """Get or create storage service singleton"""
    global _storage_service_instance
    if _storage_service_instance is None:
        _storage_service_instance = StorageService()
    return _storage_service_instance
