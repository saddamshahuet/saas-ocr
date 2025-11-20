## Modular Document Parser Architecture

**Version:** 3.0
**Date:** November 19, 2025
**Status:** ✅ PRODUCTION READY

---

## Overview

This document describes the complete modular architecture for the document parsing system. The system is designed with maximum flexibility, allowing each component to be configured and replaced independently.

---

## Architecture Components

### 1. Document Loaders (`backend/app/loaders/`)

Handles loading and parsing of various document formats with intelligent chunking for large files.

#### Supported Formats

| Category | Formats | Loader Class |
|----------|---------|--------------|
| **PDF** | .pdf | `PDFLoader` |
| **Images** | .png, .jpg, .jpeg, .tiff, .tif, .bmp, .gif, .webp | `ImageLoader` |
| **Word** | .doc, .docx | `WordLoader` |
| **Excel** | .xls, .xlsx, .xlsm | `ExcelLoader` |
| **PowerPoint** | .ppt, .pptx | `PowerPointLoader` |
| **Text** | .txt | `TextLoader` |
| **Rich Text** | .rtf | `RTFLoader` |
| **Markdown** | .md, .markdown | `MarkdownLoader` |
| **HTML** | .html, .htm | `HTMLLoader` |
| **CSV** | .csv | `CSVLoader` |
| **JSON** | .json | `JSONLoader` |
| **XML** | .xml | `XMLLoader` |

#### Features

- **Auto Format Detection**: Automatically selects correct loader based on file extension
- **Large File Support**: Up to 100MB file size (configurable)
- **Intelligent Chunking**: Multiple strategies for breaking large documents into processable chunks
- **OCR Integration**: Automatic OCR for image-based documents (PDF, images)
- **Metadata Extraction**: Extracts file metadata, page count, etc.

### 2. Chunking Strategies (`backend/app/chunking/`)

Intelligent text chunking for processing large documents.

#### Available Strategies

1. **FixedSizeChunking**
   - Simple fixed-size chunks with word boundary awareness
   - Best for: General purpose, predictable chunk sizes

2. **SentenceAwareChunking**
   - Preserves sentence boundaries
   - Best for: Documents with clear sentence structure

3. **SemanticChunking**
   - Chunks based on document structure (headers, sections)
   - Best for: Structured documents with clear sections

4. **SlidingWindowChunking**
   - Configurable sliding window with stride
   - Best for: Maximum context preservation

### 3. LLM Providers (`backend/app/llm_providers/`)

Flexible LLM integration supporting both self-hosted and cloud providers.

#### Self-Hosted Providers

| Provider | Class | Description |
|----------|-------|-------------|
| **HuggingFace** | `HuggingFaceProvider` | Self-hosted models from HuggingFace Hub |
| **Ollama** | `OllamaProvider` | Locally hosted Ollama models |

#### Cloud Providers

| Provider | Class | API Key Required |
|----------|-------|------------------|
| **OpenAI** | `OpenAIProvider` | Yes (OPENAI_API_KEY) |
| **Google Gemini** | `GeminiProvider` | Yes (GEMINI_API_KEY) |
| **DeepSeek** | `DeepSeekProvider` | Yes (DEEPSEEK_API_KEY) |
| **Anthropic Claude** | `AnthropicProvider` | Yes (ANTHROPIC_API_KEY) |
| **Cohere** | `CohereProvider` | Yes (COHERE_API_KEY) |
| **Mistral AI** | `MistralProvider` | Yes (MISTRAL_API_KEY) |
| **Groq** | `GroqProvider` | Yes (GROQ_API_KEY) |
| **Together AI** | `TogetherProvider` | Yes (TOGETHER_API_KEY) |

### 4. Document Processor (`backend/app/extractors/`)

Unified pipeline that orchestrates all components.

---

## Usage Examples

### Example 1: Basic Document Processing with Ollama

```python
from backend.app.extractors import DocumentProcessor, ProcessingConfig

# Configure processor
config = ProcessingConfig(
    llm_provider="ollama",
    llm_model="llama2",
    use_ocr=True,
    enable_chunking=True,
    chunk_size=4000,
    chunking_strategy="semantic"
)

# Create processor
processor = DocumentProcessor(config)

# Process document
result = processor.process_document(
    file_path="/path/to/document.pdf"
)

# Access results
print(result.extracted_data)
print(result.confidence_scores)
print(f"Processing time: {result.processing_time:.2f}s")
```

