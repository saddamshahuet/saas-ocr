# SaaS OCR Platform - Deployment Guide

## Overview

This guide covers the complete deployment of the SaaS OCR platform from scratch, including database schema creation and comprehensive seed data representing 2-3 years of production usage.

## Single Script Deployment

The platform provides a **single deployment script** that handles everything:
- ✅ Database schema creation (all tables)
- ✅ Comprehensive RBAC system setup (permissions, roles)
- ✅ Production-ready seed data (75,000+ jobs, 150,000+ audit logs, etc.)
- ✅ Multi-tenant organizations (60 organizations across all tiers)
- ✅ Realistic user base (750+ users)
- ✅ Historical data spanning 2.5 years

## Quick Start

### Prerequisites

1. **PostgreSQL Database Running**
   ```bash
   # Using Docker (recommended)
   docker-compose up -d postgres redis minio

   # Or install PostgreSQL locally
   # Ensure PostgreSQL 15+ is running on localhost:5432
   ```

2. **Environment Configuration**
   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit .env and configure:
   # - DATABASE_URL (PostgreSQL connection string)
   # - SECRET_KEY (JWT signing key)
   # - MinIO/S3 credentials
   # - OCR API keys (optional for initial deployment)
   ```

3. **Python Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

### Deployment Options

#### Option 1: Full Deployment (Recommended)

Deploy the complete system with all seed data:

```bash
cd backend
python deploy_with_seed_data.py
```

This will:
- Create all database tables
- Generate 60 organizations (starter, pro, enterprise tiers)
- Create 750+ users across organizations
- Generate 75,000+ OCR jobs representing 2.5 years
- Create 150,000+ audit log entries
- Set up complete RBAC system
- **Time estimate: 5-10 minutes**

#### Option 2: Fresh Start (Drop Existing)

**⚠️ WARNING: This will delete ALL existing data!**

```bash
cd backend
python deploy_with_seed_data.py --drop-existing
```

The script will prompt for confirmation before dropping the database.

#### Option 3: Schema Only (No Seed Data)

Create only the database schema without seed data:

```bash
cd backend
python deploy_with_seed_data.py --skip-seed
```

Use this for:
- Production deployments where you'll import real data
- Custom data generation scenarios
- Testing schema migrations

## Seed Data Details

### Organizations (60 Total)

| Tier | Count | API Calls Limit | Storage Limit | Features |
|------|-------|----------------|---------------|----------|
| **Enterprise** | 15 | 1,000,000/month | 5 TB | All features, SSO, Advanced OCR |
| **Pro** | 25 | 100,000/month | 500 GB | Batch processing, Custom schemas |
| **Starter** | 20 | 10,000/month | 50 GB | Basic features |

**Sample Organizations:**
- `acme-corp` (Enterprise) - Technology leader
- `global-finance` (Enterprise) - International banking
- `startuphub` (Pro) - Startup accelerator
- `design-studio` (Pro) - Creative agency
- `startup-alpha` (Starter) - Early-stage tech startup

### Users (750+ Total)

- **1 Superuser**: `admin@saasocr.com` (system administrator)
- **750+ Organization Users**: Distributed across organizations
  - Enterprise orgs: 15-25 users each
  - Pro orgs: 5-15 users each
  - Starter orgs: 2-5 users each

**Roles Distribution:**
- Organization Owners (1 per org)
- Admins (1-2 per org)
- Managers (2-5 per larger orgs)
- Members (majority of users)
- Viewers (read-only access)

**Default Password:** `Password123!` (for all demo users)

### Workspaces (150+ Total)

Workspaces organize teams within organizations:
- Enterprise: 5-10 workspaces (Engineering, Marketing, Sales, etc.)
- Pro: 2-5 workspaces
- Starter: 1-3 workspaces

### OCR Jobs (75,000+ Total)

Realistic job distribution over 2.5 years:
- **Status**: 80% completed, 15% failed, 5% processing
- **Document Types**: Invoice, Receipt, Tax Forms, ID Documents, Financial, Medical, etc.
- **Pages**: 1-50 pages per job (weighted toward 1-5 pages)
- **Processing Time**: 1.5-45 seconds per job
- **Extracted Data**: Realistic structured data based on document type
- **Confidence Scores**: 75-99% per field

**Timeline**: Jobs distributed evenly from 2.5 years ago to present

### Documents (75,000+ Total)

One document per job:
- **File Types**: PDF (60%), PNG (20%), JPG (15%), TIFF (5%)
- **File Sizes**: 50 KB - 10 MB
- **Storage**: Organized by org/year/month structure
- **Processing Status**: 80% processed, 20% pending/failed

### Schema Templates (80+ Total)

Pre-configured extraction schemas:
- Invoice (Standard, Medical)
- Receipt (Retail, Restaurant)
- Tax Forms (W-2, 1099)
- ID Documents (Driver License, Passport)
- Financial (Bank Statement)
- Medical (Records, Lab Results)
- Procurement (Purchase Order)
- Shipping (Packing Slip)

### API Keys (500+ Total)

- **Distribution**: Based on org tier (Enterprise: 5-15, Pro: 2-8, Starter: 1-3)
- **Status**: 90% active, 10% revoked
- **Usage**: 80% of active keys have usage history
- **IP Restrictions**: 30% have IP whitelisting enabled

### Batch Operations (800+ Total)

Available for Pro and Enterprise tiers:
- **Status**: 75% completed, 20% processing, 5% failed
- **Size**: 10-500 jobs per batch
- **Success Rate**: 95% average success rate
- **Use Cases**: Monthly invoices, quarterly documents, year-end tax forms

### Audit Logs (150,000+ Total)

Complete audit trail for HIPAA compliance:
- **Actions**: Document operations, job creation, user management, API access
- **IP Addresses**: Realistic IP distribution
- **User Agents**: Web browsers, API clients, cURL, Postman
- **Status Codes**: 95% success (200-204), 5% errors (400-500)
- **Timeline**: Distributed over 2.5 years

### RBAC System

**36 Permissions** across resources:
- Documents (read, write, delete, manage)
- Jobs (read, write, delete, manage)
- Users (read, write, delete, manage)
- Organization (read, write, manage, billing)
- Workspaces (read, write, delete, manage)
- API Keys (read, write, delete, manage)
- Schemas (read, write, delete, manage)
- Audit Logs (read, manage)
- Roles & Permissions (read, write, manage)

**12 Roles**:
- System Roles: Super Admin, Organization Owner, Admin, Manager, Member, Viewer
- Custom Roles: Billing Admin, API User, Schema Designer, Auditor, Workspace Manager, Developer

## Post-Deployment

### Verify Deployment

Check the deployment statistics printed at the end:

```
Database Statistics:
  - Organizations: 60
  - Users: 750+
  - Workspaces: 150+
  - Jobs: 75,000+
  - Documents: 75,000+
  - API Keys: 500+
  - Schema Templates: 80+
  - Batches: 800+
  - Audit Logs: 150,000+
  - Permissions: 36
  - Roles: 12
