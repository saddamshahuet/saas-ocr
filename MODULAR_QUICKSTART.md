# Modular Document Parser - Quick Start Guide

## Installation

```bash
# Clone repository
git clone <repository-url>
cd saas-ocr

# Install dependencies
pip install -r requirements.txt

# Optional: Install Ollama for local LLM
# Visit: https://ollama.ai
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama2
```

## Quick Start

### 1. Simple Document Processing

```python
from backend.app.extractors import DocumentProcessor

# Create processor (uses Ollama by default)
processor = DocumentProcessor()

# Process any document
result = processor.process_document(file_path="your_document.pdf")

# Get results
print(result.extracted_data)
```

### 2. Using Cloud LLM (OpenAI)

```python
from backend.app.extractors import DocumentProcessor, ProcessingConfig
import os

config = ProcessingConfig(
    llm_provider="openai",
    llm_model="gpt-4-turbo-preview",
    llm_api_key=os.getenv("OPENAI_API_KEY")
)

processor = DocumentProcessor(config)
result = processor.process_document(file_path="document.pdf")
```

### 3. Supported Document Formats

| Format | Extension | Example |
|--------|-----------|---------|
| PDF | .pdf | `processor.process_document("file.pdf")` |
| Word | .docx, .doc | `processor.process_document("file.docx")` |
| Excel | .xlsx, .xls | `processor.process_document("file.xlsx")` |
| PowerPoint | .pptx, .ppt | `processor.process_document("file.pptx")` |
| Images | .jpg, .png, .tiff | `processor.process_document("scan.jpg")` |
| Text | .txt, .rtf, .md | `processor.process_document("file.txt")` |
| Data | .csv, .json, .xml | `processor.process_document("data.csv")` |
| Web | .html | `processor.process_document("page.html")` |

## Supported LLM Providers

### Self-Hosted (Free)

```python
# Ollama (recommended for local use)
config = ProcessingConfig(
    llm_provider="ollama",
    llm_model="llama2"  # or mistral, codellama, mixtral
)

# HuggingFace
config = ProcessingConfig(
    llm_provider="huggingface",
    llm_model="meta-llama/Llama-2-7b-chat-hf"
)
```

### Cloud-Based

```python
# OpenAI
config = ProcessingConfig(
    llm_provider="openai",
    llm_model="gpt-4-turbo-preview",
    llm_api_key=os.getenv("OPENAI_API_KEY")
)

# Google Gemini
config = ProcessingConfig(
    llm_provider="gemini",
    llm_model="gemini-pro",
    llm_api_key=os.getenv("GEMINI_API_KEY")
)

# DeepSeek (cost-effective)
config = ProcessingConfig(
    llm_provider="deepseek",
    llm_model="deepseek-chat",
    llm_api_key=os.getenv("DEEPSEEK_API_KEY")
)

# Anthropic Claude
config = ProcessingConfig(
    llm_provider="anthropic",
    llm_model="claude-3-sonnet-20240229",
    llm_api_key=os.getenv("ANTHROPIC_API_KEY")
)

# And more: Cohere, Mistral AI, Groq, Together AI
```

## Environment Setup

Create `.env` file:

```bash
# LLM API Keys (optional - only for cloud providers you want to use)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...
ANTHROPIC_API_KEY=...
COHERE_API_KEY=...
MISTRAL_API_KEY=...
GROQ_API_KEY=...
TOGETHER_API_KEY=...

# Ollama URL (if using Ollama)
OLLAMA_BASE_URL=http://localhost:11434

# OCR Settings
OCR_LANGUAGE=en
```

## Advanced Usage

### Custom Extraction Schema

```python
schema = {
    "type": "object",
    "properties": {
        "patient_name": {"type": "string"},
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

### Large Document Processing

```python
config = ProcessingConfig(
    enable_chunking=True,
    chunk_size=4000,
    chunk_overlap=200,
    chunking_strategy="semantic",  # or: fixed_size, sentence_aware, sliding_window
    max_chunks_to_process=50  # Limit for very large docs
)

processor = DocumentProcessor(config)
result = processor.process_document(file_path="large_document.pdf")
```

### Provider Fallback

```python
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
            break
    except:
        continue
```

## Architecture

```
Document Processing Pipeline
├── Document Loaders (12+ formats)
│   ├── PDF Loader (with OCR)
│   ├── Image Loader (with OCR)
│   ├── Office Loaders (Word, Excel, PowerPoint)
│   └── Text Loaders (TXT, RTF, MD, HTML, CSV, JSON, XML)
│
├── Chunking Strategies
│   ├── Fixed Size Chunking
│   ├── Sentence Aware Chunking
│   ├── Semantic Chunking
│   └── Sliding Window Chunking
│
├── LLM Providers (10+ providers)
│   ├── Self-Hosted: HuggingFace, Ollama
│   └── Cloud: OpenAI, Gemini, DeepSeek, Anthropic, Cohere, Mistral, Groq, Together
│
└── Document Processor (Unified Pipeline)
    ├── Load document
    ├── Apply OCR (if needed)
    ├── Chunk content (if needed)
    ├── Extract with LLM
    └── Return structured data
```

## Key Features

✅ **12+ Document Formats**: PDF, Word, Excel, PowerPoint, Images, and more
✅ **10+ LLM Providers**: Self-hosted and cloud options
✅ **100MB File Support**: Intelligent chunking for large documents
✅ **4 Chunking Strategies**: Fixed, Sentence-aware, Semantic, Sliding window
✅ **OCR Integration**: Automatic OCR for scanned documents
✅ **Modular Design**: Each component independently configurable
✅ **Production Ready**: Error handling, retries, confidence scoring
✅ **Zero Vendor Lock-in**: Switch LLM providers with single line change

## Examples

See `examples/example_usage.py` for comprehensive examples including:

- Basic document processing
- Custom LLM provider configuration
- Direct component usage
- Custom extraction schemas
- Chunking strategies
- Large document processing
- Batch processing
- Provider fallback
- Custom pipelines

## Documentation

- [MODULAR_ARCHITECTURE.md](./MODULAR_ARCHITECTURE.md) - Complete architecture documentation
- [examples/example_usage.py](./examples/example_usage.py) - Code examples
- [API Documentation](#) - API endpoint documentation

## Troubleshooting

### OCR Not Working

```bash
# Install system dependencies
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr poppler-utils

# macOS:
brew install tesseract poppler
```

### Ollama Not Available

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama2

# Verify it's running
curl http://localhost:11434/api/tags
```

### GPU Support

```bash
# For CUDA support (NVIDIA GPUs)
pip install paddlepaddle-gpu torch torchvision torchaudio

# For CPU only
pip install paddlepaddle torch torchvision torchaudio
```

## Performance Tips

1. **Use Ollama for local processing**: Free and fast
2. **Use Groq for cloud processing**: Fastest cloud inference
3. **Use DeepSeek for cost-effective**: Best price/performance ratio
4. **Enable chunking for large docs**: Better memory management
5. **Use semantic chunking**: Best for structured documents

## Support

For issues and questions:
- GitHub Issues: [Create issue](#)
- Documentation: [Full docs](./MODULAR_ARCHITECTURE.md)
- Examples: [See examples](./examples/)

## License

MIT License - See LICENSE file

---

**Ready to process your documents!** 🚀

Start with: `processor = DocumentProcessor()` and `result = processor.process_document("your_file.pdf")`
