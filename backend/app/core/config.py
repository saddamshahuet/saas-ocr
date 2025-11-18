"""
Application configuration settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "SaaS OCR"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # API
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 0

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Storage (MinIO/S3)
    STORAGE_TYPE: str = "minio"  # minio or s3
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "saas-ocr"
    MINIO_SECURE: bool = False

    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "saas-ocr"

    # OCR Configuration
    OCR_LANGUAGE: str = "en"
    OCR_USE_GPU: bool = True
    OCR_MAX_WORKERS: int = 4
    OCR_BATCH_SIZE: int = 10

    # LLM Configuration
    LLM_MODEL_NAME: str = "llama3-8b"
    LLM_MODEL_PATH: str = "/models"
    LLM_USE_GPU: bool = True
    LLM_MAX_LENGTH: int = 4096
    LLM_TEMPERATURE: float = 0.0

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = "pdf,png,jpg,jpeg,tiff,tif"
    MAX_PAGES_PER_DOCUMENT: int = 100

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    CORS_ALLOW_CREDENTIALS: bool = True

    # Monitoring
    PROMETHEUS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"

    # HIPAA Compliance
    ENABLE_AUDIT_LOG: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 2555  # 7 years
    DATA_RETENTION_DAYS: int = 90
    ENABLE_ENCRYPTION_AT_REST: bool = True

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("ALLOWED_EXTENSIONS", pre=True)
    def parse_allowed_extensions(cls, v):
        """Parse allowed extensions from comma-separated string"""
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",")]
        return v

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert max upload size from MB to bytes"""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
