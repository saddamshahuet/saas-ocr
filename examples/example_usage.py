"""
Example usage of the modular document parser system

This script demonstrates various usage patterns for the document processing system.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.extractors import DocumentProcessor, ProcessingConfig, ProcessingStrategy
from backend.app.loaders import DocumentLoaderFactory, load_document
from backend.app.llm_providers import create_llm_provider, LLMProviderFactory
from backend.app.chunking import get_chunking_strategy


def example1_basic_usage():
    """Example 1: Basic document processing with default settings"""
    print("\n" + "="*60)
    print("Example 1: Basic Document Processing")
    print("="*60)

    # Create processor with default configuration
    processor = DocumentProcessor()

    # Process a document
    # Note: Replace with your actual file path
    result = processor.process_document(
        file_path="sample_document.pdf"
    )

    print(f"Processing time: {result.processing_time:.2f}s")
    print(f"Extracted data: {result.extracted_data}")
    print(f"Confidence scores: {result.confidence_scores}")


def example2_custom_llm_provider():
    """Example 2: Using different LLM providers"""
    print("\n" + "="*60)
    print("Example 2: Custom LLM Provider Configuration")
    print("="*60)

    # Option A: Using Ollama (local, free)
    print("\n--- Using Ollama ---")
    config_ollama = ProcessingConfig(
        llm_provider="ollama",
        llm_model="llama2",
        llm_api_base="http://localhost:11434"
    )

    processor = DocumentProcessor(config_ollama)

    # Option B: Using OpenAI
    print("\n--- Using OpenAI ---")
    config_openai = ProcessingConfig(
        llm_provider="openai",
        llm_model="gpt-4-turbo-preview",
        llm_api_key=os.getenv("OPENAI_API_KEY"),
        llm_temperature=0.0
    )

    processor = DocumentProcessor(config_openai)

    # Option C: Using Google Gemini
    print("\n--- Using Google Gemini ---")
    config_gemini = ProcessingConfig(
        llm_provider="gemini",
        llm_model="gemini-pro",
        llm_api_key=os.getenv("GEMINI_API_KEY")
    )

    processor = DocumentProcessor(config_gemini)

    # Option D: Using DeepSeek (cost-effective)
    print("\n--- Using DeepSeek ---")
    config_deepseek = ProcessingConfig(
        llm_provider="deepseek",
        llm_model="deepseek-chat",
        llm_api_key=os.getenv("DEEPSEEK_API_KEY")
    )

    processor = DocumentProcessor(config_deepseek)


def example3_document_loaders():
    """Example 3: Using document loaders directly"""
    print("\n" + "="*60)
    print("Example 3: Direct Document Loader Usage")
    print("="*60)

    # Initialize factory
    factory = DocumentLoaderFactory()

    # Load different document types
    print("\n--- Loading PDF ---")
    pdf_doc = factory.load_document(file_path="sample.pdf")
    print(f"Pages: {pdf_doc.page_count}")
    print(f"Chunks: {len(pdf_doc.chunks) if pdf_doc.chunks else 0}")

    print("\n--- Loading Word Document ---")
    word_doc = factory.load_document(file_path="sample.docx")
    print(f"Content length: {len(word_doc.content)}")

    print("\n--- Loading Image ---")
    image_doc = factory.load_document(file_path="sample.jpg")
    print(f"Content extracted: {len(image_doc.content)} characters")

    print("\n--- Loading Excel ---")
    excel_doc = factory.load_document(file_path="sample.xlsx")
    print(f"Sheets processed: {excel_doc.page_count}")


def example4_custom_schema():
    """Example 4: Custom extraction schema"""
    print("\n" + "="*60)
    print("Example 4: Custom Extraction Schema")
    print("="*60)

    # Define custom schema for medical records
    medical_schema = {
        "type": "object",
        "properties": {
            "patient_demographics": {
                "type": "object",
                "properties": {
                    "full_name": {
                        "type": "string",
                        "description": "Patient's full name"
                    },
                    "date_of_birth": {
                        "type": "string",
                        "description": "Date of birth in MM/DD/YYYY format"
                    },
                    "gender": {
                        "type": "string",
                        "enum": ["Male", "Female", "Other"]
                    },
                    "medical_record_number": {
                        "type": "string",
                        "description": "Unique medical record identifier"
                    }
                }
            },
            "medical_information": {
                "type": "object",
                "properties": {
                    "primary_diagnosis": {
                        "type": "string",
                        "description": "Primary medical diagnosis"
                    },
                    "allergies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of known allergies"
                    },
                    "current_medications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "medication_name": {"type": "string"},
                                "dosage": {"type": "string"},
                                "frequency": {"type": "string"}
                            }
                        }
                    },
                    "dnr_status": {
                        "type": "boolean",
                        "description": "Do Not Resuscitate status"
                    }
                }
            },
            "provider_information": {
                "type": "object",
                "properties": {
                    "attending_physician": {"type": "string"},
                    "physician_phone": {"type": "string"}
                }
            }
        }
    }

    processor = DocumentProcessor()

    result = processor.process_document(
        file_path="medical_record.pdf",
        extraction_schema=medical_schema
    )

    print("Extracted data:")
    print(result.extracted_data)


def example5_chunking_strategies():
    """Example 5: Different chunking strategies"""
    print("\n" + "="*60)
    print("Example 5: Chunking Strategies")
    print("="*60)

    sample_text = """
    This is a sample document with multiple sections.

    Section 1: Introduction
    This section introduces the topic.

    Section 2: Methods
    This section describes the methodology used.

    Section 3: Results
    This section presents the results.
    """

    # Strategy 1: Fixed Size
    print("\n--- Fixed Size Chunking ---")
    fixed_chunker = get_chunking_strategy(
        strategy_name="fixed_size",
        chunk_size=100,
        chunk_overlap=20
    )
    fixed_chunks = fixed_chunker.chunk(sample_text)
    print(f"Created {len(fixed_chunks)} chunks")

    # Strategy 2: Sentence Aware
    print("\n--- Sentence Aware Chunking ---")
    sentence_chunker = get_chunking_strategy(
        strategy_name="sentence_aware",
        chunk_size=100,
        chunk_overlap=20
    )
    sentence_chunks = sentence_chunker.chunk(sample_text)
    print(f"Created {len(sentence_chunks)} chunks")

    # Strategy 3: Semantic
    print("\n--- Semantic Chunking ---")
    semantic_chunker = get_chunking_strategy(
        strategy_name="semantic",
        chunk_size=200,
        chunk_overlap=20
    )
    semantic_chunks = semantic_chunker.chunk(sample_text)
    print(f"Created {len(semantic_chunks)} chunks")

    for i, chunk in enumerate(semantic_chunks, 1):
        print(f"\nChunk {i}:")
        print(chunk.content[:100] + "...")


def example6_large_document_processing():
    """Example 6: Processing large documents"""
    print("\n" + "="*60)
    print("Example 6: Large Document Processing")
    print("="*60)

    # Configuration for large documents
    config = ProcessingConfig(
        max_file_size=100 * 1024 * 1024,  # 100MB
        enable_chunking=True,
        chunk_size=3000,
        chunk_overlap=200,
        chunking_strategy="semantic",
        processing_strategy=ProcessingStrategy.CHUNKED,
        max_chunks_to_process=50  # Limit processing
    )

    processor = DocumentProcessor(config)

    result = processor.process_document(
        file_path="large_document.pdf"
    )

    print(f"Processing time: {result.processing_time:.2f}s")
    print(f"Chunks processed: {len(result.chunks_processed)}")

    if result.chunks_processed:
        total_chars = sum(c['length'] for c in result.chunks_processed)
        print(f"Total characters processed: {total_chars}")


def example7_multi_format_batch():
    """Example 7: Batch processing multiple document formats"""
    print("\n" + "="*60)
    print("Example 7: Batch Processing Multiple Formats")
    print("="*60)

    processor = DocumentProcessor()

    # List of documents to process
    documents = [
        "document1.pdf",
        "document2.docx",
        "document3.jpg",
        "document4.xlsx"
    ]

    results = []

    for doc_path in documents:
        print(f"\nProcessing: {doc_path}")

        try:
            result = processor.process_document(file_path=doc_path)
            results.append({
                "file": doc_path,
                "success": True,
                "data": result.extracted_data,
                "time": result.processing_time
            })
            print(f"✓ Success ({result.processing_time:.2f}s)")

        except Exception as e:
            results.append({
                "file": doc_path,
                "success": False,
                "error": str(e)
            })
            print(f"✗ Failed: {e}")

    # Summary
    print("\n--- Batch Processing Summary ---")
    successful = sum(1 for r in results if r['success'])
    print(f"Processed: {len(results)} documents")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")


def example8_provider_fallback():
    """Example 8: Provider fallback strategy"""
    print("\n" + "="*60)
    print("Example 8: Provider Fallback Strategy")
    print("="*60)

    # Define provider priority order
    providers = [
        ("ollama", "llama2"),
        ("openai", "gpt-3.5-turbo"),
        ("gemini", "gemini-pro"),
        ("deepseek", "deepseek-chat")
    ]

    document_path = "sample.pdf"

    for provider_name, model_name in providers:
        print(f"\nTrying provider: {provider_name} ({model_name})")

        try:
            config = ProcessingConfig(
                llm_provider=provider_name,
                llm_model=model_name
            )

            processor = DocumentProcessor(config)

            if not processor.llm_provider.is_available():
                print(f"Provider not available, skipping...")
                continue

            result = processor.process_document(file_path=document_path)

            if result.extracted_data:
                print(f"✓ Success with {provider_name}!")
                print(f"Extracted data: {result.extracted_data}")
                break

        except Exception as e:
            print(f"✗ Failed with {provider_name}: {e}")
            continue

    else:
        print("\n✗ All providers failed!")


def example9_custom_processing_pipeline():
    """Example 9: Custom processing pipeline"""
    print("\n" + "="*60)
    print("Example 9: Custom Processing Pipeline")
    print("="*60)

    from backend.app.loaders import DocumentLoaderFactory
    from backend.app.llm_providers import create_llm_provider

    # Step 1: Load document
    print("Step 1: Loading document...")
    factory = DocumentLoaderFactory()
    document = factory.load_document(file_path="sample.pdf")
    print(f"Loaded {document.page_count} pages")

    # Step 2: Create custom LLM provider
    print("\nStep 2: Initializing LLM provider...")
    llm = create_llm_provider(
        provider_name="ollama",
        model_name="llama2"
    )

    # Step 3: Define extraction schema
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Brief summary of the document"},
            "key_points": {"type": "array", "items": {"type": "string"}}
        }
    }

    # Step 4: Extract data
    print("\nStep 3: Extracting structured data...")
    result = llm.extract_structured_data(
        text=document.content,
        schema=schema
    )

    print(f"\nExtracted data: {result.extracted_data}")
    print(f"Confidence: {result.confidence_scores}")
    print(f"Processing time: {result.processing_time:.2f}s")


def main():
    """Run all examples"""
    examples = [
        # example1_basic_usage,
        example2_custom_llm_provider,
        # example3_document_loaders,
        # example4_custom_schema,
        example5_chunking_strategies,
        # example6_large_document_processing,
        # example7_multi_format_batch,
        example8_provider_fallback,
        # example9_custom_processing_pipeline
    ]

    print("\n")
    print("="*60)
    print("Modular Document Parser - Example Usage")
    print("="*60)

    for i, example_func in enumerate(examples, 1):
        try:
            example_func()
        except Exception as e:
            print(f"\nExample {i} failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
