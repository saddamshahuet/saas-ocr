# Enterprise Features Documentation

This document provides a comprehensive guide to all enterprise-grade features implemented in the SaaS OCR platform.

## Table of Contents

1. [Multi-Tenancy & Organizations](#multi-tenancy--organizations)
2. [Advanced RBAC (Role-Based Access Control)](#advanced-rbac)
3. [Data Residency](#data-residency)
4. [Mobile Application](#mobile-application)
5. [Quick Start Guide](#quick-start-guide)

---

## Multi-Tenancy & Organizations

### Overview

The platform now supports full multi-tenancy, allowing multiple organizations to use the platform while maintaining complete data isolation. Each organization can have multiple workspaces and manage their own members with role-based permissions.

### Key Concepts

#### Organizations
- **Definition**: A company or entity using the platform
- **Features**:
  - Isolated data storage
  - Custom settings and configuration
  - Usage quotas and billing
  - Data residency selection
  - Member management

#### Workspaces
- **Definition**: Teams or projects within an organization
- **Features**:
  - Segment work by department/project
  - Workspace-specific members
  - Separate document storage
  - Custom workspace settings

#### Organization Members
- **Roles**: Owner, Admin, Manager, Member, Viewer
- **Capabilities**: Role-based access control

### API Endpoints

#### Create Organization

```bash
POST /api/v1/organizations
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Acme Healthcare",
  "slug": "acme-healthcare",  # Optional, auto-generated if not provided
  "description": "Healthcare document processing",
  "tier": "enterprise"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Acme Healthcare",
  "slug": "acme-healthcare",
  "tier": "enterprise",
  "region": "us-east-1",
  "api_calls_limit": 200000,
  "api_calls_used": 0,
  "storage_limit_gb": 500,
  "member_count": 1,
  "workspace_count": 1,
  "created_at": "2025-11-22T10:00:00Z"
}
```

#### List Organizations

```bash
GET /api/v1/organizations?page=1&page_size=50
Authorization: Bearer <token>
```

#### Add Member to Organization

```bash
POST /api/v1/organizations/{org_id}/members
Content-Type: application/json
Authorization: Bearer <token>

{
  "user_email": "user@example.com",
  "role": "member"  # owner, admin, manager, member, viewer
}
```

#### Create Workspace

```bash
POST /api/v1/organizations/{org_id}/workspaces
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Clinical Operations",
  "slug": "clinical-ops",
  "description": "Clinical document processing workspace"
}
```

### Role Hierarchy

```
Owner (highest privileges)
  ├─ Full organization control
  ├─ Can delete organization
  ├─ Can manage all members
  └─ Can change billing

Admin
  ├─ Manage organization settings
  ├─ Manage members and workspaces
  ├─ View analytics and billing
  └─ Cannot delete organization

Manager
  ├─ Manage documents and jobs
  ├─ Create workspaces
  ├─ View analytics
  └─ Cannot manage members

Member
  ├─ Create and manage own documents
  ├─ Upload and process files
  ├─ View own jobs
  └─ Cannot manage workspaces

Viewer (lowest privileges)
  ├─ Read-only access
  ├─ View documents and jobs
  └─ Cannot create or modify
```

### Usage Example

```python
import requests

# API configuration
API_URL = "https://api.saas-ocr.com"
TOKEN = "your-jwt-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Create organization
org_response = requests.post(
    f"{API_URL}/api/v1/organizations",
    headers=headers,
    json={
        "name": "My Healthcare Org",
        "tier": "professional"
    }
)
org = org_response.json()
org_id = org["id"]

# Add team member
member_response = requests.post(
    f"{API_URL}/api/v1/organizations/{org_id}/members",
    headers=headers,
    json={
        "user_email": "colleague@example.com",
        "role": "member"
    }
)

# Create workspace
workspace_response = requests.post(
    f"{API_URL}/api/v1/organizations/{org_id}/workspaces",
    headers=headers,
    json={
        "name": "Admissions",
        "description": "Patient admission documents"
    }
)
workspace = workspace_response.json()

print(f"Organization created: {org_id}")
print(f"Workspace created: {workspace['id']}")
```

---

## Advanced RBAC

### Overview

The platform implements a comprehensive Role-Based Access Control system with fine-grained permissions, custom roles, and resource-level access control.

### Permission Model

#### System Permissions (30+ built-in)

**Documents:**
- `read:documents` - View documents
- `write:documents` - Create/edit documents
- `delete:documents` - Delete documents
- `manage:documents` - Full document control

**Jobs:**
- `read:jobs` - View jobs
- `write:jobs` - Create jobs
- `delete:jobs` - Delete jobs
- `manage:jobs` - Full job control

**Users:**
- `read:users` - View users
- `write:users` - Invite users
- `delete:users` - Remove users
- `manage:users` - Full user management

**Organization:**
- `read:organization` - View org settings
- `write:organization` - Edit org settings
- `manage:organization` - Full org control

**Workspaces:**
- `read:workspaces` - View workspaces
- `write:workspaces` - Create workspaces
- `delete:workspaces` - Delete workspaces
- `manage:workspaces` - Full workspace control

**Billing:**
- `read:billing` - View billing info
- `manage:billing` - Manage billing

**Roles:**
- `read:roles` - View roles
- `write:roles` - Create custom roles
- `manage:roles` - Full role management

### Default Roles

| Role | Priority | Description | Key Permissions |
|------|----------|-------------|-----------------|
| **Owner** | 100 | Full control | ALL permissions |
| **Admin** | 90 | Administrative access | manage:organization, manage:users, manage:workspaces |
| **Manager** | 70 | Operations management | manage:documents, manage:jobs, read:analytics |
| **Member** | 50 | Standard access | write:documents, write:jobs, write:schemas |
| **Viewer** | 30 | Read-only access | read:* (all read permissions) |
| **Auditor** | 40 | Compliance access | read:*, read:analytics, read:billing |

### Using RBAC in Code

#### Backend (Python/FastAPI)

```python
from fastapi import Depends, HTTPException
from app.services.rbac_service import RBACService
from app.api.dependencies import get_current_user

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check permission
    has_permission = RBACService.user_has_permission(
        user=current_user,
        permission_name="delete:documents",
        db=db,
        organization_id=org_id,
        resource_type="document",
        resource_id=doc_id,
    )

    if not has_permission:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Proceed with deletion
    ...
```

#### Using Permission Decorators

```python
from app.middleware.permissions import require_permission, PermissionChecker

# Method 1: Decorator
@require_permission("manage:documents")
@router.post("/documents/batch")
async def batch_upload(...):
    ...

# Method 2: Dependency
@router.get("/analytics/report")
async def get_report(
    _: None = Depends(PermissionChecker("read:analytics")),
    db: Session = Depends(get_db),
):
    ...
```

### Custom Roles

Create organization-specific custom roles:

```python
from app.models import Role, Permission
from app.services.rbac_service import RBACService

# Create custom role
custom_role = Role(
    name="Data Analyst",
    description="Can view and analyze data but not modify",
    organization_id=org_id,
    role_type="custom",
    priority=45,
)

# Assign specific permissions
permissions = db.query(Permission).filter(
    Permission.name.in_([
        "read:documents",
        "read:jobs",
        "read:analytics",
        "read:billing",
    ])
).all()

custom_role.permissions = permissions
db.add(custom_role)
db.commit()

# Assign role to user
RBACService.assign_role_to_user(
    user_id=user.id,
    role_id=custom_role.id,
    organization_id=org_id,
    db=db,
)
```

### Resource-Level Permissions

Grant permissions on specific resources:

```python
# Grant user permission to edit a specific document
RBACService.grant_resource_permission(
    user_id=user.id,
    permission_name="write:documents",
    resource_type="document",
    resource_id=123,
    organization_id=org_id,
    db=db,
)
```

### Permission Audit Logging

All permission changes are automatically logged:

```python
# Audit logs are automatically created for:
# - Role assignments
# - Role revocations
# - Permission grants
# - Custom role creation

# Query audit logs
from app.models import AuditPermission

audits = db.query(AuditPermission).filter(
    AuditPermission.organization_id == org_id,
    AuditPermission.action == "assign_role",
).order_by(AuditPermission.created_at.desc()).all()

for audit in audits:
    print(f"{audit.performed_by.email} {audit.action} role {audit.role.name} to {audit.target_user.email}")
```

---

## Data Residency

### Overview

The platform supports multi-region data storage for compliance with data sovereignty regulations (GDPR, HIPAA, etc.). Organizations can choose where their data is stored and migrate between regions.

### Supported Regions

#### North America
- **us-east-1**: US East (N. Virginia) - HIPAA compliant
- **us-east-2**: US East (Ohio) - HIPAA compliant
- **us-west-1**: US West (N. California) - HIPAA compliant
- **us-west-2**: US West (Oregon) - HIPAA compliant
- **ca-central-1**: Canada (Central) - HIPAA compliant

#### Europe (GDPR Compliant)
- **eu-west-1**: Europe (Ireland) - GDPR compliant
- **eu-west-2**: Europe (London) - GDPR compliant
- **eu-central-1**: Europe (Frankfurt) - GDPR compliant
- **uk-south-1**: UK South - GDPR compliant

#### Asia Pacific
- **ap-southeast-1**: Asia Pacific (Singapore)
- **ap-southeast-2**: Asia Pacific (Sydney)
- **ap-northeast-1**: Asia Pacific (Tokyo)
- **ap-south-1**: Asia Pacific (Mumbai)

### Selecting a Region

When creating an organization, specify the region:

```python
org_response = requests.post(
    f"{API_URL}/api/v1/organizations",
    headers=headers,
    json={
        "name": "EU Healthcare Org",
        "region": "eu-west-1"  # GDPR-compliant region
    }
)
```

### Region Information

```python
from app.core.regions import RegionService

# Get region info
region = RegionService.get_region_info("eu-west-1")
print(f"Region: {region.name}")
print(f"GDPR Compliant: {region.gdpr_compliant}")
print(f"HIPAA Compliant: {region.hipaa_compliant}")

# List GDPR-compliant regions
gdpr_regions = RegionService.get_gdpr_regions()
print(gdpr_regions)  # ['eu-west-1', 'eu-west-2', 'eu-central-1', 'uk-south-1']

# Get recommended region for continent
region = RegionService.get_nearest_region("Europe")
print(region)  # 'eu-west-1'
```

### Data Migration

#### Validate Migration

```python
from app.services.data_migration_service import DataMigrationService

# Check if migration is possible
validation = await DataMigrationService.validate_migration(
    organization_id=org_id,
    target_region="eu-west-1",
    db=db,
)

if validation["valid"]:
    print(f"Can migrate {validation['document_count']} documents")
    print(f"Total size: {validation['total_size_gb']} GB")
    print(f"Estimated time: {validation['estimated_time_hours']} hours")
else:
    print(f"Migration not allowed: {validation['error']}")
```

#### Perform Migration

```python
# Dry run (test migration without moving data)
result = await DataMigrationService.start_migration(
    organization_id=org_id,
    target_region="eu-west-1",
    db=db,
    dry_run=True,
)

# Actual migration
result = await DataMigrationService.start_migration(
    organization_id=org_id,
    target_region="eu-west-1",
    db=db,
    dry_run=False,
)

print(f"Migrated {result['migrated_count']} documents")
print(f"Failed: {result['failed_count']}")
```

#### Estimate Migration Cost

```python
cost = DataMigrationService.estimate_migration_cost(
    total_size_gb=100.5,
    source_region="us-east-1",
    target_region="eu-west-1",
)

print(f"Transfer cost: ${cost['one_time_transfer_cost_usd']}")
print(f"Monthly storage difference: ${cost['monthly_storage_cost_difference_usd']}")
```

### Compliance Rules

**Migration Restrictions:**
- ❌ Cannot migrate from GDPR to non-GDPR region
- ❌ Cannot migrate from HIPAA to non-HIPAA region
- ✅ Can migrate within same compliance tier
- ✅ Can upgrade to higher compliance (e.g., US to EU for GDPR)

### Storage Routing

The platform automatically routes all storage operations to the correct region based on the organization's configuration:

```python
from app.services.region_storage_service import RegionStorageService

# Upload file to organization's region
result = await RegionStorageService.upload_file(
    region=org.region,
    file_data=file_bytes,
    object_name=f"documents/{doc_id}/file.pdf",
    bucket_type="documents",
    content_type="application/pdf",
)

# Download from specific region
data = await RegionStorageService.download_file(
    region=org.region,
    object_name=f"documents/{doc_id}/file.pdf",
    bucket_type="documents",
)

# Get presigned URL for temporary access
url = await RegionStorageService.get_presigned_url(
    region=org.region,
    object_name=f"documents/{doc_id}/file.pdf",
    bucket_type="documents",
    expiry_seconds=3600,  # 1 hour
)
```

---

## Mobile Application

### Overview

The React Native mobile app provides enterprise-grade document scanning and processing capabilities with offline support, push notifications, and biometric security.

### Features

#### Authentication
- Email/password login
- JWT token management
- Biometric login (Face ID, Touch ID, Fingerprint)
- Secure credential storage
- Auto token refresh

#### Document Scanning
- Camera with edge detection
- Automatic document crop
- Multi-document batch scanning
- Photo capture and gallery picker
- Real-time upload

#### Offline Support
- Encrypted local storage (MMKV)
- Offline upload queue
- Document caching
- Auto-sync when online

#### Push Notifications
- Job completion alerts
- Real-time updates
- Topic subscriptions

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/saas-ocr.git
cd saas-ocr/mobile

# Install dependencies
npm install

# iOS - Install pods
cd ios && pod install && cd ..

# Configure Firebase
# 1. Add GoogleService-Info.plist (iOS)
# 2. Add google-services.json (Android)

# Update API URL in src/services/apiClient.ts
# const API_BASE_URL = 'https://your-api-domain.com';

# Run the app
npm run ios     # iOS
npm run android # Android
```

### Usage Examples

#### Login with Email

```typescript
import {useAuthStore} from '@store/authStore';

const LoginScreen = () => {
  const {login} = useAuthStore();

  const handleLogin = async (email: string, password: string) => {
    try {
      await login(email, password);
      // Automatically navigated to main app
    } catch (error) {
      Alert.alert('Login Failed', error.message);
    }
  };

  // ...
};
```

#### Scan Document

```typescript
import {documentScannerService} from '@services/documentScannerService';

const ScanScreen = () => {
  const handleScan = async () => {
    try {
      const document = await documentScannerService.scanDocument();

      if (document) {
        // Upload to server
        const job = await documentScannerService.uploadDocument(
          document,
          organizationId,
          workspaceId,
        );

        Alert.alert('Success', 'Document uploaded');
      }
    } catch (error) {
      Alert.alert('Scan Failed', error.message);
    }
  };

  // ...
};
```

#### Enable Biometric Login

```typescript
import {useAuthStore} from '@store/authStore';
import {biometricService} from '@services/biometricService';

const SettingsScreen = () => {
  const {enableBiometric} = useAuthStore();

  const handleEnableBiometric = async () => {
    try {
      const available = await biometricService.isBiometricAvailable();

      if (!available) {
        Alert.alert('Not Available', 'Biometric not supported on this device');
        return;
      }

      await enableBiometric();
      Alert.alert('Success', 'Biometric login enabled');
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  // ...
};
```

### Mobile API Integration

The mobile app uses the same REST API as the web platform:

```typescript
// Upload document
POST /api/v1/jobs
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <binary>
organization_id: 123
workspace_id: 456
document_type: "hospice_admission"
```

### Offline Queue

Documents scanned while offline are automatically queued and uploaded when connection is restored:

```typescript
import {storageService} from '@services/storageService';

// Add to offline queue
storageService.addToOfflineQueue({
  type: 'document_upload',
  document: scannedDocument,
  organizationId,
  workspaceId,
});

// On network reconnect, queue is automatically processed
```

---

## Quick Start Guide

### 1. Set Up Organization

```bash
# Create organization
curl -X POST https://api.saas-ocr.com/api/v1/organizations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Organization",
    "tier": "professional",
    "region": "us-east-1"
  }'
```

### 2. Add Team Members

```bash
# Invite admin
curl -X POST https://api.saas-ocr.com/api/v1/organizations/1/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "admin@example.com",
    "role": "admin"
  }'

# Invite member
curl -X POST https://api.saas-ocr.com/api/v1/organizations/1/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "member@example.com",
    "role": "member"
  }'
```

### 3. Create Workspace

```bash
curl -X POST https://api.saas-ocr.com/api/v1/organizations/1/workspaces \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Clinical Operations",
    "description": "Clinical document processing"
  }'
```

### 4. Upload Document (Mobile or Web)

**Mobile:**
1. Open app
2. Login with credentials or biometric
3. Tap "Scan Document"
4. Camera opens with edge detection
5. Capture document
6. Review and confirm
7. Document uploaded automatically

**Web/API:**
```bash
curl -X POST https://api.saas-ocr.com/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.pdf" \
  -F "organization_id=1" \
  -F "workspace_id=1" \
  -F "document_type=hospice_admission"
```

### 5. Monitor Processing

```bash
# Check job status
curl https://api.saas-ocr.com/api/v1/jobs/{job_id} \
  -H "Authorization: Bearer $TOKEN"

# Get extracted data
# When status is "completed", extracted_data field contains results
```

---

## Security Best Practices

### For Backend

1. **Always verify organization access**
   ```python
   verify_organization_access(user, org_id, db, required_role="member")
   ```

2. **Use permission checks**
   ```python
   @require_permission("write:documents")
   ```

3. **Enable audit logging**
   ```python
   # Automatically logged for all permission changes
   ```

4. **Use region-aware storage**
   ```python
   # Storage is automatically routed to correct region
   await RegionStorageService.upload_file(region=org.region, ...)
   ```

### For Mobile

1. **Store tokens securely**
   - Use Keychain (iOS) / Keystore (Android)
   - Never store in AsyncStorage

2. **Enable biometric when available**
   ```typescript
   await biometricService.isBiometricAvailable();
   await enableBiometric();
   ```

3. **Encrypt sensitive local data**
   ```typescript
   // MMKV automatically encrypts
   storageService.set('sensitive_data', data);
   ```

4. **Handle offline gracefully**
   ```typescript
   storageService.addToOfflineQueue(item);
   ```

---

## Support

For questions or issues:
- **Documentation**: https://docs.saas-ocr.com
- **Email**: support@saas-ocr.com
- **GitHub**: https://github.com/your-org/saas-ocr

## License

Proprietary - All rights reserved
