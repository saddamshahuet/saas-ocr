"""Main FastAPI application"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid
import logging
from typing import Optional, List

from app.core.config import settings
from app.core.database import get_db, init_db
from app.core.security import create_access_token, verify_password, get_password_hash
from app.models import User, Job, Document
from app.schemas.user import UserCreate, UserResponse, Token
from app.schemas.job import JobCreate, JobResponse, JobListResponse
from app.services.ocr_service import get_ocr_service
from app.services.llm_service import get_llm_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered OCR and structured data extraction for healthcare documents",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Application started successfully")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ==================== Authentication Endpoints ====================

@app.post("/api/v1/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
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


@app.post("/api/v1/login", response_model=Token)
async def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """Login and get access token"""
    # Find user
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is inactive")

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    logger.info(f"User logged in: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/v1/me", response_model=UserResponse)
async def get_current_user(db: Session = Depends(get_db)):
    """Get current user information"""
    # NOTE: In production, add proper JWT authentication dependency
    # For MVP, return first user
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ==================== Job/Document Processing Endpoints ====================

@app.post("/api/v1/jobs", response_model=JobResponse)
async def create_job(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    schema_template: str = Form("medical_general"),
    webhook_url: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a document and create a processing job

    Args:
        file: Document file (PDF, PNG, JPG, etc.)
        document_type: Type of document (optional)
        schema_template: Schema template to use for extraction
        webhook_url: Webhook URL for completion notification (optional)

    Returns:
        Job information
    """
    # Get current user (simplified for MVP)
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Check API calls remaining
    if user.api_calls_remaining <= 0:
        raise HTTPException(status_code=429, detail="API call limit exceeded")

    # Validate file type
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Create job
    job_id = str(uuid.uuid4())
    new_job = Job(
        job_id=job_id,
        user_id=user.id,
        status="pending",
        document_type=document_type,
        schema_template=schema_template,
        webhook_url=webhook_url,
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Save uploaded file
    import os
    import tempfile
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    file_size = len(content)

    # Create document record
    document = Document(
        job_id=new_job.id,
        filename=file.filename,
        original_filename=file.filename,
        file_size=file_size,
        file_type=file_extension,
        mime_type=file.content_type or "application/octet-stream",
        storage_path=file_path,
        storage_bucket="local",
        is_processed=False,
    )

    db.add(document)
    db.commit()

    # Process document (in production, this would be async via Celery)
    try:
        # Update job status
        new_job.status = "processing"
        db.commit()

        # Run OCR
        logger.info(f"Processing document: {file.filename}")
        ocr_service = get_ocr_service(
            use_gpu=settings.OCR_USE_GPU,
            language=settings.OCR_LANGUAGE
        )

        ocr_result = ocr_service.process_document(
            file_path=file_path,
            file_type=file_extension,
            preprocess=True
        )

        # Extract structured data using LLM
        llm_service = get_llm_service(
            model_name=settings.LLM_MODEL_NAME,
            use_gpu=settings.LLM_USE_GPU
        )

        extraction_result = llm_service.extract_structured_data(
            text=ocr_result["raw_text"],
            schema_template=schema_template
        )

        # Update job with results
        new_job.status = "completed"
        new_job.total_pages = ocr_result["total_pages"]
        new_job.pages_processed = ocr_result["total_pages"]
        new_job.raw_text = ocr_result["raw_text"]
        new_job.extracted_data = extraction_result["extracted_data"]
        new_job.confidence_scores = extraction_result["confidence_scores"]

        document.is_processed = True

        # Decrement API calls
        user.api_calls_remaining -= 1

        db.commit()
        db.refresh(new_job)

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        new_job.status = "failed"
        new_job.error_message = str(e)
        db.commit()

    return new_job


@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get job status and results"""
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@app.get("/api/v1/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all jobs for the current user"""
    # Get current user (simplified for MVP)
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Build query
    query = db.query(Job).filter(Job.user_id == user.id)

    if status:
        query = query.filter(Job.status == status)

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


# ==================== Statistics Endpoint ====================

@app.get("/api/v1/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get usage statistics"""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated")

    total_jobs = db.query(Job).filter(Job.user_id == user.id).count()
    completed_jobs = db.query(Job).filter(
        Job.user_id == user.id,
        Job.status == "completed"
    ).count()
    failed_jobs = db.query(Job).filter(
        Job.user_id == user.id,
        Job.status == "failed"
    ).count()

    return {
        "api_calls_remaining": user.api_calls_remaining,
        "api_calls_total": user.api_calls_total,
        "api_calls_used": user.api_calls_total - user.api_calls_remaining,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "tier": user.tier,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
