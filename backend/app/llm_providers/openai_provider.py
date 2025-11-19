"""OpenAI cloud LLM provider"""
from typing import Dict, Any, Optional
import logging
import time
from .base import BaseLLMProvider, LLMConfig, ExtractionResult, LLMProviderType

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """LLM provider using OpenAI API"""

    def __init__(self, config: LLMConfig):
        """
        Initialize OpenAI provider

        Args:
            config: LLM configuration
        """
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _validate_config(self) -> None:
        """Validate configuration"""
        if self.config.provider_type != LLMProviderType.OPENAI:
            raise ValueError(
                f"Invalid provider type: {self.config.provider_type}. "
                f"Expected {LLMProviderType.OPENAI}"
            )

        if not self.config.api_key:
            raise ValueError("api_key is required for OpenAI provider")

        if not self.config.model_name:
            self.config.model_name = "gpt-4-turbo-preview"  # Default model

    def _initialize_client(self) -> None:
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI

            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )

            self.logger.info(f"OpenAI client initialized with model: {self.config.model_name}")

        except ImportError:
            self.logger.error("openai package not available. Install with: pip install openai")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

    def is_available(self) -> bool:
        """Check if provider is available"""
        try:
            # Try to list models as a health check
            if self.client:
                self.client.models.list()
                return True
        except Exception as e:
            self.logger.warning(f"OpenAI API not available: {e}")

        return False

    def generate_completion(self, prompt: str, **kwargs) -> str:
        """
        Generate text completion

        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")

        try:
            response = self.client.chat.completions.create(
                model=kwargs.get("model", self.config.model_name),
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts structured data from documents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                top_p=kwargs.get("top_p", self.config.top_p),
                frequency_penalty=kwargs.get("frequency_penalty", self.config.frequency_penalty),
                presence_penalty=kwargs.get("presence_penalty", self.config.presence_penalty),
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"OpenAI generation failed: {e}")
            raise

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract structured data from text using OpenAI

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

            # Use function calling for structured output if schema provided
            use_functions = kwargs.get("use_functions", True)

            if use_functions and self._supports_function_calling():
                result = self._extract_with_functions(prompt, schema, **kwargs)
            else:
                # Generate completion with retry
                def generate():
                    return self.generate_completion(prompt, **kwargs)

                raw_response = self.retry_with_backoff(generate)

                # Parse JSON response
                extracted_data = self.parse_json_response(raw_response)

                result = {
                    "extracted_data": extracted_data,
                    "raw_response": raw_response,
                    "tokens_used": None
                }

            # Calculate confidence scores
            confidence_scores = self.calculate_confidence_scores(result["extracted_data"])

            processing_time = time.time() - start_time

            return ExtractionResult(
                extracted_data=result["extracted_data"],
                confidence_scores=confidence_scores,
                raw_response=result["raw_response"],
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                tokens_used=result.get("tokens_used"),
                processing_time=processing_time
            )

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            raise

    def _supports_function_calling(self) -> bool:
        """Check if model supports function calling"""
        function_calling_models = [
            "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
        ]
        return any(model in self.config.model_name for model in function_calling_models)

    def _extract_with_functions(
        self,
        prompt: str,
        schema: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract using OpenAI function calling

        Args:
            prompt: Extraction prompt
            schema: JSON schema
            **kwargs: Additional parameters

        Returns:
            Dictionary with extracted data and metadata
        """
        try:
            # Convert schema to function definition
            function_def = {
                "name": "extract_data",
                "description": "Extract structured data from the document",
                "parameters": schema
            }

            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You are a medical document data extraction expert."},
                    {"role": "user", "content": prompt}
                ],
                functions=[function_def],
                function_call={"name": "extract_data"},
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            # Extract function call result
            message = response.choices[0].message

            if message.function_call:
                import json
                extracted_data = json.loads(message.function_call.arguments)
            else:
                extracted_data = {}

            return {
                "extracted_data": extracted_data,
                "raw_response": message.content or str(message.function_call),
                "tokens_used": response.usage.total_tokens if response.usage else None
            }

        except Exception as e:
            self.logger.error(f"Function calling extraction failed: {e}")
            raise
