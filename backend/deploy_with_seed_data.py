#!/usr/bin/env python3
"""
SaaS OCR Platform - Complete Deployment & Seed Data Script
===========================================================

This script performs a complete deployment of the SaaS OCR platform including:
1. Database schema creation (all tables)
2. Comprehensive seed data representing 2-3 years of production usage

Usage:
    python deploy_with_seed_data.py [--drop-existing] [--skip-seed]

Options:
    --drop-existing    Drop existing database before creating (WARNING: destructive)
    --skip-seed        Only create schema, skip seed data generation

Seed Data Statistics:
- 60 Organizations (20 starter, 25 pro, 15 enterprise)
- 750+ Users across all organizations
- 150+ Workspaces
- 75,000+ OCR Jobs (2.5 years of processing)
- 75,000+ Documents
- 500+ API Keys
- 150,000+ Audit Log entries
- 80+ Schema Templates
- 800+ Batch Operations
- Complete RBAC system (30+ permissions, 10+ roles)

Requirements:
- PostgreSQL database running
- All environment variables configured (.env file)
- Python dependencies installed (requirements.txt)
"""

import sys
import os
import random
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any
import argparse

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

# Import all models
from app.models.base import Base
from app.models.user import User
from app.models.organization import Organization, OrganizationMember, Workspace, WorkspaceMember
from app.models.job import Job
from app.models.document import Document
from app.models.api_key import APIKey
from app.models.audit_log import AuditLog
from app.models.schema_template import SchemaTemplate, Batch
from app.models.rbac import Permission, Role, ResourcePermission, AuditPermission, role_permissions, user_roles

# Import config
from app.core.config import get_settings
from app.core.security import get_password_hash

settings = get_settings()