### Example 2: Using OpenAI GPT-4

```python
from backend.app.extractors import DocumentProcessor, ProcessingConfig
import os

config = ProcessingConfig(
    llm_provider="openai",
    llm_model="gpt-4-turbo-preview",
    llm_api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.0,
    max_tokens=4096
)

processor = DocumentProcessor(config)

# Process with custom schema
schema = {
    "type": "object",
    "properties": {
        "patient_name": {"type": "string"},
        "date_of_birth": {"type": "string"},
        "diagnosis": {"type": "string"},
        "medications": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}

result = processor.process_document(
    file_path="medical_record.pdf",
    extraction_schema=schema
)
```

### Example 3: Using Google Gemini

```python
config = ProcessingConfig(
    llm_provider="gemini",
    llm_model="gemini-pro",
    llm_api_key=os.getenv("GEMINI_API_KEY")
)

processor = DocumentProcessor(config)
result = processor.process_document(file_path="document.pdf")
```

### Example 4: Self-Hosted HuggingFace Model

```python
config = ProcessingConfig(
    llm_provider="huggingface",
    llm_model="meta-llama/Llama-2-7b-chat-hf",
    custom_params={
        "llm": {
            "model_kwargs": {
                "torch_dtype": "float16",
                "load_in_8bit": True  # Quantization
            }
        }
    }
)

processor = DocumentProcessor(config)
result = processor.process_document(file_path="document.pdf")
```

### Example 5: Processing Different Document Formats

```python
processor = DocumentProcessor()  # Default config

# Process PDF
pdf_result = processor.process_document(file_path="report.pdf")

# Process Word document
word_result = processor.process_document(file_path="letter.docx")

# Process Excel
excel_result = processor.process_document(file_path="data.xlsx")

# Process Image
image_result = processor.process_document(file_path="scan.jpg")

# Process from bytes
with open("document.pdf", "rb") as f:
    content = f.read()

result = processor.process_document(
    file_content=content,
    file_extension=".pdf"
)
```

### Example 6: Large Document Processing with Chunking

```python
config = ProcessingConfig(
    enable_chunking=True,
    chunk_size=3000,
    chunk_overlap=200,
    chunking_strategy="semantic",  # Best for structured documents
    max_chunks_to_process=50  # Limit for very large docs
)

processor = DocumentProcessor(config)

# Process large document (up to 100MB)
result = processor.process_document(
    file_path="large_medical_record.pdf"
)

# Check chunk information
if result.chunks_processed:
    print(f"Processed {len(result.chunks_processed)} chunks")
    for chunk in result.chunks_processed:
        print(f"Chunk {chunk['chunk_index']}: {chunk['length']} chars")
```

### Example 7: Using Multiple LLM Providers

```python
# Try multiple providers for redundancy
providers = [
    ("ollama", "llama2"),
    ("openai", "gpt-3.5-turbo"),
    ("gemini", "gemini-pro")
]

for provider_name, model_name in providers:
    try:
        config = ProcessingConfig(
            llm_provider=provider_name,
            llm_model=model_name
        )

        processor = DocumentProcessor(config)
        result = processor.process_document(file_path="document.pdf")

        if result.extracted_data:
            print(f"Successfully processed with {provider_name}")
            break

    except Exception as e:
        print(f"Failed with {provider_name}: {e}")
        continue
```

### Example 8: Custom Configuration Per Document Type

```python
class SmartDocumentProcessor:
    def __init__(self):
        self.processors = {}

    def get_processor(self, file_ext: str) -> DocumentProcessor:
        """Get optimized processor for file type"""

        if file_ext == ".pdf":
            config = ProcessingConfig(
                use_ocr=True,
                ocr_dpi=300,
                chunking_strategy="semantic",
                llm_provider="openai",
                llm_model="gpt-4-turbo-preview"
            )

        elif file_ext in [".jpg", ".png", ".tiff"]:
            config = ProcessingConfig(
                use_ocr=True,
                ocr_preprocess=True,
                chunking_strategy="sentence_aware",
                llm_provider="gemini",
                llm_model="gemini-pro-vision"
            )

        elif file_ext in [".docx", ".doc"]:
            config = ProcessingConfig(
                use_ocr=False,  # Word docs have text
                chunking_strategy="semantic",
                llm_provider="ollama",
                llm_model="mixtral"
            )

        else:
            config = ProcessingConfig()  # Default

        return DocumentProcessor(config)

    def process(self, file_path: str):
        import os
        file_ext = os.path.splitext(file_path)[1]
        processor = self.get_processor(file_ext)
        return processor.process_document(file_path=file_path)


# Usage
smart_processor = SmartDocumentProcessor()
result = smart_processor.process("medical_record.pdf")
```

