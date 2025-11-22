"""Unified document processing pipeline"""
from typing import Dict, Any, Optional, Union, List
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ProcessingStrategy(Enum):
    """Document processing strategies"""
    FULL_DOCUMENT = "full_document"  # Process entire document as one
    CHUNKED = "chunked"  # Process document in chunks and merge results
    PAGE_BY_PAGE = "page_by_page"  # Process each page separately
    HYBRID = "hybrid"  # Intelligent combination based on document size


@dataclass
class ProcessingConfig:
    """Configuration for document processing"""
    # Document loader config
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    enable_chunking: bool = True
    chunk_size: int = 4000
    chunk_overlap: int = 200
    chunking_strategy: str = "semantic"  # fixed_size, sentence_aware, semantic, sliding_window

    # OCR config
    use_ocr: bool = True
    ocr_language: str = "en"
    ocr_preprocess: bool = True
    ocr_dpi: int = 300

    # Language support
    auto_detect_language: bool = True  # Automatically detect document language
    supported_languages: List[str] = field(default_factory=lambda: ["en", "es", "fr", "de", "zh", "ja", "ar"])
    use_multilingual_prompts: bool = True  # Use language-specific LLM prompts

    # Layout understanding
    enable_layout_analysis: bool = True  # Enable document layout analysis
    extract_tables: bool = True  # Extract tables from documents
    use_layoutlm: bool = False  # Use LayoutLMv3 for advanced layout understanding
    detect_forms: bool = True  # Detect form fields
    classify_sections: bool = True  # Classify document sections

    # LLM provider config
    llm_provider: str = "ollama"  # huggingface, ollama, openai, gemini, etc.
    llm_model: str = "llama2"
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    llm_timeout: int = 120
    llm_max_retries: int = 3

    # Processing strategy
    processing_strategy: ProcessingStrategy = ProcessingStrategy.HYBRID
    max_chunks_to_process: Optional[int] = None  # Limit chunks for very large docs

    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_file_size": self.max_file_size,
            "enable_chunking": self.enable_chunking,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunking_strategy": self.chunking_strategy,
            "use_ocr": self.use_ocr,
            "ocr_language": self.ocr_language,
            "ocr_preprocess": self.ocr_preprocess,
            "ocr_dpi": self.ocr_dpi,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_temperature": self.llm_temperature,
            "llm_max_tokens": self.llm_max_tokens,
            "processing_strategy": self.processing_strategy.value,
            "custom_params": self.custom_params
        }


@dataclass
class ProcessingResult:
    """Result from document processing"""
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    metadata: Dict[str, Any]
    processing_time: float
    document_info: Dict[str, Any]
    chunks_processed: Optional[List[Dict]] = None
    errors: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "extracted_data": self.extracted_data,
            "confidence_scores": self.confidence_scores,
            "metadata": self.metadata,
            "processing_time": self.processing_time,
            "document_info": self.document_info,
            "chunks_processed": self.chunks_processed or [],
            "errors": self.errors or []
        }


