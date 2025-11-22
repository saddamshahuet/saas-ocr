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
from app.services.language_service import get_language_manager
from app.services.ehr_service import EHRConnector, EHRStandard
from app.services.review_service import get_review_queue, ReviewStatus

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


# ==================== Language Detection Endpoint ====================

@app.post("/api/v1/detect-language")
async def detect_language(text: str = Form(...)):
    """
    Detect language from text

    Args:
        text: Text to analyze for language detection

    Returns:
        Detected languages with confidence scores
    """
    try:
        language_manager = get_language_manager()

        # Detect languages
        detected = language_manager.detect_language(text, top_n=3)

        # Get additional info for top language
        if detected:
            top_lang = detected[0]['lang']
            config = language_manager.auto_detect_and_configure(text)

            return {
                "detected_languages": detected,
                "primary_language": {
                    "code": config['detected_language'],
                    "name": config['language_name'],
                    "confidence": config['confidence'],
                    "ocr_language": config['ocr_language'],
                    "supported": config['supported']
                },
                "all_supported_languages": [
                    {"code": code, "name": cfg.name}
                    for code, cfg in language_manager.get_all_supported_languages().items()
                ]
            }
        else:
            return {
                "detected_languages": [],
                "primary_language": None,
                "error": "Unable to detect language"
            }

    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Language detection failed: {str(e)}")


# ==================== EHR Export Endpoints ====================

