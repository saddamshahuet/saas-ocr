"""HuggingFace self-hosted LLM provider"""
from typing import Dict, Any, Optional
import logging
import time
from .base import BaseLLMProvider, LLMConfig, ExtractionResult, LLMProviderType

logger = logging.getLogger(__name__)


class HuggingFaceProvider(BaseLLMProvider):
    """LLM provider using self-hosted HuggingFace models"""

    def __init__(self, config: LLMConfig):
        """
        Initialize HuggingFace provider

        Args:
            config: LLM configuration
        """
        super().__init__(config)
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._initialize_model()

    def _validate_config(self) -> None:
        """Validate configuration"""
        if self.config.provider_type != LLMProviderType.SELF_HOSTED_HUGGINGFACE:
            raise ValueError(
                f"Invalid provider type: {self.config.provider_type}. "
                f"Expected {LLMProviderType.SELF_HOSTED_HUGGINGFACE}"
            )

        if not self.config.model_name:
            raise ValueError("model_name is required for HuggingFace provider")

    def _initialize_model(self) -> None:
        """Initialize HuggingFace model and tokenizer"""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            import torch

            self.logger.info(f"Loading HuggingFace model: {self.config.model_name}")

            # Determine device
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.logger.info(f"Using device: {device}")

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                trust_remote_code=True
            )

            # Load model
            model_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
                "device_map": "auto" if device == "cuda" else None,
            }

            # Add custom parameters
            if self.config.custom_params:
                model_kwargs.update(self.config.custom_params.get('model_kwargs', {}))

            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                **model_kwargs
            )

            # Create pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if device == "cuda" else -1,
                max_new_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
            )

            self.logger.info("HuggingFace model loaded successfully")

        except ImportError:
            self.logger.error(
                "transformers or torch not available. "
                "Install with: pip install transformers torch accelerate"
            )
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize HuggingFace model: {e}")
            raise

    def is_available(self) -> bool:
        """Check if provider is available"""
        return self.pipeline is not None

    def generate_completion(self, prompt: str, **kwargs) -> str:
        """
        Generate text completion

        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        if not self.is_available():
            raise RuntimeError("HuggingFace model not initialized")

        try:
            # Merge kwargs with config
            gen_kwargs = {
                "max_new_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "do_sample": self.config.temperature > 0,
            }

            # Generate
            result = self.pipeline(
                prompt,
                **gen_kwargs,
                return_full_text=False
            )

            # Extract generated text
            if result and len(result) > 0:
                return result[0]['generated_text']
            else:
                return ""

        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            raise

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract structured data from text

        Args:
            text: Input text to extract from
            schema: JSON schema defining structure to extract
            prompt_template: Optional custom prompt template
            **kwargs: Additional arguments

        Returns:
            ExtractionResult object
        """
        start_time = time.time()

        try:
            # Build extraction prompt
            prompt = self.build_extraction_prompt(text, schema, prompt_template)

            # Generate completion with retry
            def generate():
                return self.generate_completion(prompt, **kwargs)

            raw_response = self.retry_with_backoff(generate)

            # Parse JSON response
            extracted_data = self.parse_json_response(raw_response)

            # Calculate confidence scores
            confidence_scores = self.calculate_confidence_scores(extracted_data)

            # Count tokens (approximate)
            tokens_used = len(self.tokenizer.encode(prompt + raw_response)) if self.tokenizer else None

            processing_time = time.time() - start_time

            return ExtractionResult(
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                raw_response=raw_response,
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                tokens_used=tokens_used,
                processing_time=processing_time,
                metadata={
                    "device": "cuda" if self.model.device.type == "cuda" else "cpu"
                }
            )

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            raise

    def unload_model(self) -> None:
        """Unload model from memory"""
        import gc
        import torch

        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        if self.pipeline:
            del self.pipeline

        self.model = None
        self.tokenizer = None
        self.pipeline = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self.logger.info("Model unloaded from memory")
