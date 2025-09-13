# Software Requirements Specification (SRS)

## 1. Introduction
### 1.1 Purpose
Define the functional and non-functional requirements for the AI-powered OCR & Data Extraction Service.

### 1.2 Scope
Service to extract structured data from various document types for hospice and palliative care.

## 2. Overall Description
- Cloud-hosted Python API
- Accepts documents (PDF, image, Word, etc.)
- Returns JSON with extracted fields

## 3. Functional Requirements
- Upload document via API
- Extract fields: Patient Name, DoB, Allergies, Carer Info, etc.
- Return data in specified JSON schema
- Support for multi-page, mixed-format documents

## 4. Non-Functional Requirements
- High accuracy (target >95%)
- Response time < 10s per document
- Secure data handling (encryption in transit & at rest)
- Scalable cloud infrastructure

## 5. Constraints
- Must use cloud GPU/TPU resources
- No local hosting

## 6. Assumptions
- JSON schema provided per use case
- Cloud provider supports required compute
