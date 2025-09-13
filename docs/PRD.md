# Product Requirements Document (PRD)

## Project Overview
AI-powered OCR & Data Extraction Service for Hospice & Palliative Care. The system extracts structured data from any document type and outputs it in a well-defined JSON schema.

## Goals
- Extract key patient and care information from diverse document types
- Output structured data in a customizable JSON schema
- Provide a scalable, cost-effective API service

## Features
- Accepts scanned PDFs, images, Word docs, handwritten/printed text
- Extracts fields: Patient Name, DoB, Allergies, Carer Info, etc.
- JSON output per use-case schema
- API-based access
- Usage-based billing (per call/token)

## Target Users
- Hospice and palliative care providers
- Healthcare IT integrators

## Success Metrics
- Extraction accuracy
- API response time
- Cost per document

## Constraints
- High compute requirements (GPU/TPU)
- Cloud-based hosting only

## Out of Scope
- Manual data entry
- On-premise deployment
