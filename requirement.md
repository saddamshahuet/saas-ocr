# Project Idea: AI-Powered OCR & Data Extraction Service for Hospice & Palliative Care

## Context
We want to design and implement an **AI-driven OCR and structured data extraction service**. The system should handle **any type of document** (scanned PDFs, Word docs, images, handwritten or printed text, mixed layouts, etc.) and extract **specific information** relevant to hospice and palliative care.  
Examples of extracted data fields include:
- Patient Name  
- Date of Birth (DoB)  
- Allergies  
- Carer Information  
- Other relevant structured attributes  

The extracted data must be transformed into a **well-defined JSON schema** (which will be provided per use case, along with sample examples).  

## Current Approach
The client is currently considering **Google Gemini API subscription**, where the workflow would be:  
1. Provide a document to Gemini API.  
2. Send a carefully crafted user-defined prompt (including JSON schema + examples).  
3. Gemini processes and extracts the requested data.  
4. JSON is returned in the required schema.  

Since **Gemini API usage is priced per million tokens** (model-dependent), costs will vary depending on document size and usage volume.  

## Business Opportunity
Instead of relying fully on a third-party service, we see a potential business case in:  
- **Self-hosting** or **cloud-hosting** a robust, open-source OCR + LLM pipeline.  
- Offering this as a **Python API service** with structured JSON output.  
- Monetizing through **per-API call** or **per-token usage billing** for clients.  

## Challenges
- AI models for OCR + LLM reasoning are **compute expensive**, requiring high-spec GPUs/TPUs.  
- Local in-house hosting is not feasible due to lack of infrastructure.  
- Need to explore **cloud-based AI hosting providers** that offer:  
  - Pay-per-use pricing (hourly, per-call, or per-execution).  
  - Flexible scaling.  
  - Reasonable costs for OCR + long-context LLM workloads.  

## Research & Planning Requirements
To move forward, the following **deliverables** are needed:

### 1. AI Model Research
- Identify **AI models capable of OCR + structured extraction**.  
- Must handle:  
  - Multi-page long documents (50+ pages).  
  - Mixed formats (handwriting, scanned text, digital text).  
  - Long prompts (to include schema + instructions).  
- Compare open-source vs proprietary models (e.g., Gemini, GPT-4, Claude, Llama 3, Donut, LayoutLMv3, etc.).

### 2. Cloud/Hosting Platforms
- Research **10–15 cloud platforms** providing GPU/TPU-based AI hosting.  
- Document their **machine specs + pricing**.  
- Compare services offering:  
  - Pay-per-hour machines.  
  - Serverless/on-demand execution models.  
  - Fixed dedicated GPU rentals.  

### 3. Comparison Matrix
Create a **tabular comparison** including:  
- Platform Name  
- GPU/CPU Specs Offered  
- RAM/Storage  
- Pricing (hourly, monthly, per-execution)  
- Flexibility (scaling, spot instances, serverless availability)  
- Notes/Limitations  

### 4. Financial Model
- Estimate **cost of operating per document / per API call**.  
- Compare different scenarios (short docs vs long docs).  
- Suggest **client pricing models** (markup strategies):  
  - Per document.  
  - Per page.  
  - Per API call.  
  - Per token (if LLM-backed).  

### 5. Implementation Options
- Explore feasibility of:  
  - Hosting a **fixed AI-capable machine** full-time.  
  - Using **on-demand cloud services** (pay when needed).  
- Analyze trade-offs (cost, latency, availability, scaling).  

---

✅ **Goal:** Produce a **comprehensive feasibility study + business model plan** that includes technical model selection, hosting provider comparison, and financial viability.  
