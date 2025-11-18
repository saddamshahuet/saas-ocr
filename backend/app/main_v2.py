"""
Main FastAPI application - Version 2 with all features integrated
Includes: Async processing, Storage, Auth, Payments, Analytics, Batch processing
"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid
import logging
from typing import Optional, List
from datetime import timedelta
import tempfile
import os
import io

from app.core.config import settings
from app.core.database import get_db, init_db
from app.core.security import create_access_token, verify_password, get_password_hash, generate_api_key
from app.api.dependencies import get_current_user, get_current_superuser, check_api_calls_remaining, get_optional_user
from app.models import User, Job, Document, APIKey, SchemaTemplate, Batch
from app.schemas.user import UserCreate, UserResponse, Token
from app.schemas.job import JobCreate, JobResponse, JobListResponse, JobStatus
from app.services.storage_service import get_storage_service
from app.services.analytics_service import get_analytics_service
from app.services.payment_service import get_payment_service
from app.services.celery_tasks import process_document_task, process_batch_task

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=f"{settings.APP_NAME} v2",
    version=settings.APP_VERSION,
    description="AI-powered OCR and structured data extraction for healthcare documents - Full Feature Set",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Startup/Shutdown Events ====================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Application started successfully (v2 with all features)")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "features": [
            "Async Processing (Celery)",
            "Cloud Storage (MinIO/S3)",
            "JWT & API Key Authentication",
            "Payment Integration (Stripe)",
            "Analytics & Reporting",
            "Batch Processing",
            "Webhook Delivery",
            "Custom Schemas"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": settings.APP_VERSION}


# ==================== Authentication Endpoints ====================

@app.post("/api/v1/register", response_model=UserResponse, tags=["Authentication"])
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user

    Creates a new user account with email and password.
    Returns user information with JWT token.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        organization=user_data.organization,
        is_active=True,
        is_verified=False,
        tier="starter",
        api_calls_remaining=10000,
        api_calls_total=10000,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {new_user.email}")
    return new_user


@app.post("/api/v1/login", response_model=Token, tags=["Authentication"])
async def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """
    Login and get access token

    Authenticate with email and password to receive a JWT token.
    """
    # Find user
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is inactive")

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    logger.info(f"User logged in: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/v1/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


# ==================== API Key Management ====================

@app.post("/api/v1/api-keys", tags=["API Keys"])
async def create_api_key(
    name: str = Form(..., description="Friendly name for this API key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key

    Generate a new API key for programmatic access.
    Save the returned key securely - it won't be shown again.
    """
    # Generate API key
    full_key, key_hash, key_prefix = generate_api_key()

    # Create API key record
    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=name,
        is_active=True
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info(f"API key created for user {current_user.email}: {key_prefix}...")

    return {
        "api_key": full_key,  # Only time this will be shown
        "key_prefix": key_prefix,
        "name": name,
        "created_at": api_key.created_at,
        "message": "Save this key securely. It will not be shown again."
    }