```

### Test Login

1. **Superuser Access**
   ```
   Email: admin@saasocr.com
   Password: Password123!
   ```

2. **Organization Users**
   ```
   Email: [any-user]@[org-slug].com
   Password: Password123!

   Examples:
   - john.smith.0@acme-corp.com
   - jane.johnson.0@startuphub.com
   ```

### Start the Application

```bash
# Option 1: Using Docker Compose
docker-compose up -d

# Option 2: Local development
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Application will be available at:
# http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Verify API Access

```bash
# Health check
curl http://localhost:8000/health

# Get API documentation
curl http://localhost:8000/docs

# Login as superuser
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@saasocr.com", "password": "Password123!"}'
```

## Database Management

### Connect to Database

```bash
# Using psql
psql postgresql://postgres:postgres@localhost:5432/saas_ocr

# Using Docker
docker-compose exec postgres psql -U postgres -d saas_ocr
```

### Useful Queries

```sql
-- Count records by table
SELECT
  'Organizations' as table_name, COUNT(*) as count FROM organizations
UNION ALL
SELECT 'Users', COUNT(*) FROM users
UNION ALL
SELECT 'Jobs', COUNT(*) FROM jobs
UNION ALL
SELECT 'Documents', COUNT(*) FROM documents
UNION ALL
SELECT 'Audit Logs', COUNT(*) FROM audit_logs;

-- View organization summary
SELECT
  tier,
  COUNT(*) as org_count,
  SUM(api_calls_used) as total_api_calls,
  ROUND(AVG(storage_used_gb)::numeric, 2) as avg_storage_gb
FROM organizations
GROUP BY tier
ORDER BY tier;

-- View job statistics
SELECT
  status,
  COUNT(*) as count,
  ROUND(AVG(processing_time_seconds)::numeric, 2) as avg_processing_time
FROM jobs
GROUP BY status
ORDER BY count DESC;

-- View most active users (by jobs created)
SELECT
  u.email,
  u.full_name,
  o.name as organization,
  COUNT(j.id) as total_jobs
FROM users u
LEFT JOIN jobs j ON j.user_id = u.id
LEFT JOIN organizations o ON o.id = u.default_organization_id
GROUP BY u.id, u.email, u.full_name, o.name
ORDER BY total_jobs DESC
LIMIT 10;
```