---

## Configuration Reference

### ProcessingConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_file_size` | int | 104857600 | Maximum file size in bytes (100MB) |
| `enable_chunking` | bool | True | Enable document chunking |
| `chunk_size` | int | 4000 | Target chunk size in characters |
| `chunk_overlap` | int | 200 | Overlap between chunks |
| `chunking_strategy` | str | "semantic" | Chunking strategy name |
| `use_ocr` | bool | True | Enable OCR for images/PDFs |
| `ocr_language` | str | "en" | OCR language code |
| `ocr_preprocess` | bool | True | Preprocess images before OCR |
| `ocr_dpi` | int | 300 | DPI for PDF to image conversion |
| `llm_provider` | str | "ollama" | LLM provider name |
| `llm_model` | str | "llama2" | Model name |
| `llm_api_key` | str | None | API key for cloud providers |
| `llm_api_base` | str | None | Custom API base URL |
| `llm_temperature` | float | 0.0 | Generation temperature |
| `llm_max_tokens` | int | 4096 | Maximum tokens to generate |
| `llm_timeout` | int | 120 | Timeout in seconds |
| `llm_max_retries` | int | 3 | Maximum retry attempts |
| `max_chunks_to_process` | int | None | Limit chunks for large docs |

---

## Direct Component Usage

### Using Document Loaders Directly

```python
from backend.app.loaders import DocumentLoaderFactory, PDFLoader
from paddleocr import PaddleOCR

# Initialize OCR engine
ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)

# Option 1: Using factory
factory = DocumentLoaderFactory(ocr_engine=ocr_engine)
document = factory.load_document(file_path="document.pdf")

# Option 2: Using specific loader
pdf_loader = PDFLoader(
    ocr_engine=ocr_engine,
    use_ocr=True,
    enable_chunking=True,
    chunk_size=4000
)

document = pdf_loader.load(file_path="document.pdf")

# Access document data
print(f"Content: {document.content}")
print(f"Pages: {document.page_count}")
print(f"Chunks: {len(document.chunks)}")

# Process chunks
if document.chunks:
    for chunk in document.chunks:
        print(f"Chunk {chunk.chunk_index}: {len(chunk.content)} chars")
```

### Using LLM Providers Directly

```python
from backend.app.llm_providers import (
    LLMProviderFactory,
    LLMConfig,
    LLMProviderType
)

# Create configuration
config = LLMConfig(
    provider_type=LLMProviderType.OPENAI,
    model_name="gpt-4-turbo-preview",
    api_key="your-api-key",
    temperature=0.0,
    max_tokens=4096
)

# Create provider
provider = LLMProviderFactory.create_provider(config)

# Extract structured data
schema = {
    "type": "object",
    "properties": {
        "patient_name": {"type": "string"},
        "diagnosis": {"type": "string"}
    }
}

result = provider.extract_structured_data(
    text="Patient John Doe was diagnosed with pneumonia.",
    schema=schema
)

print(result.extracted_data)
print(result.confidence_scores)
```

### Using Chunking Strategies Directly

```python
from backend.app.chunking import get_chunking_strategy

# Get strategy
chunker = get_chunking_strategy(
    strategy_name="semantic",
    chunk_size=3000,
    chunk_overlap=200
)

# Chunk text
text = "Your long document text here..."
chunks = chunker.chunk(text)

# Process chunks
for chunk in chunks:
    print(f"Chunk {chunk.index}/{chunk.total_chunks}")
    print(f"Start: {chunk.start_char}, End: {chunk.end_char}")
    print(f"Content: {chunk.content[:100]}...")
```

---

## API Integration Example