@app.get("/api/v1/api-keys", tags=["API Keys"])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all API keys for current user (without the actual keys)"""
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()

    return [
        {
            "id": key.id,
            "name": key.name,
            "key_prefix": key.key_prefix,
            "is_active": key.is_active,
            "last_used_at": key.last_used_at,
            "usage_count": key.usage_count,
            "created_at": key.created_at
        }
        for key in keys
    ]


@app.delete("/api/v1/api-keys/{key_id}", tags=["API Keys"])
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    db.delete(key)
    db.commit()

    return {"message": "API key revoked successfully"}


# ==================== Document Processing Endpoints ====================

@app.post("/api/v1/jobs", response_model=JobResponse, tags=["Processing"])
async def create_job(
    file: UploadFile = File(..., description="Document file (PDF, PNG, JPG, TIFF)"),
    document_type: Optional[str] = Form(None, description="Type of document"),
    schema_template: str = Form("medical_general", description="Schema template to use"),
    webhook_url: Optional[str] = Form(None, description="Webhook URL for completion notification"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload document and create processing job

    Uploads a document and processes it asynchronously with OCR and LLM extraction.
    Returns immediately with job ID for status tracking.
    """
    # Check API calls
    check_api_calls_remaining(current_user)

    # Validate file type
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Read file
    file_content = await file.read()
    file_size = len(file_content)

    # Check file size
    if file_size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Create job
    job_id = str(uuid.uuid4())
    new_job = Job(
        job_id=job_id,
        user_id=current_user.id,
        status="pending",
        document_type=document_type,
        schema_template=schema_template,
        webhook_url=webhook_url,
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Upload to storage
    storage_service = get_storage_service()
    storage_path = f"users/{current_user.id}/jobs/{job_id}/{file.filename}"

    try:
        storage_service.upload_file(
            file_data=io.BytesIO(file_content),
            object_name=storage_path,
            content_type=file.content_type or "application/octet-stream",
            metadata={
                "job_id": job_id,
                "user_id": str(current_user.id),
                "original_filename": file.filename
            }
        )
    except Exception as e:
        logger.error(f"Failed to upload file to storage: {e}")
        db.delete(new_job)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    # Create document record
    document = Document(
        job_id=new_job.id,
        filename=file.filename,
        original_filename=file.filename,
        file_size=file_size,
        file_type=file_extension,
        mime_type=file.content_type or "application/octet-stream",
        storage_path=storage_path,
        storage_bucket=settings.MINIO_BUCKET_NAME if settings.STORAGE_TYPE == "minio" else settings.S3_BUCKET_NAME,
        is_processed=False,
    )

    db.add(document)
    db.commit()

    # Download to temp file for processing
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}")
    temp_file.write(file_content)
    temp_file.close()

    # Queue async processing task
    process_document_task.delay(
        job_id=new_job.id,
        file_path=temp_file.name,
        file_type=file_extension,
        schema_template=schema_template
    )

    logger.info(f"Job {job_id} created and queued for processing")

    return new_job


@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse, tags=["Processing"])
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job status and results"""
    job = db.query(Job).filter(
        Job.job_id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@app.get("/api/v1/jobs", response_model=JobListResponse, tags=["Processing"])
async def list_jobs(
    page: int = 1,
    page_size: int = 20,
    status: Optional[JobStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all jobs for current user with pagination"""
    # Build query
    query = db.query(Job).filter(Job.user_id == current_user.id)

    if status:
        query = query.filter(Job.status == status.value)

    # Get total count
    total = query.count()

    # Paginate
    jobs = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    total_pages = (total + page_size - 1) // page_size

    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# ==================== Batch Processing ====================