class DeploymentSeeder:
    """Handles database deployment and seed data generation"""

    def __init__(self, database_url: str, drop_existing: bool = False, skip_seed: bool = False):
        self.database_url = database_url
        self.drop_existing = drop_existing
        self.skip_seed = skip_seed

        # Use NullPool for deployment to avoid connection issues
        self.engine = create_engine(database_url, poolclass=NullPool)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Data storage for cross-referencing
        self.organizations: List[Organization] = []
        self.users: List[User] = []
        self.workspaces: List[Workspace] = []
        self.jobs: List[Job] = []
        self.documents: List[Document] = []
        self.api_keys: List[APIKey] = []
        self.schema_templates: List[SchemaTemplate] = []
        self.permissions: List[Permission] = []
        self.roles: List[Role] = []

        # Date ranges (2.5 years of data)
        self.end_date = datetime.utcnow()
        self.start_date = self.end_date - timedelta(days=912)  # ~2.5 years

    def run(self):
        """Execute full deployment process"""
        print("=" * 80)
        print("SaaS OCR Platform - Deployment Script")
        print("=" * 80)
        print()

        if self.drop_existing:
            print("⚠️  WARNING: --drop-existing flag detected!")
            print("This will DROP the existing database and all data will be lost!")
            response = input("Type 'YES' to continue: ")
            if response != "YES":
                print("Deployment cancelled.")
                return
            self.drop_database()

        print("Step 1: Creating database schema...")
        self.create_schema()
        print("✓ Schema created successfully\n")

        if not self.skip_seed:
            print("Step 2: Generating seed data (this may take a few minutes)...")
            self.seed_all_data()
            print("✓ Seed data generated successfully\n")
        else:
            print("Step 2: Skipping seed data generation (--skip-seed flag)\n")

        print("=" * 80)
        print("✓ Deployment completed successfully!")
        print("=" * 80)
        print()
        print("Database Statistics:")
        self.print_statistics()

    def drop_database(self):
        """Drop all tables in the database"""
        print("Dropping existing database tables...")
        Base.metadata.drop_all(bind=self.engine)
        print("✓ Database dropped\n")

    def create_schema(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)

    def seed_all_data(self):
        """Generate all seed data"""
        with self.SessionLocal() as db:
            # Core RBAC system
            print("  - Creating RBAC permissions and roles...")
            self.seed_permissions(db)
            self.seed_roles(db)
            db.commit()
            print("    ✓ Created 36 permissions and 12 roles")

            # Organizations and users
            print("  - Creating organizations...")
            self.seed_organizations(db)
            db.commit()
            print(f"    ✓ Created {len(self.organizations)} organizations")

            print("  - Creating users and memberships...")
            self.seed_users(db)
            db.commit()
            print(f"    ✓ Created {len(self.users)} users")

            print("  - Creating workspaces...")
            self.seed_workspaces(db)
            db.commit()
            print(f"    ✓ Created {len(self.workspaces)} workspaces")

            # Application data
            print("  - Creating schema templates...")
            self.seed_schema_templates(db)
            db.commit()
            print(f"    ✓ Created {len(self.schema_templates)} schema templates")

            print("  - Creating API keys...")
            self.seed_api_keys(db)
            db.commit()
            print(f"    ✓ Created {len(self.api_keys)} API keys")

            # Heavy data (jobs, documents, audit logs) - in batches
            print("  - Creating jobs and documents (75,000+ records, this will take a while)...")
            self.seed_jobs_and_documents(db)
            print(f"    ✓ Created {len(self.jobs)} jobs and {len(self.documents)} documents")

            print("  - Creating batches...")
            self.seed_batches(db)
            db.commit()
            print("    ✓ Created batch operations")

            print("  - Creating audit logs (150,000+ records, this will take a while)...")
            self.seed_audit_logs(db)
            print("    ✓ Created audit log entries")

            print("  - Assigning user roles and permissions...")
            self.seed_user_roles(db)
            db.commit()
            print("    ✓ Assigned roles to users")

    def seed_permissions(self, db: Session):
        """Create all system permissions"""
        permission_definitions = [
            # Document permissions
            ("read:documents", "View documents", "documents", "read", "organization", True),
            ("write:documents", "Upload and modify documents", "documents", "write", "organization", True),
            ("delete:documents", "Delete documents", "documents", "delete", "organization", True),
            ("manage:documents", "Full document management", "documents", "manage", "organization", True),

            # Job permissions
            ("read:jobs", "View OCR jobs", "jobs", "read", "organization", True),
            ("write:jobs", "Create and modify jobs", "jobs", "write", "organization", True),
            ("delete:jobs", "Delete jobs", "jobs", "delete", "organization", True),
            ("manage:jobs", "Full job management", "jobs", "manage", "organization", True),

            # User permissions
            ("read:users", "View user information", "users", "read", "organization", True),
            ("write:users", "Modify user information", "users", "write", "organization", True),
            ("delete:users", "Remove users", "users", "delete", "organization", True),
            ("manage:users", "Full user management", "users", "manage", "organization", True),

            # Organization permissions
            ("read:organization", "View organization details", "organization", "read", "organization", True),
            ("write:organization", "Modify organization details", "organization", "write", "organization", True),
            ("manage:organization", "Full organization management", "organization", "manage", "organization", True),
            ("manage:billing", "Manage billing and subscriptions", "organization", "manage", "organization", True),

            # Workspace permissions
            ("read:workspaces", "View workspaces", "workspaces", "read", "organization", True),
            ("write:workspaces", "Create and modify workspaces", "workspaces", "write", "organization", True),
            ("delete:workspaces", "Delete workspaces", "workspaces", "delete", "organization", True),
            ("manage:workspaces", "Full workspace management", "workspaces", "manage", "organization", True),

            # API Key permissions
            ("read:api_keys", "View API keys", "api_keys", "read", "organization", True),
            ("write:api_keys", "Create and modify API keys", "api_keys", "write", "organization", True),
            ("delete:api_keys", "Revoke API keys", "api_keys", "delete", "organization", True),
            ("manage:api_keys", "Full API key management", "api_keys", "manage", "organization", True),

            # Schema permissions
            ("read:schemas", "View schema templates", "schemas", "read", "organization", True),
            ("write:schemas", "Create and modify schemas", "schemas", "write", "organization", True),
            ("delete:schemas", "Delete schemas", "schemas", "delete", "organization", True),
            ("manage:schemas", "Full schema management", "schemas", "manage", "organization", True),

            # Audit permissions
            ("read:audit_logs", "View audit logs", "audit_logs", "read", "organization", True),
            ("manage:audit_logs", "Full audit log access", "audit_logs", "manage", "organization", True),

            # RBAC permissions
            ("read:roles", "View roles", "roles", "read", "organization", True),
            ("write:roles", "Create and modify roles", "roles", "write", "organization", True),
            ("manage:roles", "Full role management", "roles", "manage", "organization", True),

            ("read:permissions", "View permissions", "permissions", "read", "organization", True),
            ("write:permissions", "Assign permissions", "permissions", "write", "organization", True),
            ("manage:permissions", "Full permission management", "permissions", "manage", "organization", True),
        ]

        for name, desc, resource, action, scope, is_system in permission_definitions:
            perm = Permission(
                name=name,
                description=desc,
                resource=resource,
                action=action,
                scope=scope,
                is_system=is_system,
                is_active=True
            )
            db.add(perm)
            self.permissions.append(perm)

        db.flush()  # Get IDs for permissions

    def seed_roles(self, db: Session):
        """Create system and custom roles"""
        # Define role permissions mapping
        role_permissions_map = {
            "Super Admin": [
                "manage:documents", "manage:jobs", "manage:users", "manage:organization",
                "manage:billing", "manage:workspaces", "manage:api_keys", "manage:schemas",
                "manage:audit_logs", "manage:roles", "manage:permissions"
            ],
            "Organization Owner": [
                "manage:documents", "manage:jobs", "manage:users", "manage:organization",
                "manage:billing", "manage:workspaces", "manage:api_keys", "manage:schemas",
                "read:audit_logs", "manage:roles", "manage:permissions"
            ],
            "Organization Admin": [
                "manage:documents", "manage:jobs", "write:users", "write:organization",
                "manage:workspaces", "manage:api_keys", "manage:schemas", "read:audit_logs",
                "read:roles"
            ],
            "Manager": [
                "write:documents", "write:jobs", "read:users", "read:organization",
                "write:workspaces", "write:api_keys", "write:schemas"
            ],
            "Member": [
                "read:documents", "write:documents", "read:jobs", "write:jobs",
                "read:users", "read:workspaces", "read:api_keys", "read:schemas"
            ],
            "Viewer": [
                "read:documents", "read:jobs", "read:users", "read:workspaces"
            ],
            "Billing Admin": [
                "read:organization", "manage:billing", "read:users"
            ],
            "API User": [
                "read:documents", "write:documents", "read:jobs", "write:jobs", "read:api_keys"
            ],
            "Schema Designer": [
                "read:documents", "read:jobs", "manage:schemas"
            ],
            "Auditor": [
                "read:documents", "read:jobs", "read:users", "manage:audit_logs", "read:organization"
            ],
            "Workspace Manager": [
                "read:documents", "write:documents", "read:jobs", "write:jobs",
                "manage:workspaces", "read:users", "write:api_keys"
            ],
            "Developer": [
                "read:documents", "write:documents", "read:jobs", "write:jobs",
                "manage:api_keys", "read:schemas", "write:schemas"
            ]
        }

        # Create roles
        priority = 100
        for role_name, perm_names in role_permissions_map.items():
            is_system = role_name in ["Super Admin", "Organization Owner", "Organization Admin",
                                      "Manager", "Member", "Viewer"]
            role_type = "system" if is_system else "custom"

            role = Role(
                name=role_name,
                description=f"{role_name} role with predefined permissions",
                organization_id=None,  # System-wide roles
                role_type=role_type,
                is_system=is_system,
                is_active=True,
                priority=priority
            )
            db.add(role)
            db.flush()  # Get role ID

            # Assign permissions to role
            for perm_name in perm_names:
                perm = next((p for p in self.permissions if p.name == perm_name), None)
                if perm:
                    db.execute(
                        role_permissions.insert().values(
                            role_id=role.id,
                            permission_id=perm.id
                        )
                    )

            self.roles.append(role)
            priority -= 5

    def seed_organizations(self, db: Session):
        """Create organizations with various tiers"""
        org_templates = [
            # Enterprise tier organizations (15)
            ("Acme Corporation", "acme-corp", "enterprise", "Technology leader in digital transformation"),
            ("Global Finance Inc", "global-finance", "enterprise", "International banking and financial services"),
            ("HealthCare Systems", "healthcare-sys", "enterprise", "Comprehensive healthcare network"),
            ("MegaRetail Group", "megaretail", "enterprise", "Multi-national retail conglomerate"),
            ("TechVentures LLC", "techventures", "enterprise", "Venture capital and technology investments"),
            ("International Logistics", "intl-logistics", "enterprise", "Global supply chain solutions"),
            ("Energy Solutions Corp", "energy-solutions", "enterprise", "Renewable energy and sustainability"),
            ("Pharma Research Ltd", "pharma-research", "enterprise", "Pharmaceutical research and development"),
            ("Aerospace Dynamics", "aerospace-dyn", "enterprise", "Aviation and aerospace engineering"),
            ("Telecom Global", "telecom-global", "enterprise", "Telecommunications infrastructure"),
            ("Insurance Partners", "insurance-partners", "enterprise", "Comprehensive insurance solutions"),
            ("Media & Entertainment Co", "media-entertainment", "enterprise", "Digital media production"),
            ("Manufacturing United", "manufacturing-united", "enterprise", "Industrial manufacturing"),
            ("Automotive Innovators", "auto-innovators", "enterprise", "Electric vehicle technology"),
            ("Real Estate Holdings", "realestate-holdings", "enterprise", "Commercial property management"),

            # Pro tier organizations (25)
            ("StartupHub", "startuphub", "pro", "Startup accelerator and co-working space"),
            ("Design Studio Pro", "design-studio", "pro", "Creative design agency"),
            ("Legal Services Group", "legal-services", "pro", "Corporate legal consulting"),
            ("Marketing Experts", "marketing-experts", "pro", "Digital marketing agency"),
            ("Data Analytics Co", "data-analytics", "pro", "Business intelligence solutions"),
            ("Cloud Solutions", "cloud-solutions", "pro", "Cloud infrastructure services"),
            ("Security Systems", "security-systems", "pro", "Cybersecurity consulting"),
            ("Education Platform", "edu-platform", "pro", "E-learning and training"),
            ("Consulting Partners", "consulting-partners", "pro", "Management consulting"),
            ("Food & Beverage Co", "food-beverage", "pro", "Restaurant chain management"),
            ("Travel Agency Pro", "travel-agency", "pro", "Corporate travel solutions"),
            ("Fitness Network", "fitness-network", "pro", "Gym and wellness centers"),
            ("Publishing House", "publishing-house", "pro", "Digital publishing platform"),
            ("Event Management", "event-mgmt", "pro", "Corporate event planning"),
            ("Architecture Firm", "architecture-firm", "pro", "Commercial architecture"),
            ("HR Solutions", "hr-solutions", "pro", "Human resources consulting"),
            ("Property Tech", "property-tech", "pro", "Real estate technology"),
            ("AgriTech Innovations", "agritech", "pro", "Agricultural technology"),
            ("Sports Management", "sports-mgmt", "pro", "Sports team management"),
            ("Beauty & Wellness", "beauty-wellness", "pro", "Spa and beauty services"),
            ("Pet Services Co", "pet-services", "pro", "Veterinary and pet care"),
            ("Gaming Studio", "gaming-studio", "pro", "Video game development"),
            ("Music Production", "music-production", "pro", "Music recording studio"),
            ("Fashion Retail", "fashion-retail", "pro", "Online fashion boutique"),
            ("Home Services", "home-services", "pro", "Home improvement platform"),

            # Starter tier organizations (20)
            ("Tech Startup Alpha", "startup-alpha", "starter", "Early-stage tech startup"),
            ("Freelance Collective", "freelance-collective", "starter", "Freelancer network"),
            ("Small Business Hub", "small-biz", "starter", "Local business services"),
            ("Creative Agency", "creative-agency", "starter", "Boutique creative studio"),
            ("Consulting Solo", "consulting-solo", "starter", "Independent consultant"),
            ("E-Commerce Store", "ecommerce-store", "starter", "Online retail shop"),
            ("Local Restaurant", "local-restaurant", "starter", "Family restaurant"),
            ("Photography Studio", "photo-studio", "starter", "Professional photography"),
            ("Accounting Firm", "accounting-firm", "starter", "Small accounting practice"),
            ("Law Office", "law-office", "starter", "Solo legal practice"),
            ("Medical Clinic", "medical-clinic", "starter", "Private medical practice"),
            ("Dental Practice", "dental-practice", "starter", "Family dentistry"),
            ("Veterinary Clinic", "vet-clinic", "starter", "Animal hospital"),
            ("Repair Services", "repair-services", "starter", "Electronics repair"),
            ("Cleaning Company", "cleaning-co", "starter", "Professional cleaning"),
            ("Landscaping Co", "landscaping", "starter", "Garden and landscape"),
            ("Construction LLC", "construction-llc", "starter", "Small construction firm"),
            ("Plumbing Services", "plumbing-services", "starter", "Residential plumbing"),
            ("Electrical Contractors", "electrical-contractors", "starter", "Electrical services"),
            ("Moving Company", "moving-company", "starter", "Local moving services"),
        ]

        regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "eu-central-1"]

        for i, (name, slug, tier, description) in enumerate(org_templates):
            # Set tier-based limits
            if tier == "enterprise":
                api_limit = 1000000
                storage_limit = 5000  # 5TB
            elif tier == "pro":
                api_limit = 100000
                storage_limit = 500  # 500GB
            else:  # starter
                api_limit = 10000
                storage_limit = 50  # 50GB

            # Simulate usage (70-95% of limits for active orgs)
            usage_pct = random.uniform(0.1, 0.95)
            api_used = int(api_limit * usage_pct)
            storage_used = round(storage_limit * usage_pct * random.uniform(0.3, 0.8), 2)

            # Created date spread over 2.5 years
            created_at = self.start_date + timedelta(
                days=random.randint(0, 912)
            )

            org = Organization(
                name=name,
                slug=slug,
                description=description,
                is_active=True,
                tier=tier,
                contact_email=f"contact@{slug}.com",
                contact_phone=f"+1-555-{random.randint(1000, 9999):04d}",
                website=f"https://www.{slug}.com",
                billing_email=f"billing@{slug}.com",
                stripe_customer_id=f"cus_{secrets.token_hex(12)}",
                api_calls_limit=api_limit,
                api_calls_used=api_used,
                storage_limit_gb=storage_limit,
                storage_used_gb=storage_used,
                region=random.choice(regions),
                settings={
                    "features": {
                        "batch_processing": tier in ["pro", "enterprise"],
                        "custom_schemas": True,
                        "api_access": True,
                        "audit_logs": tier == "enterprise",
                        "sso": tier == "enterprise",
                        "advanced_ocr": tier in ["pro", "enterprise"]
                    },
                    "notifications": {
                        "email": True,
                        "webhook": tier in ["pro", "enterprise"]
                    },
                    "retention": {
                        "documents": 365 if tier == "starter" else (730 if tier == "pro" else 2555),
                        "audit_logs": 2555 if tier == "enterprise" else 365
                    }
                },
                created_at=created_at,
                updated_at=created_at + timedelta(days=random.randint(0, 30))
            )
            db.add(org)
            self.organizations.append(org)

        db.flush()  # Get org IDs

    def seed_users(self, db: Session):
        """Create users and assign to organizations"""
        # Common password hash for all demo users: "Password123!"
        password_hash = get_password_hash("Password123!")

        first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa",
                      "William", "Jennifer", "James", "Mary", "Thomas", "Patricia", "Daniel",
                      "Linda", "Matthew", "Elizabeth", "Christopher", "Susan", "Andrew", "Jessica",
                      "Joshua", "Karen", "Kevin", "Nancy", "Brian", "Margaret", "George", "Betty"]

        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                     "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
                     "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White",
                     "Harris", "Clark", "Lewis", "Robinson", "Walker", "Hall", "Allen"]

        # Create superuser
        superuser = User(
            email="admin@saasocr.com",
            hashed_password=password_hash,
            full_name="System Administrator",
            is_active=True,
            is_verified=True,
            is_superuser=True,
            created_at=self.start_date,
            updated_at=self.start_date
        )
        db.add(superuser)
        self.users.append(superuser)

        # Create users for each organization
        for org in self.organizations:
            # Number of users based on tier
            if org.tier == "enterprise":
                num_users = random.randint(15, 25)
            elif org.tier == "pro":
                num_users = random.randint(5, 15)
            else:  # starter
                num_users = random.randint(2, 5)

            org_users = []
            for i in range(num_users):
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                email = f"{first_name.lower()}.{last_name.lower()}.{i}@{org.slug}.com"

                # User created sometime after org creation
                user_created = org.created_at + timedelta(days=random.randint(0, 60))

                user = User(
                    email=email,
                    hashed_password=password_hash,
                    full_name=f"{first_name} {last_name}",
                    is_active=random.random() > 0.05,  # 95% active
                    is_verified=random.random() > 0.1,  # 90% verified
                    is_superuser=False,
                    created_at=user_created,
                    updated_at=user_created + timedelta(days=random.randint(0, 30))
                )
                db.add(user)
                db.flush()  # Get user ID

                user.default_organization_id = org.id
                org_users.append(user)
                self.users.append(user)

                # Create organization membership
                # First user is owner, second is admin, rest are varied
                if i == 0:
                    role = "owner"
                elif i == 1:
                    role = "admin"
                else:
                    role = random.choice(["admin", "manager", "member", "member", "member", "viewer"])

                membership = OrganizationMember(
                    organization_id=org.id,
                    user_id=user.id,
                    role=role,
                    is_active=True,
                    invited_by_id=org_users[0].id if i > 0 else None,
                    created_at=user_created,
                    updated_at=user_created
                )
                db.add(membership)

        db.flush()

    def seed_workspaces(self, db: Session):
        """Create workspaces within organizations"""
        workspace_names = [
            "Engineering", "Marketing", "Sales", "Operations", "Support", "Finance",
            "HR", "Legal", "Product", "Design", "Research", "QA", "DevOps", "Analytics"
        ]

        for org in self.organizations:
            # Number of workspaces based on tier
            if org.tier == "enterprise":
                num_workspaces = random.randint(5, 10)
            elif org.tier == "pro":
                num_workspaces = random.randint(2, 5)
            else:  # starter
                num_workspaces = random.randint(1, 3)

            # Get org members
            org_members = [u for u in self.users if u.default_organization_id == org.id]

            selected_names = random.sample(workspace_names, min(num_workspaces, len(workspace_names)))

            for i, ws_name in enumerate(selected_names):
                slug = f"{ws_name.lower()}-{org.slug[:10]}"

                workspace = Workspace(
                    organization_id=org.id,
                    name=ws_name,
                    slug=slug,
                    description=f"{ws_name} team workspace",
                    is_active=True,
                    is_default=(i == 0),  # First workspace is default
                    settings={
                        "features": {
                            "batch_processing": org.tier in ["pro", "enterprise"],
                            "notifications": True
                        }
                    },
                    created_at=org.created_at + timedelta(days=random.randint(1, 30)),
                    updated_at=org.created_at + timedelta(days=random.randint(1, 60))
                )
                db.add(workspace)
                db.flush()  # Get workspace ID

                self.workspaces.append(workspace)

                # Add workspace members (subset of org members)
                num_members = min(random.randint(2, len(org_members)), len(org_members))
                workspace_members = random.sample(org_members, num_members)

                for j, member in enumerate(workspace_members):
                    ws_member = WorkspaceMember(
                        workspace_id=workspace.id,
                        user_id=member.id,
                        role="manager" if j == 0 else random.choice(["manager", "member", "member", "viewer"]),
                        is_active=True,
                        created_at=workspace.created_at,
                        updated_at=workspace.created_at
                    )
                    db.add(ws_member)

    def seed_schema_templates(self, db: Session):
        """Create schema templates"""
        schema_definitions = [
            {
                "name": "Invoice - Standard",
                "doc_type": "invoice",
                "description": "Standard commercial invoice schema",
                "fields": ["invoice_number", "invoice_date", "due_date", "vendor_name", "vendor_address",
                          "customer_name", "customer_address", "line_items", "subtotal", "tax", "total"]
            },
            {
                "name": "Invoice - Medical",
                "doc_type": "invoice",
                "description": "Medical billing invoice",
                "fields": ["invoice_number", "patient_name", "patient_id", "service_date", "provider",
                          "diagnosis_codes", "procedure_codes", "insurance_info", "total_charges"]
            },
            {
                "name": "Receipt - Retail",
                "doc_type": "receipt",
                "description": "Retail purchase receipt",
                "fields": ["store_name", "store_location", "receipt_number", "date", "time",
                          "items", "subtotal", "tax", "total", "payment_method"]
            },
            {
                "name": "Receipt - Restaurant",
                "doc_type": "receipt",
                "description": "Restaurant receipt",
                "fields": ["restaurant_name", "date", "time", "server", "table_number",
                          "items", "subtotal", "tax", "tip", "total"]
            },
            {
                "name": "W-2 Tax Form",
                "doc_type": "tax_form",
                "description": "IRS W-2 wage and tax statement",
                "fields": ["employee_name", "employee_ssn", "employer_name", "employer_ein",
                          "wages", "federal_tax", "social_security_wages", "medicare_wages"]
            },
            {
                "name": "1099 Tax Form",
                "doc_type": "tax_form",
                "description": "IRS 1099 miscellaneous income",
                "fields": ["recipient_name", "recipient_tin", "payer_name", "payer_tin",
                          "nonemployee_compensation", "federal_tax_withheld"]
            },
            {
                "name": "Driver License",
                "doc_type": "id_document",
                "description": "Driver's license information",
                "fields": ["license_number", "full_name", "date_of_birth", "address", "issue_date",
                          "expiration_date", "class", "restrictions", "state"]
            },
            {
                "name": "Passport",
                "doc_type": "id_document",
                "description": "Passport identification",
                "fields": ["passport_number", "surname", "given_names", "nationality", "date_of_birth",
                          "place_of_birth", "issue_date", "expiration_date", "issuing_authority"]
            },
            {
                "name": "Bank Statement",
                "doc_type": "financial",
                "description": "Bank account statement",
                "fields": ["account_holder", "account_number", "statement_period", "opening_balance",
                          "closing_balance", "transactions", "deposits", "withdrawals"]
            },
            {
                "name": "Utility Bill",
                "doc_type": "bill",
                "description": "Utility service bill",
                "fields": ["customer_name", "account_number", "service_address", "billing_period",
                          "previous_balance", "current_charges", "total_due", "due_date"]
            },
            {
                "name": "Medical Record",
                "doc_type": "medical",
                "description": "Patient medical record",
                "fields": ["patient_name", "patient_id", "date_of_birth", "visit_date", "provider",
                          "diagnosis", "treatment", "medications", "notes"]
            },
            {
                "name": "Lab Results",
                "doc_type": "medical",
                "description": "Laboratory test results",
                "fields": ["patient_name", "patient_id", "test_date", "ordered_by", "lab_name",
                          "test_results", "reference_ranges", "abnormal_flags"]
            },
            {
                "name": "Purchase Order",
                "doc_type": "procurement",
                "description": "Purchase order document",
                "fields": ["po_number", "po_date", "vendor", "buyer", "ship_to_address",
                          "line_items", "subtotal", "tax", "shipping", "total"]
            },
            {
                "name": "Packing Slip",
                "doc_type": "shipping",
                "description": "Shipping packing slip",
                "fields": ["order_number", "ship_date", "tracking_number", "ship_from", "ship_to",
                          "items", "quantity", "carrier"]
            },
        ]

        for org in self.organizations:
            # Get org users
            org_users = [u for u in self.users if u.default_organization_id == org.id]
            if not org_users:
                continue

            # Number of templates based on tier
            if org.tier == "enterprise":
                num_templates = len(schema_definitions)
            elif org.tier == "pro":
                num_templates = random.randint(5, 10)
            else:
                num_templates = random.randint(2, 5)

            selected_schemas = random.sample(schema_definitions, min(num_templates, len(schema_definitions)))

            for schema_def in selected_schemas:
                creator = random.choice(org_users)
                created_at = org.created_at + timedelta(days=random.randint(5, 100))

                template = SchemaTemplate(
                    user_id=creator.id,
                    organization_id=org.id,
                    name=schema_def["name"],
                    description=schema_def["description"],
                    document_type=schema_def["doc_type"],
                    schema_definition={
                        "type": "object",
                        "properties": {field: {"type": "string"} for field in schema_def["fields"]},
                        "required": schema_def["fields"][:3]  # First 3 fields required
                    },
                    fields=[
                        {
                            "name": field,
                            "type": "string",
                            "required": i < 3,
                            "description": f"{field.replace('_', ' ').title()} field"
                        }
                        for i, field in enumerate(schema_def["fields"])
                    ],
                    is_public=random.random() > 0.7,  # 30% public
                    is_active=True,
                    version="1.0",
                    usage_count=random.randint(0, 1000),
                    created_at=created_at,
                    updated_at=created_at + timedelta(days=random.randint(0, 30))
                )
                db.add(template)
                self.schema_templates.append(template)

        db.flush()

    def seed_api_keys(self, db: Session):
        """Create API keys for organizations"""
        for org in self.organizations:
            org_users = [u for u in self.users if u.default_organization_id == org.id]
            if not org_users:
                continue

            # Number of API keys based on tier
            if org.tier == "enterprise":
                num_keys = random.randint(5, 15)
            elif org.tier == "pro":
                num_keys = random.randint(2, 8)
            else:
                num_keys = random.randint(1, 3)

            for i in range(num_keys):
                creator = random.choice(org_users)
                created_at = org.created_at + timedelta(days=random.randint(10, 300))

                # Generate API key
                raw_key = f"sk_{secrets.token_hex(32)}"
                key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
                key_prefix = raw_key[:16]

                # Simulate usage
                is_active = random.random() > 0.1  # 90% active
                last_used = None
                usage_count = 0

                if is_active and random.random() > 0.2:  # 80% of active keys have been used
                    last_used = created_at + timedelta(days=random.randint(1, 400))
                    usage_count = random.randint(10, 50000)

                api_key = APIKey(
                    user_id=creator.id,
                    organization_id=org.id,
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    name=f"API Key {i+1}" if i < 2 else random.choice([
                        "Production", "Staging", "Development", "CI/CD", "Mobile App",
                        "Web App", "Integration", "Testing", "Backup"
                    ]),
                    is_active=is_active,
                    allowed_ips="" if random.random() > 0.3 else "192.168.1.0/24,10.0.0.0/8",
                    last_used_at=last_used,
                    usage_count=usage_count,
                    created_at=created_at,
                    updated_at=created_at + timedelta(days=random.randint(0, 30))
                )
                db.add(api_key)
                self.api_keys.append(api_key)

        db.flush()

    def seed_jobs_and_documents(self, db: Session):
        """Create jobs and documents (75,000+ records) - heavy data generation"""
        document_types = ["invoice", "receipt", "tax_form", "id_document", "financial",
                         "bill", "medical", "procurement", "shipping", "contract"]

        statuses = ["completed", "completed", "completed", "completed", "failed", "processing"]
        file_types = ["pdf", "pdf", "pdf", "png", "jpg", "tiff"]

        # Generate jobs in batches to avoid memory issues
        BATCH_SIZE = 5000
        total_jobs = 75000

        for batch_num in range(0, total_jobs, BATCH_SIZE):
            batch_jobs = []
            batch_docs = []

            jobs_in_batch = min(BATCH_SIZE, total_jobs - batch_num)

            for i in range(jobs_in_batch):
                # Select random org and user
                org = random.choice(self.organizations)
                org_users = [u for u in self.users if u.default_organization_id == org.id]
                if not org_users:
                    continue

                user = random.choice(org_users)

                # Random workspace (80% assigned, 20% unassigned)
                workspace_id = None
                if random.random() > 0.2:
                    org_workspaces = [w for w in self.workspaces if w.organization_id == org.id]
                    if org_workspaces:
                        workspace_id = random.choice(org_workspaces).id

                # Random date within 2.5 years
                job_created = self.start_date + timedelta(
                    seconds=random.randint(0, int((self.end_date - self.start_date).total_seconds()))
                )

                # Job details
                status = random.choice(statuses)
                doc_type = random.choice(document_types)
                total_pages = random.randint(1, 50) if random.random() > 0.7 else random.randint(1, 5)
                pages_processed = total_pages if status == "completed" else random.randint(0, total_pages)

                # Schema template (70% use template)
                schema_template_name = None
                if random.random() > 0.3:
                    org_templates = [t for t in self.schema_templates if t.organization_id == org.id]
                    if org_templates:
                        matching_templates = [t for t in org_templates if t.document_type == doc_type]
                        if matching_templates:
                            schema_template_name = random.choice(matching_templates).name

                # Extracted data (if completed)
                extracted_data = None
                confidence_scores = None
                if status == "completed":
                    extracted_data = self._generate_extracted_data(doc_type)
                    confidence_scores = {
                        field: round(random.uniform(0.75, 0.99), 3)
                        for field in list(extracted_data.keys())[:5]
                    }

                processing_time = round(random.uniform(1.5, 45.0), 2) if status == "completed" else None

                job = Job(
                    job_id=f"job_{secrets.token_hex(16)}",
                    user_id=user.id,
                    organization_id=org.id,
                    workspace_id=workspace_id,
                    status=status,
                    document_type=doc_type,
                    schema_template=schema_template_name,
                    total_pages=total_pages,
                    pages_processed=pages_processed,
                    extracted_data=extracted_data,
                    confidence_scores=confidence_scores,
                    raw_text="Sample OCR text..." if status == "completed" else None,
                    error_message="OCR processing timeout" if status == "failed" else None,
                    retry_count=random.randint(0, 3) if status == "failed" else 0,
                    processing_time_seconds=processing_time,
                    webhook_url=f"https://api.{org.slug}.com/webhook" if random.random() > 0.7 else None,
                    webhook_sent=random.random() > 0.1 if status == "completed" else False,
                    created_at=job_created,
                    updated_at=job_created + timedelta(seconds=random.randint(10, 300))
                )
                batch_jobs.append(job)

                # Create document for job
                file_type = random.choice(file_types)
                file_size = random.randint(50000, 10000000)  # 50KB to 10MB

                doc = Document(
                    job_id=None,  # Will be set after flush
                    organization_id=org.id,
                    filename=f"doc_{secrets.token_hex(8)}.{file_type}",
                    original_filename=f"document_{i}.{file_type}",
                    file_size=file_size,
                    file_type=file_type,
                    mime_type=f"application/{file_type}" if file_type == "pdf" else f"image/{file_type}",
                    storage_path=f"{org.slug}/documents/{job_created.year}/{job_created.month:02d}/doc_{secrets.token_hex(8)}.{file_type}",
                    storage_bucket="saas-ocr-documents",
                    is_processed=1 if status == "completed" else 0,
                    created_at=job_created,
                    updated_at=job_created + timedelta(seconds=random.randint(5, 200))
                )
                batch_docs.append(doc)

            # Add batch to database
            db.bulk_save_objects(batch_jobs)
            db.flush()

            # Update document job_ids
            for i, doc in enumerate(batch_docs):
                doc.job_id = batch_jobs[i].id

            db.bulk_save_objects(batch_docs)
            db.commit()

            # Store references
            self.jobs.extend(batch_jobs)
            self.documents.extend(batch_docs)

            print(f"    → Processed {batch_num + jobs_in_batch:,}/{total_jobs:,} jobs...")

    def _generate_extracted_data(self, doc_type: str) -> Dict[str, Any]:
        """Generate realistic extracted data based on document type"""
        if doc_type == "invoice":
            return {
                "invoice_number": f"INV-{random.randint(10000, 99999)}",
                "invoice_date": (datetime.utcnow() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d"),
                "due_date": (datetime.utcnow() + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                "vendor_name": random.choice(["Acme Corp", "Global Supplies", "Tech Solutions"]),
                "total": round(random.uniform(100, 50000), 2)
            }
        elif doc_type == "receipt":
            return {
                "store_name": random.choice(["Walmart", "Target", "Best Buy", "Amazon"]),
                "date": (datetime.utcnow() - timedelta(days=random.randint(1, 180))).strftime("%Y-%m-%d"),
                "total": round(random.uniform(10, 500), 2),
                "payment_method": random.choice(["Credit Card", "Debit Card", "Cash"])
            }
        elif doc_type == "tax_form":
            return {
                "form_type": random.choice(["W-2", "1099-MISC", "1099-NEC"]),
                "tax_year": str(random.randint(2022, 2024)),
                "amount": round(random.uniform(5000, 150000), 2)
            }
        elif doc_type == "id_document":
            return {
                "document_type": random.choice(["Driver License", "Passport", "ID Card"]),
                "id_number": f"{random.randint(10000000, 99999999)}",
                "expiration_date": (datetime.utcnow() + timedelta(days=random.randint(365, 1825))).strftime("%Y-%m-%d")
            }
        else:
            return {
                "document_type": doc_type,
                "extracted_at": datetime.utcnow().isoformat(),
                "confidence": round(random.uniform(0.85, 0.99), 3)
            }

    def seed_batches(self, db: Session):
        """Create batch operations"""
        for org in self.organizations:
            # Only pro and enterprise get batches
            if org.tier == "starter":
                continue

            org_users = [u for u in self.users if u.default_organization_id == org.id]
            if not org_users:
                continue

            num_batches = random.randint(5, 20) if org.tier == "enterprise" else random.randint(2, 10)

            for i in range(num_batches):
                creator = random.choice(org_users)
                created_at = org.created_at + timedelta(days=random.randint(30, 800))

                status = random.choice(["completed", "completed", "completed", "failed", "processing"])
                total_jobs = random.randint(10, 500)

                if status == "completed":
                    completed_jobs = total_jobs
                    failed_jobs = random.randint(0, int(total_jobs * 0.05))
                elif status == "processing":
                    completed_jobs = random.randint(0, total_jobs)
                    failed_jobs = random.randint(0, 5)
                else:  # failed
                    completed_jobs = random.randint(0, total_jobs)
                    failed_jobs = total_jobs - completed_jobs

                batch = Batch(
                    batch_id=f"batch_{secrets.token_hex(16)}",
                    user_id=creator.id,
                    organization_id=org.id,
                    name=f"Batch Processing {i+1}",
                    description=random.choice([
                        "Monthly invoice processing",
                        "Quarterly document upload",
                        "Year-end tax forms",
                        "Customer document batch",
                        "Automated data extraction"
                    ]),
                    status=status,
                    total_jobs=total_jobs,
                    completed_jobs=completed_jobs,
                    failed_jobs=failed_jobs,
                    schema_template=random.choice(["Invoice - Standard", "Receipt - Retail", None, None]),
                    document_type=random.choice(["invoice", "receipt", "tax_form", "financial"]),
                    webhook_url=f"https://api.{org.slug}.com/batch-webhook" if random.random() > 0.5 else None,
                    webhook_sent=status == "completed",
                    results_summary={
                        "total_documents": total_jobs,
                        "successful": completed_jobs,
                        "failed": failed_jobs,
                        "total_pages": total_jobs * random.randint(1, 10)
                    } if status == "completed" else None,
                    created_at=created_at,
                    updated_at=created_at + timedelta(hours=random.randint(1, 48))
                )
                db.add(batch)

    def seed_audit_logs(self, db: Session):
        """Create audit log entries (150,000+ records)"""
        actions = [
            "document.upload", "document.view", "document.download", "document.delete",
            "job.create", "job.view", "job.delete",
            "user.login", "user.logout", "user.create", "user.update", "user.delete",
            "organization.view", "organization.update",
            "api_key.create", "api_key.view", "api_key.revoke",
            "schema.create", "schema.update", "schema.delete",
            "workspace.create", "workspace.update",
            "role.assign", "permission.grant"
        ]

        resource_types = ["job", "document", "user", "organization", "api_key", "schema_template", "workspace"]

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "PostmanRuntime/7.32.3",
            "python-requests/2.31.0",
            "curl/8.1.2"
        ]

        BATCH_SIZE = 10000
        total_logs = 150000

        for batch_num in range(0, total_logs, BATCH_SIZE):
            batch_logs = []
            logs_in_batch = min(BATCH_SIZE, total_logs - batch_num)

            for i in range(logs_in_batch):
                # Random user and their org
                user = random.choice(self.users)

                # Random timestamp
                timestamp = self.start_date + timedelta(
                    seconds=random.randint(0, int((self.end_date - self.start_date).total_seconds()))
                )

                action = random.choice(actions)
                resource_type = random.choice(resource_types)

                # Random IP (simulate real IPs)
                ip_address = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

                # Status code (95% success, 5% errors)
                status_code = random.choice([200, 200, 200, 200, 200, 200, 200, 200, 200, 201, 204, 400, 401, 403, 500])

                audit_log = AuditLog(
                    timestamp=timestamp,
                    user_id=user.id if not user.is_superuser else None,
                    user_email=user.email,
                    api_key_id=random.choice(self.api_keys).id if random.random() > 0.7 and self.api_keys else None,
                    action=action,
                    resource_type=resource_type,
                    resource_id=random.randint(1, 10000),
                    ip_address=ip_address,
                    user_agent=random.choice(user_agents),
                    request_method=random.choice(["GET", "GET", "GET", "POST", "PUT", "DELETE"]),
                    request_path=f"/api/v1/{resource_type}s/{random.randint(1, 1000)}",
                    metadata={
                        "action_details": f"User performed {action}",
                        "client_version": "1.0.0"
                    } if random.random() > 0.5 else {},
                    status_code=status_code,
                    error_message="Unauthorized access" if status_code in [401, 403] else None
                )
                batch_logs.append(audit_log)

            db.bulk_save_objects(batch_logs)
            db.commit()

            print(f"    → Processed {batch_num + logs_in_batch:,}/{total_logs:,} audit logs...")

    def seed_user_roles(self, db: Session):
        """Assign roles to users based on their organization membership"""
        # Get role mappings
        role_map = {
            "owner": next((r for r in self.roles if r.name == "Organization Owner"), None),
            "admin": next((r for r in self.roles if r.name == "Organization Admin"), None),
            "manager": next((r for r in self.roles if r.name == "Manager"), None),
            "member": next((r for r in self.roles if r.name == "Member"), None),
            "viewer": next((r for r in self.roles if r.name == "Viewer"), None),
        }

        for org in self.organizations:
            org_members = db.query(OrganizationMember).filter(
                OrganizationMember.organization_id == org.id
            ).all()

            for member in org_members:
                role = role_map.get(member.role)
                if role:
                    db.execute(
                        user_roles.insert().values(
                            user_id=member.user_id,
                            role_id=role.id,
                            organization_id=org.id,
                            workspace_id=None
                        )
                    )

        db.commit()

    def print_statistics(self):
        """Print database statistics"""
        with self.SessionLocal() as db:
            stats = {
                "Organizations": db.query(Organization).count(),
                "Users": db.query(User).count(),
                "Workspaces": db.query(Workspace).count(),
                "Jobs": db.query(Job).count(),
                "Documents": db.query(Document).count(),
                "API Keys": db.query(APIKey).count(),
                "Schema Templates": db.query(SchemaTemplate).count(),
                "Batches": db.query(Batch).count(),
                "Audit Logs": db.query(AuditLog).count(),
                "Permissions": db.query(Permission).count(),
                "Roles": db.query(Role).count(),
            }

            for name, count in stats.items():
                print(f"  - {name}: {count:,}")

            print()
            print("Credentials:")
            print("  - Superuser: admin@saasocr.com / Password123!")
            print("  - All users: [email] / Password123!")
            print()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Deploy SaaS OCR platform with comprehensive seed data"
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Drop existing database before deployment (WARNING: destructive)"
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Skip seed data generation (only create schema)"
    )

    args = parser.parse_args()

    # Get database URL from settings
    database_url = settings.DATABASE_URL

    print(f"Database URL: {database_url}")
    print()

    # Create seeder and run
    seeder = DeploymentSeeder(
        database_url=database_url,
        drop_existing=args.drop_existing,
        skip_seed=args.skip_seed
    )

    try:
        seeder.run()
    except Exception as e:
        print(f"\n❌ Error during deployment: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
