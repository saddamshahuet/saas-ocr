# System Architecture

## Overview
The system consists of a cloud-hosted API that orchestrates OCR and LLM-based data extraction pipelines.

## Components
- **API Gateway**: Receives document uploads and returns JSON results
- **OCR Engine**: Extracts text from images/PDFs
- **LLM Extraction Module**: Parses text and extracts structured fields
- **Schema Mapper**: Formats output to required JSON schema
- **Cloud Infrastructure**: Provides scalable GPU/TPU resources

## Data Flow
1. User uploads document via API
2. OCR engine processes document
3. LLM module extracts structured data
4. Output mapped to JSON schema
5. JSON returned to user

## Security
- All data encrypted in transit and at rest
- Access via authenticated API keys