class DocumentProcessor:
    """Unified document processing pipeline"""

    def __init__(self, config: Optional[ProcessingConfig] = None):
        """
        Initialize document processor

        Args:
            config: Processing configuration
        """
        self.config = config or ProcessingConfig()
        self.ocr_engine = None
        self.llm_provider = None
        self.document_loader_factory = None
        self.language_manager = None
        self.layout_analyzer = None

        self._initialize_components()

    def _initialize_components(self):
        """Initialize processing components"""
        # Initialize OCR engine
        if self.config.use_ocr:
            self._initialize_ocr()

        # Initialize document loader factory
        from ..loaders import DocumentLoaderFactory
        self.document_loader_factory = DocumentLoaderFactory(
            ocr_engine=self.ocr_engine
        )

        # Initialize LLM provider
        self._initialize_llm()

        # Initialize language manager
        if self.config.auto_detect_language:
            from ..services.language_service import get_language_manager
            self.language_manager = get_language_manager()
            logger.info("Language manager initialized")

        # Initialize layout analyzer
        if self.config.enable_layout_analysis:
            from ..services.layout_service import get_layout_analyzer
            self.layout_analyzer = get_layout_analyzer(
                use_layoutlm=self.config.use_layoutlm,
                extract_tables=self.config.extract_tables,
                detect_forms=self.config.detect_forms,
                classify_sections=self.config.classify_sections
            )
            logger.info("Layout analyzer initialized")

        logger.info("Document processor initialized successfully")

    def _initialize_ocr(self):
        """Initialize OCR engine"""
        try:
            from paddleocr import PaddleOCR

            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang=self.config.ocr_language,
                use_gpu=False,  # Can be made configurable
                show_log=False
            )

            logger.info(f"OCR engine initialized (language: {self.config.ocr_language})")

        except Exception as e:
            logger.warning(f"Failed to initialize OCR engine: {e}")
            self.ocr_engine = None

    def _initialize_llm(self):
        """Initialize LLM provider"""
        try:
            from ..llm_providers import LLMProviderFactory, LLMConfig, LLMProviderType

            # Map provider name to type
            provider_type_map = {
                'huggingface': LLMProviderType.SELF_HOSTED_HUGGINGFACE,
                'ollama': LLMProviderType.SELF_HOSTED_OLLAMA,
                'openai': LLMProviderType.OPENAI,
                'gemini': LLMProviderType.GEMINI,
                'deepseek': LLMProviderType.DEEPSEEK,
                'anthropic': LLMProviderType.ANTHROPIC,
                'cohere': LLMProviderType.COHERE,
                'mistral': LLMProviderType.MISTRAL,
                'groq': LLMProviderType.GROQ,
                'together': LLMProviderType.TOGETHER,
            }

            provider_type = provider_type_map.get(self.config.llm_provider.lower())
            if not provider_type:
                logger.warning(f"Unknown LLM provider: {self.config.llm_provider}")
                return

            llm_config = LLMConfig(
                provider_type=provider_type,
                model_name=self.config.llm_model,
                api_key=self.config.llm_api_key,
                api_base=self.config.llm_api_base,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
                timeout=self.config.llm_timeout,
                max_retries=self.config.llm_max_retries,
                custom_params=self.config.custom_params.get('llm', {})
            )

            self.llm_provider = LLMProviderFactory.create_provider(llm_config)

            logger.info(
                f"LLM provider initialized: {self.config.llm_provider} "
                f"(model: {self.config.llm_model})"
            )

        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            self.llm_provider = None

    def process_document(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        file_extension: Optional[str] = None,
        extraction_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ProcessingResult:
        """
        Process document end-to-end

        Args:
            file_path: Path to document file
            file_content: Binary content of document
            file_extension: File extension (required if file_content provided)
            extraction_schema: JSON schema for extraction
            **kwargs: Additional processing parameters

        Returns:
            ProcessingResult object
        """
        start_time = time.time()
        errors = []

        try:
            # Step 1: Load document
            logger.info("Loading document...")
            loaded_doc = self._load_document(
                file_path, file_content, file_extension
            )

            # Step 2: Analyze layout if enabled
            layout_result = None
            if self.config.enable_layout_analysis and self.layout_analyzer:
                logger.info("Analyzing document layout...")
                layout_result = self._analyze_layout(loaded_doc, file_path)

            # Step 3: Extract data using LLM
            logger.info("Extracting structured data...")
            extraction_result = self._extract_data(
                loaded_doc,
                extraction_schema
            )

            # Step 4: Build result
            processing_time = time.time() - start_time

            # Build metadata
            metadata = {
                "llm_provider": extraction_result.provider_type,
                "llm_model": extraction_result.model_used,
                "tokens_used": extraction_result.tokens_used,
                "llm_processing_time": extraction_result.processing_time
            }

            # Add layout information if available
            if layout_result:
                metadata["layout_analysis"] = {
                    "num_tables": len(layout_result.tables),
                    "num_elements": len(layout_result.elements),
                    "num_sections": len(layout_result.sections),
                    "columns_detected": layout_result.columns_detected,
                    "num_columns": layout_result.num_columns,
                    "page_layout": layout_result.page_layout,
                    "tables": [table.to_dict() for table in layout_result.tables],
                    "elements": [elem.to_dict() for elem in layout_result.elements[:10]],  # Limit to first 10
                    "sections": layout_result.sections
                }

            result = ProcessingResult(
                extracted_data=extraction_result.extracted_data,
                confidence_scores=extraction_result.confidence_scores,
                metadata=metadata,
                processing_time=processing_time,
                document_info=loaded_doc.to_dict(),
                chunks_processed=self._get_chunks_info(loaded_doc),
                errors=errors if errors else None
            )

            logger.info(f"Document processed successfully in {processing_time:.2f}s")

            return result

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            errors.append(str(e))

            return ProcessingResult(
                extracted_data={},
                confidence_scores={},
                metadata={"error": str(e)},
                processing_time=time.time() - start_time,
                document_info={},
                errors=errors
            )

    def _load_document(
        self,
        file_path: Optional[str],
        file_content: Optional[bytes],
        file_extension: Optional[str]
    ):
        """Load document using appropriate loader"""
        loader_config = {
            "max_file_size": self.config.max_file_size,
            "enable_chunking": self.config.enable_chunking,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
        }

        return self.document_loader_factory.load_document(
            file_path=file_path,
            file_content=file_content,
            file_extension=file_extension,
            loader_config=loader_config
        )

    def _analyze_layout(self, loaded_doc, file_path: Optional[str]):
        """
        Analyze document layout

        Args:
            loaded_doc: Loaded document object
            file_path: Optional file path

        Returns:
            LayoutAnalysisResult or None
        """
        if not self.layout_analyzer:
            return None

        try:
            # For PDF files, analyze layout
            if file_path and file_path.lower().endswith('.pdf'):
                layout_result = self.layout_analyzer.analyze_layout(
                    file_path=file_path,
                    page_number=1  # Analyze first page
                )
                return layout_result

            # For image files, convert loaded doc data if available
            elif loaded_doc.raw_data:
                try:
                    from PIL import Image
                    import io

                    image = Image.open(io.BytesIO(loaded_doc.raw_data))
                    layout_result = self.layout_analyzer.analyze_layout(
                        image=image,
                        page_number=1
                    )
                    return layout_result
                except Exception as e:
                    logger.warning(f"Could not analyze layout from image: {e}")
                    return None

            return None

        except Exception as e:
            logger.error(f"Layout analysis failed: {e}")
            return None

    def _extract_data(self, loaded_doc, extraction_schema):
        """Extract structured data from loaded document"""
        if not self.llm_provider:
            raise RuntimeError("LLM provider not initialized")

        if not self.llm_provider.is_available():
            raise RuntimeError("LLM provider not available")

        # Default medical schema if none provided
        if not extraction_schema:
            extraction_schema = self._get_default_medical_schema()

        # Choose processing strategy
        if self.config.processing_strategy == ProcessingStrategy.FULL_DOCUMENT:
            return self._extract_from_full_document(loaded_doc, extraction_schema)

        elif self.config.processing_strategy == ProcessingStrategy.CHUNKED:
            return self._extract_from_chunks(loaded_doc, extraction_schema)

        elif self.config.processing_strategy == ProcessingStrategy.HYBRID:
            # Use full document if small enough, otherwise chunks
            if len(loaded_doc.content) <= self.config.chunk_size:
                return self._extract_from_full_document(loaded_doc, extraction_schema)
            else:
                return self._extract_from_chunks(loaded_doc, extraction_schema)

        else:
            return self._extract_from_full_document(loaded_doc, extraction_schema)

    def _extract_from_full_document(self, loaded_doc, extraction_schema):
        """Extract from full document content"""
        # Detect language and build prompt if multilingual support is enabled
        detected_language = 'en'
        prompt_template = None

        if self.config.auto_detect_language and self.language_manager and self.config.use_multilingual_prompts:
            lang_info = self.language_manager.auto_detect_and_configure(loaded_doc.content)
            detected_language = lang_info['detected_language']

            # Build multilingual prompt
            prompt_template = self.language_manager.get_multilingual_prompt(
                text=loaded_doc.content,
                schema=extraction_schema,
                detected_language=detected_language
            )

            logger.info(f"Detected language: {lang_info['language_name']} ({detected_language}) "
                       f"with confidence {lang_info['confidence']:.2%}")

        return self.llm_provider.extract_structured_data(
            text=loaded_doc.content,
            schema=extraction_schema,
            prompt_template=prompt_template
        )

    def _extract_from_chunks(self, loaded_doc, extraction_schema):
        """Extract from document chunks and merge results"""
        if not loaded_doc.chunks:
            # No chunks, process full document
            return self._extract_from_full_document(loaded_doc, extraction_schema)

        # Detect language once from full content if enabled
        detected_language = 'en'
        if self.config.auto_detect_language and self.language_manager:
            lang_info = self.language_manager.auto_detect_and_configure(loaded_doc.content)
            detected_language = lang_info['detected_language']
            logger.info(f"Detected language for chunks: {lang_info['language_name']} ({detected_language})")

        # Limit chunks if configured
        chunks_to_process = loaded_doc.chunks
        if self.config.max_chunks_to_process:
            chunks_to_process = chunks_to_process[:self.config.max_chunks_to_process]

        # Extract from each chunk
        chunk_results = []
        for chunk in chunks_to_process:
            try:
                # Build multilingual prompt for this chunk if enabled
                prompt_template = None
                if self.config.use_multilingual_prompts and self.language_manager:
                    prompt_template = self.language_manager.get_multilingual_prompt(
                        text=chunk.content,
                        schema=extraction_schema,
                        detected_language=detected_language
                    )

                result = self.llm_provider.extract_structured_data(
                    text=chunk.content,
                    schema=extraction_schema,
                    prompt_template=prompt_template
                )
                chunk_results.append(result)
            except Exception as e:
                logger.warning(f"Failed to extract from chunk {chunk.chunk_index}: {e}")

        # Merge results from all chunks
        return self._merge_chunk_results(chunk_results)

    def _merge_chunk_results(self, chunk_results):
        """Merge extraction results from multiple chunks"""
        if not chunk_results:
            raise ValueError("No chunk results to merge")

        if len(chunk_results) == 1:
            return chunk_results[0]

        # Simple merging strategy: take the most confident value for each field
        merged_data = {}
        merged_confidence = {}

        for result in chunk_results:
            for field, value in result.extracted_data.items():
                confidence = result.confidence_scores.get(field, 0.0)

                # If field not in merged or this has higher confidence, use it
                if field not in merged_data or confidence > merged_confidence.get(field, 0.0):
                    merged_data[field] = value
                    merged_confidence[field] = confidence

        # Create merged result
        from ..llm_providers import ExtractionResult

        return ExtractionResult(
            extracted_data=merged_data,
            confidence_scores=merged_confidence,
            raw_response="[Merged from multiple chunks]",
            model_used=chunk_results[0].model_used,
            provider_type=chunk_results[0].provider_type,
            metadata={"chunks_merged": len(chunk_results)}
        )

    def _get_chunks_info(self, loaded_doc):
        """Get information about processed chunks"""
        if not loaded_doc.chunks:
            return None

        return [
            {
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "length": len(chunk.content),
                "confidence": chunk.confidence
            }
            for chunk in loaded_doc.chunks
        ]

    def _get_default_medical_schema(self) -> Dict[str, Any]:
        """Get default medical extraction schema"""
        return {
            "type": "object",
            "properties": {
                "patient_name": {
                    "type": "string",
                    "description": "Full name of the patient"
                },
                "date_of_birth": {
                    "type": "string",
                    "description": "Patient's date of birth"
                },
                "medical_record_number": {
                    "type": "string",
                    "description": "Medical record number or patient ID"
                },
                "primary_diagnosis": {
                    "type": "string",
                    "description": "Primary diagnosis or condition"
                },
                "allergies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of known allergies"
                },
                "medications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "dosage": {"type": "string"},
                            "frequency": {"type": "string"}
                        }
                    },
                    "description": "Current medications"
                },
                "physician_name": {
                    "type": "string",
                    "description": "Name of attending physician"
                }
            },
            "required": ["patient_name"]
        }

    def update_config(self, **kwargs):
        """Update configuration dynamically"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated config: {key} = {value}")

        # Reinitialize if critical parameters changed
        critical_params = ['llm_provider', 'llm_model', 'use_ocr', 'ocr_language']
        if any(key in critical_params for key in kwargs.keys()):
            logger.info("Reinitializing components due to config change")
            self._initialize_components()
