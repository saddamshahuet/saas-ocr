# SaaS OCR - Setup Guide

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- PostgreSQL 15+ (if running without Docker)
- Redis 7+ (if running without Docker)

### Option 1: Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd saas-ocr
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Check service status:**
   ```bash
   docker-compose ps
   ```

5. **View logs:**
   ```bash
   docker-compose logs -f app
   ```

6. **Access the application:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Frontend: Open `frontend/index.html` in your browser
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

### Option 2: Local Development

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install system dependencies (Ubuntu/Debian):**
   ```bash
   sudo apt-get update
   sudo apt-get install -y \
       libgomp1 \
       libglib2.0-0 \
       libsm6 \
       libxext6 \
       libxrender-dev \
       libgl1-mesa-glx \
       poppler-utils
   ```

3. **Start PostgreSQL and Redis:**
   ```bash
   # Using Docker for databases only
   docker-compose up -d postgres redis minio
   ```

4. **Run database migrations:**
   ```bash
   cd backend
   python -c "from app.core.database import init_db; init_db()"
   ```

5. **Start the FastAPI application:**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Open the frontend:**
   - Open `frontend/index.html` in your web browser

---

## Project Structure

```
saas-ocr/
├── backend/
│   └── app/
│       ├── api/                 # API route handlers
│       ├── core/                # Core configuration
│       │   ├── config.py        # Settings
│       │   ├── database.py      # Database connection
│       │   └── security.py      # Auth utilities
│       ├── models/              # SQLAlchemy models
│       │   ├── user.py
│       │   ├── job.py
│       │   ├── document.py
│       │   └── audit_log.py
│       ├── schemas/             # Pydantic schemas
│       ├── services/            # Business logic
│       │   ├── ocr_service.py   # OCR processing
│       │   └── llm_service.py   # LLM extraction
│       ├── utils/               # Utilities
│       └── main.py              # FastAPI app
├── frontend/
│   └── index.html               # Web interface
├── docs/                        # Documentation
│   ├── PRD.md
│   ├── Business-Use-Cases.md
│   └── Unique-Selling-Points.md
├── storage/                     # Local file storage
├── tests/                       # Test suite
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image
├── docker-compose.yml           # Multi-container setup
└── .env.example                 # Environment template
```

---

## API Usage

### 1. Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe",
    "organization": "Healthcare Corp"
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=user@example.com&password=securepassword123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Upload Document for Processing

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -F "file=@/path/to/document.pdf" \
  -F "schema_template=medical_general" \
  -F "document_type=hospice_admission"
```

Response:
```json
{
  "id": 1,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "extracted_data": {
    "patient_demographics": {
      "patient_name": "Jane Smith",
      "date_of_birth": "01/15/1945",
      "gender": "Female"
    },
    "medical_information": {
      "primary_diagnosis": "Congestive Heart Failure",
      "medications": [
        {"medication": "Furosemide 40mg PO daily"},
        {"medication": "Metoprolol 25mg PO BID"}
      ],
      "allergies": ["Penicillin"]
    }
  },
  "confidence_scores": {
    "patient_demographics.patient_name": 0.95,
    "patient_demographics.date_of_birth": 0.92
  }
}
```

### 4. Get Job Status

```bash
curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}"
```

### 5. List Jobs

```bash
curl -X GET "http://localhost:8000/api/v1/jobs?page=1&page_size=20&status=completed"
```

### 6. Get Usage Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/stats"
```

---

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `SECRET_KEY` | JWT secret key | **CHANGE IN PRODUCTION** |
| `OCR_USE_GPU` | Enable GPU acceleration | `True` |
| `OCR_LANGUAGE` | OCR language | `en` |
| `LLM_MODEL_NAME` | LLM model to use | `llama3-8b` |
| `MAX_UPLOAD_SIZE_MB` | Max file size | `50` |
| `ALLOWED_EXTENSIONS` | Allowed file types | `pdf,png,jpg,jpeg,tiff` |

### Supported Document Types

- **PDF**: Multi-page documents
- **Images**: PNG, JPG, JPEG, TIFF

### Supported Schema Templates

1. **medical_general**: General medical documents
2. **hospice**: Hospice-specific forms
3. **home_health**: Home health assessments

---

## Testing

### Run Unit Tests

```bash
cd backend
pytest tests/ -v
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

### Test API Endpoints

Use the interactive API documentation:
- Open http://localhost:8000/docs
- Click "Try it out" on any endpoint
- Fill in parameters and execute

---

## Production Deployment

### Security Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DEBUG=False`
- [ ] Use HTTPS (TLS/SSL certificates)
- [ ] Enable database connection pooling
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Enable audit logging
- [ ] Configure backup strategy
- [ ] Review CORS settings
- [ ] Enable rate limiting
- [ ] Set up monitoring (Prometheus/Grafana)

### Scaling

1. **Horizontal Scaling:**
   - Deploy multiple app instances behind load balancer
   - Use separate Celery workers for async processing

2. **GPU Optimization:**
   - Use GPU-enabled instances for OCR/LLM processing
   - Configure CUDA and appropriate drivers

3. **Database:**
   - Enable connection pooling
   - Set up read replicas for reporting
   - Configure automatic backups

4. **Storage:**
   - Use S3 or S3-compatible storage (MinIO)
   - Enable versioning and lifecycle policies

---

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U postgres -d saas_ocr
```

### OCR Processing Errors

```bash
# Check if poppler is installed (for PDF processing)
which pdftoppm

# Test OCR service
python -c "from app.services.ocr_service import get_ocr_service; ocr = get_ocr_service(use_gpu=False)"
```

### Memory Issues

If you encounter OOM errors:

1. Reduce `OCR_MAX_WORKERS` in `.env`
2. Use CPU instead of GPU: `OCR_USE_GPU=False`
3. Process smaller batches: `OCR_BATCH_SIZE=5`

### File Upload Errors

- Check `MAX_UPLOAD_SIZE_MB` setting
- Verify file extension is in `ALLOWED_EXTENSIONS`
- Check disk space in storage directory

---

## Development

### Adding New Schema Templates

1. Create schema definition in `backend/app/schemas/`
2. Add extraction logic in `backend/app/services/llm_service.py`
3. Update schema dropdown in `frontend/index.html`

### Adding New Document Types

1. Add document type to models
2. Implement specialized extraction logic
3. Create test cases

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit pull request

---

## Support

For issues, questions, or contributions:
- GitHub Issues: [Create an issue]
- Documentation: See `/docs` directory
- Email: support@example.com

---

## License

This project is open source under the MIT License. See LICENSE file for details.