@app.post("/api/v1/batches", tags=["Batch Processing"])
async def create_batch(
    files: List[UploadFile] = File(..., description="Multiple document files"),
    name: Optional[str] = Form(None),
    schema_template: str = Form("medical_general"),
    webhook_url: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a batch processing job

    Upload multiple documents for batch processing.
    All documents will be processed in parallel.
    """
    # Check API calls
    if current_user.api_calls_remaining < len(files):
        raise HTTPException(
            status_code=429,
            detail=f"Insufficient API calls. Need {len(files)}, have {current_user.api_calls_remaining}"
        )

    # Create batch
    batch_id = str(uuid.uuid4())
    batch = Batch(
        batch_id=batch_id,
        user_id=current_user.id,
        name=name or f"Batch {batch_id[:8]}",
        status="pending",
        total_jobs=len(files),
        schema_template=schema_template,
        webhook_url=webhook_url
    )

    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Create jobs for each file
    job_ids = []
    storage_service = get_storage_service()

    for file in files:
        # Validate file
        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            continue

        # Read file
        file_content = await file.read()

        # Create job
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            user_id=current_user.id,
            status="pending",
            schema_template=schema_template
        )

        db.add(job)
        db.flush()

        # Upload to storage
        storage_path = f"users/{current_user.id}/batches/{batch_id}/{file.filename}"
        storage_service.upload_file(
            file_data=io.BytesIO(file_content),
            object_name=storage_path,
            content_type=file.content_type or "application/octet-stream"
        )

        # Create document
        document = Document(
            job_id=job.id,
            filename=file.filename,
            original_filename=file.filename,
            file_size=len(file_content),
            file_type=file_extension,
            mime_type=file.content_type or "application/octet-stream",
            storage_path=storage_path,
            storage_bucket=settings.MINIO_BUCKET_NAME if settings.STORAGE_TYPE == "minio" else settings.S3_BUCKET_NAME
        )

        db.add(document)
        job_ids.append(job.id)

    db.commit()

    # Queue batch processing
    process_batch_task.delay(
        batch_id=batch_id,
        job_ids=job_ids,
        webhook_url=webhook_url
    )

    logger.info(f"Batch {batch_id} created with {len(job_ids)} jobs")

    return {
        "batch_id": batch_id,
        "status": "pending",
        "total_jobs": len(job_ids),
        "message": f"Batch created with {len(job_ids)} jobs"
    }


@app.get("/api/v1/batches/{batch_id}", tags=["Batch Processing"])
async def get_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get batch status"""
    batch = db.query(Batch).filter(
        Batch.batch_id == batch_id,
        Batch.user_id == current_user.id
    ).first()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    return {
        "batch_id": batch.batch_id,
        "name": batch.name,
        "status": batch.status,
        "total_jobs": batch.total_jobs,
        "completed_jobs": batch.completed_jobs,
        "failed_jobs": batch.failed_jobs,
        "progress_percentage": batch.progress_percentage,
        "success_rate": batch.success_rate,
        "created_at": batch.created_at
    }


# ==================== Analytics Endpoints ====================

@app.get("/api/v1/analytics/stats", tags=["Analytics"])
async def get_user_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive usage statistics for current user"""
    analytics = get_analytics_service(db)
    return analytics.get_user_stats(current_user.id)


@app.get("/api/v1/analytics/jobs-over-time", tags=["Analytics"])
async def get_jobs_over_time(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get job statistics over time"""
    analytics = get_analytics_service(db)
    return analytics.get_jobs_over_time(current_user.id, days)


@app.get("/api/v1/analytics/accuracy", tags=["Analytics"])
async def get_accuracy_by_type(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get average confidence scores by document type"""
    analytics = get_analytics_service(db)
    return analytics.get_accuracy_by_document_type(current_user.id)


@app.get("/api/v1/analytics/cost", tags=["Analytics"])
async def get_cost_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cost analysis"""
    analytics = get_analytics_service(db)
    return analytics.get_cost_analysis(current_user.id)


@app.get("/api/v1/analytics/errors", tags=["Analytics"])
async def get_error_analysis(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent errors for troubleshooting"""
    analytics = get_analytics_service(db)
    return analytics.get_error_analysis(current_user.id, limit)


# ==================== Payment Endpoints ====================

@app.get("/api/v1/pricing", tags=["Payments"])
async def get_pricing_tiers():
    """Get all pricing tiers"""
    payment_service = get_payment_service()
    return payment_service.get_all_tiers()


@app.post("/api/v1/checkout", tags=["Payments"])
async def create_checkout_session(
    tier: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """
    Create Stripe checkout session

    Create a payment checkout session for purchasing API call packages.
    """
    payment_service = get_payment_service()

    try:
        session = payment_service.create_checkout_session(
            tier=tier,
            success_url=f"{settings.CORS_ORIGINS[0]}/payment/success",
            cancel_url=f"{settings.CORS_ORIGINS[0]}/payment/cancel",
            customer_email=current_user.email,
            user_id=current_user.id
        )

        return session

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


# ==================== Admin Endpoints ====================

@app.get("/api/v1/admin/stats", tags=["Admin"])
async def get_system_stats(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Get system-wide statistics (admin only)"""
    analytics = get_analytics_service(db)
    return analytics.get_system_stats()


@app.get("/api/v1/admin/top-users", tags=["Admin"])
async def get_top_users(
    limit: int = 10,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """Get top users by usage (admin only)"""
    analytics = get_analytics_service(db)
    return analytics.get_top_users(limit)


# ==================== Simple Stats Endpoint (Backward Compatible) ====================

@app.get("/api/v1/stats")
async def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get simple usage statistics (backward compatible)"""
    analytics = get_analytics_service(db)
    stats = analytics.get_user_stats(current_user.id)

    # Simplified format
    return {
        "api_calls_remaining": current_user.api_calls_remaining,
        "api_calls_total": current_user.api_calls_total,
        "api_calls_used": current_user.api_calls_total - current_user.api_calls_remaining,
        "total_jobs": stats["jobs"]["total"],
        "completed_jobs": stats["jobs"]["completed"],
        "failed_jobs": stats["jobs"]["failed"],
        "tier": current_user.tier,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
