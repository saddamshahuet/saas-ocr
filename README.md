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