## Backup and Restore

### Backup Database

```bash
# Full database backup
docker-compose exec postgres pg_dump -U postgres saas_ocr > backup_$(date +%Y%m%d).sql

# Or using local pg_dump
pg_dump postgresql://postgres:postgres@localhost:5432/saas_ocr > backup.sql
```

### Restore Database

```bash
# Drop and recreate database
docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS saas_ocr;"
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE saas_ocr;"

# Restore from backup
docker-compose exec -T postgres psql -U postgres saas_ocr < backup.sql
```

## Production Deployment Checklist

- [ ] Change default passwords for all demo users
- [ ] Update `SECRET_KEY` in environment variables
- [ ] Configure production database (managed PostgreSQL recommended)
- [ ] Set up MinIO/S3 with proper access controls
- [ ] Configure SMTP for email notifications
- [ ] Enable SSL/TLS for all connections
- [ ] Set up monitoring and alerting
- [ ] Configure backup automation
- [ ] Review and adjust RBAC permissions
- [ ] Set up rate limiting and DDoS protection
- [ ] Configure CDN for static assets
- [ ] Enable audit log retention policies (HIPAA: 7 years)
- [ ] Set up disaster recovery procedures

## Troubleshooting

### "Database connection refused"

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Start PostgreSQL
docker-compose up -d postgres

# Check connection
psql postgresql://postgres:postgres@localhost:5432/postgres -c "SELECT 1"
```

### "Permission denied for table"

**Solution:**
```bash
# Grant all permissions
docker-compose exec postgres psql -U postgres saas_ocr -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;"
docker-compose exec postgres psql -U postgres saas_ocr -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;"
```

### "Out of memory during seed data generation"

**Solution:**
The script processes data in batches of 5,000-10,000 records. If you still encounter memory issues:

1. Increase Docker memory limit (if using Docker)
2. Run with `--skip-seed` and generate data manually in smaller batches
3. Reduce the total number of jobs in the script (edit `total_jobs = 75000` to a smaller number)

### "Script takes too long"

**Expected Duration:** 5-10 minutes for full deployment

**To speed up:**
- Use SSD storage
- Ensure PostgreSQL has sufficient resources
- Run on a machine with 8GB+ RAM
- Consider using `--skip-seed` for testing

## Support

For issues or questions:
- Check the troubleshooting section above
- Review application logs: `docker-compose logs -f app`
- Database logs: `docker-compose logs -f postgres`
- Create an issue in the project repository

## Next Steps

After successful deployment:
1. Explore the API documentation at `/docs`
2. Test OCR processing with sample documents
3. Configure webhooks for job notifications
4. Set up monitoring and alerting
5. Customize RBAC roles and permissions
6. Configure organization-specific settings
7. Set up automated backups

## License

This deployment script and seed data are part of the SaaS OCR Platform.
For production use, ensure compliance with all applicable licenses and regulations.
