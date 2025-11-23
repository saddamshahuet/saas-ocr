# AI-Powered OCR & Data Extraction Service for Hospice & Palliative Care

## Overview
This project aims to build an **AI-driven OCR and structured data extraction service** tailored for hospice and palliative care. The system will process a wide range of document types (scanned PDFs, Word docs, images, handwritten or printed text, mixed layouts, etc.) and extract key information such as:
- Patient Name
- Date of Birth (DoB)
- Allergies
- Carer Information
- Other relevant structured attributes

Extracted data will be output in a **well-defined JSON schema** (customizable per use case).

## Motivation & Opportunity
Currently, the client is considering using the Google Gemini API for document processing and data extraction. However, this approach incurs costs based on token usage and relies on a third-party service. This project explores the opportunity to:
- **Self-host** or **cloud-host** an open-source OCR + LLM pipeline
- Offer the solution as a **Python API service** with structured JSON output
- Monetize via **per-API call** or **per-token usage** billing

## Key Challenges
- High compute requirements for OCR + LLM models (need for GPU/TPU)
- Local hosting is not feasible; cloud-based AI hosting is required
- Need to identify cost-effective, scalable, and flexible cloud providers

## Research & Deliverables
1. **AI Model Research**
	- Identify models capable of OCR + structured extraction
	- Must support long, multi-page, mixed-format documents and long prompts
	- Compare open-source and proprietary models (e.g., Gemini, GPT-4, Claude, Llama 3, Donut, LayoutLMv3)

2. **Cloud/Hosting Platforms**
	- Research 10–15 cloud platforms offering GPU/TPU-based AI hosting
	- Document machine specs, pricing, and service models (hourly, serverless, dedicated)

3. **Comparison Matrix**
	- Tabular comparison of platforms: specs, pricing, flexibility, limitations

4. **Financial Model**
	- Estimate cost per document/API call for different scenarios
	- Suggest client pricing models (per document, page, API call, or token)

5. **Implementation Options**
	- Analyze feasibility of fixed vs on-demand cloud hosting
	- Evaluate trade-offs: cost, latency, availability, scaling

## Goal
Produce a **comprehensive feasibility study and business model plan** covering technical model selection, hosting provider comparison, and financial viability for an AI-powered OCR and data extraction service in the hospice and palliative care sector.

---

## 🚀 Quick Start - Deployment

### One-Command Deployment

Deploy the complete SaaS OCR platform with a single command:

```bash
./deploy.sh
```

This will:
- ✅ Create all database tables and schema
- ✅ Generate 60 organizations (Enterprise, Pro, Starter tiers)
- ✅ Create 750+ users with realistic roles
- ✅ Generate 75,000+ OCR jobs representing 2.5 years of usage
- ✅ Create 150,000+ audit log entries (HIPAA compliant)
- ✅ Set up complete RBAC system (36 permissions, 12 roles)
- ✅ **Ready for production in 5-10 minutes!**

### Prerequisites

```bash
# 1. Start required services
docker-compose up -d postgres redis minio

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Run deployment
./deploy.sh
```

### Deployment Options

```bash
# Full deployment with seed data (default)
./deploy.sh --full

# Fresh start (WARNING: deletes existing data)
./deploy.sh --fresh

# Schema only (no seed data)
./deploy.sh --schema-only
```

### Access the Platform

After deployment:

```bash
# Start the application
docker-compose up -d

# Access API documentation
open http://localhost:8000/docs
```

**Login Credentials:**
- Email: `admin@saasocr.com`
- Password: `Password123!`

### 📖 Detailed Documentation

For comprehensive deployment information, troubleshooting, and production setup:

**[📚 Read DEPLOYMENT.md](./DEPLOYMENT.md)**

Includes:
- Complete seed data details (organizations, users, jobs, etc.)
- Database management and queries
- Backup and restore procedures
- Production deployment checklist
- Troubleshooting guide
- Post-deployment configuration

---

## Architecture Overview

### Database Schema

The platform uses PostgreSQL with the following core tables:
- **Organizations** - Multi-tenant organization management
- **Users** - User accounts with email/password authentication
- **Workspaces** - Team organization within organizations
- **Jobs** - OCR processing jobs
- **Documents** - Uploaded document files
- **Schema Templates** - Custom extraction schemas
- **API Keys** - API authentication
- **Audit Logs** - HIPAA-compliant audit trail
- **RBAC** - Roles, Permissions, and access control

### Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **Cache**: Redis
- **Storage**: MinIO (S3-compatible)
- **Task Queue**: Celery
- **OCR**: Tesseract + Azure Document Intelligence
- **LLM**: OpenAI GPT-4 / Anthropic Claude
- **Deployment**: Docker + Docker Compose