@app.post("/api/v1/jobs/{job_id}/export/hl7")
async def export_to_hl7(
    job_id: str,
    patient_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Export job results to HL7 v2 format

    Args:
        job_id: Job ID
        patient_id: Patient ID for HL7 message

    Returns:
        HL7 v2 message
    """
    # Get job
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.extracted_data:
        raise HTTPException(status_code=400, detail="No extracted data available")

    try:
        # Create EHR connector
        connector = EHRConnector(ehr_standard=EHRStandard.HL7_V2)

        # Convert to HL7
        hl7_message = connector.convert_extracted_data_to_hl7(
            extracted_data=job.extracted_data,
            patient_id=patient_id
        )

        return {
            "success": True,
            "format": "HL7 v2",
            "message": hl7_message.to_string()
        }

    except Exception as e:
        logger.error(f"HL7 export failed: {e}")
        raise HTTPException(status_code=500, detail=f"HL7 export failed: {str(e)}")


@app.post("/api/v1/jobs/{job_id}/export/fhir")
async def export_to_fhir(
    job_id: str,
    patient_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Export job results to FHIR R4 format

    Args:
        job_id: Job ID
        patient_id: Patient ID for FHIR resources

    Returns:
        FHIR Bundle resource
    """
    # Get job
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.extracted_data:
        raise HTTPException(status_code=400, detail="No extracted data available")

    try:
        # Create EHR connector
        connector = EHRConnector(ehr_standard=EHRStandard.FHIR_R4)

        # Convert to FHIR
        fhir_bundle = connector.convert_extracted_data_to_fhir(
            extracted_data=job.extracted_data,
            patient_id=patient_id,
            document_id=job_id
        )

        return {
            "success": True,
            "format": "FHIR R4",
            "bundle": fhir_bundle
        }

    except Exception as e:
        logger.error(f"FHIR export failed: {e}")
        raise HTTPException(status_code=500, detail=f"FHIR export failed: {str(e)}")


@app.post("/api/v1/jobs/{job_id}/send-to-ehr")
async def send_to_ehr(
    job_id: str,
    patient_id: str = Form(...),
    ehr_endpoint: str = Form(...),
    ehr_format: str = Form("fhir"),  # "hl7" or "fhir"
    api_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Send job results directly to EHR system

    Args:
        job_id: Job ID
        patient_id: Patient ID
        ehr_endpoint: EHR API endpoint URL
        ehr_format: EHR format ("hl7" or "fhir")
        api_key: Optional API key for authentication

    Returns:
        Result of sending to EHR
    """
    # Get job
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    if not job.extracted_data:
        raise HTTPException(status_code=400, detail="No extracted data available")

    try:
        # Determine EHR standard
        if ehr_format.lower() == "hl7":
            ehr_standard = EHRStandard.HL7_V2
        elif ehr_format.lower() == "fhir":
            ehr_standard = EHRStandard.FHIR_R4
        else:
            raise ValueError(f"Unsupported EHR format: {ehr_format}")

        # Create EHR connector
        connector = EHRConnector(
            ehr_standard=ehr_standard,
            endpoint_url=ehr_endpoint,
            api_key=api_key
        )

        # Convert data
        if ehr_standard == EHRStandard.HL7_V2:
            data = connector.convert_extracted_data_to_hl7(
                extracted_data=job.extracted_data,
                patient_id=patient_id
            )
        else:
            data = connector.convert_extracted_data_to_fhir(
                extracted_data=job.extracted_data,
                patient_id=patient_id,
                document_id=job_id
            )

        # Send to EHR
        result = connector.send_to_ehr(data)

        return result

    except Exception as e:
        logger.error(f"Failed to send to EHR: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send to EHR: {str(e)}")


# ==================== Review Queue Endpoints (Human-in-Loop) ====================

@app.get("/api/v1/review/queue")
async def get_review_items(limit: int = 10):
    """Get pending review items"""
    try:
        review_queue = get_review_queue()
        items = review_queue.get_pending_items(limit=limit)

        return {
            "success": True,
            "items": [item.to_dict() for item in items],
            "count": len(items)
        }
    except Exception as e:
        logger.error(f"Failed to get review items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/review/{item_id}/approve")
async def approve_review_item(
    item_id: str,
    suggested_value: str = Form(None),
    notes: str = Form("")
):
    """Approve a review item"""
    try:
        review_queue = get_review_queue()
        item = review_queue.get_item(item_id)

        if not item:
            raise HTTPException(status_code=404, detail="Review item not found")

        # Use suggested value if provided, otherwise use extracted value
        final_value = suggested_value if suggested_value else item.extracted_value

        success = review_queue.update_item(
            item_id=item_id,
            suggested_value=final_value,
            reviewer_notes=notes,
            status=ReviewStatus.APPROVED
        )

        return {"success": success, "message": "Item approved"}

    except Exception as e:
        logger.error(f"Failed to approve review item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/review/{item_id}/reject")
async def reject_review_item(
    item_id: str,
    notes: str = Form(...)
):
    """Reject a review item"""
    try:
        review_queue = get_review_queue()

        success = review_queue.update_item(
            item_id=item_id,
            suggested_value=None,
            reviewer_notes=notes,
            status=ReviewStatus.REJECTED
        )

        return {"success": success, "message": "Item rejected"}

    except Exception as e:
        logger.error(f"Failed to reject review item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/review/stats")
async def get_review_stats():
    """Get review queue statistics"""
    try:
        review_queue = get_review_queue()
        stats = review_queue.get_statistics()

        return {"success": True, "stats": stats}

    except Exception as e:
        logger.error(f"Failed to get review stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Mobile App APIs ====================

@app.post("/api/mobile/v1/jobs")
async def mobile_create_job(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Mobile-optimized job creation endpoint
    Simplified response for mobile apps
    """
    # Reuse existing job creation logic
    job = await create_job(
        file=file,
        document_type=document_type,
        schema_template="medical_general",
        webhook_url=None,
        db=db
    )

    # Return simplified response for mobile
    return {
        "job_id": job.job_id,
        "status": job.status,
        "message": "Document uploaded successfully"
    }


@app.get("/api/mobile/v1/jobs/{job_id}")
async def mobile_get_job(job_id: str, db: Session = Depends(get_db)):
    """
    Mobile-optimized job status endpoint
    Returns simplified status information
    """
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Simplified response for mobile
    response = {
        "job_id": job.job_id,
        "status": job.status,
        "progress": int((job.pages_processed / job.total_pages * 100) if job.total_pages else 0)
    }

    # Include results if completed
    if job.status == "completed":
        response["results"] = {
            "patient_name": job.extracted_data.get("patient_name") if job.extracted_data else None,
            "confidence": sum(job.confidence_scores.values()) / len(job.confidence_scores) if job.confidence_scores else 0
        }

    return response


@app.get("/api/mobile/v1/recent-jobs")
async def mobile_recent_jobs(limit: int = 5, db: Session = Depends(get_db)):
    """Get recent jobs for mobile app"""
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not authenticated")

    jobs = db.query(Job).filter(Job.user_id == user.id).order_by(
        Job.created_at.desc()
    ).limit(limit).all()

    return {
        "jobs": [
            {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None
            }
            for job in jobs
        ]
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