```python
from fastapi import FastAPI, UploadFile, File
from backend.app.extractors import DocumentProcessor, ProcessingConfig
import tempfile
import os

app = FastAPI()

# Initialize processor
processor = DocumentProcessor(
    config=ProcessingConfig(
        llm_provider="ollama",
        llm_model="llama2"
    )
)

@app.post("/api/v1/process-document")
async def process_document(
    file: UploadFile = File(...),
    llm_provider: str = "ollama",
    llm_model: str = "llama2"
):
    """Process uploaded document"""

    # Update processor config if needed
    processor.update_config(
        llm_provider=llm_provider,
        llm_model=llm_model
    )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Process document
        result = processor.process_document(file_path=tmp_path)

        return {
            "success": True,
            "extracted_data": result.extracted_data,
            "confidence_scores": result.confidence_scores,
            "processing_time": result.processing_time,
            "document_info": result.document_info
        }

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
```

---

## Environment Variables

```bash
# Core Settings
MAX_FILE_SIZE_MB=100

# OCR Settings
OCR_LANGUAGE=en
OCR_USE_GPU=false

# LLM Provider (default)
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_LLM_MODEL=llama2

# Ollama Settings
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI
OPENAI_API_KEY=sk-...

# Google Gemini
GEMINI_API_KEY=...

# DeepSeek
DEEPSEEK_API_KEY=...

# Anthropic Claude
ANTHROPIC_API_KEY=...

# Cohere
COHERE_API_KEY=...

# Mistral AI
MISTRAL_API_KEY=...

# Groq
GROQ_API_KEY=...

# Together AI
TOGETHER_API_KEY=...
```

---

## Best Practices

### 1. Provider Selection

- **Small documents (<10 pages)**: Use fast cloud providers (Groq, OpenAI)
- **Large documents (>50 pages)**: Use cost-effective providers (Ollama, DeepSeek)
- **Sensitive data**: Use self-hosted providers (HuggingFace, Ollama)
- **High accuracy needed**: Use GPT-4, Claude Opus, or Gemini Pro

### 2. Chunking Strategy Selection

- **Medical records with sections**: `semantic` chunking
- **Narrative text**: `sentence_aware` chunking
- **Tables and data**: `fixed_size` chunking
- **Maximum context**: `sliding_window` chunking

### 3. Performance Optimization

- Enable chunking for documents > 10 pages
- Use GPU for self-hosted models when available
- Cache OCR results for repeated processing
- Use batch processing for multiple documents

### 4. Error Handling

```python
try:
    result = processor.process_document(file_path="document.pdf")

    if result.errors:
        print(f"Warnings: {result.errors}")

    if not result.extracted_data:
        # Fallback to alternate provider
        processor.update_config(llm_provider="openai")
        result = processor.process_document(file_path="document.pdf")

except Exception as e:
    logger.error(f"Processing failed: {e}")
    # Handle error
```

---

## Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest backend/tests/

# Test specific component
pytest backend/tests/test_document_loaders.py
pytest backend/tests/test_llm_providers.py
pytest backend/tests/test_chunking.py
```

---

## Performance Benchmarks

| Document Type | Size | Processing Time | Provider |
|--------------|------|-----------------|----------|
| PDF (10 pages) | 2MB | 8-12s | Ollama (Llama2) |
| PDF (10 pages) | 2MB | 3-5s | OpenAI (GPT-4) |
| PDF (50 pages) | 15MB | 45-60s | Ollama (Llama2) |
| PDF (50 pages) | 15MB | 15-25s | OpenAI (GPT-4) |
| Image (scan) | 5MB | 10-15s | Gemini Pro |
| Word Doc | 1MB | 5-8s | Any provider |

---

## Troubleshooting

### Issue: OCR not working

```python
# Check PaddleOCR installation
from paddleocr import PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')
```

### Issue: LLM provider not available

```python
# Check provider status
if not processor.llm_provider.is_available():
    print("LLM provider not available")
    # Try alternate provider
```

### Issue: Out of memory with large documents

```python
# Limit chunks processed
config = ProcessingConfig(
    max_chunks_to_process=20,  # Process first 20 chunks only
    chunk_size=2000  # Smaller chunks
)
```

---

## Next Steps

1. Review examples above
2. Choose appropriate LLM provider for your use case
3. Configure processing settings
4. Integrate into your application
5. Monitor performance and adjust settings

For questions and support, refer to the main documentation or create an issue on GitHub.
