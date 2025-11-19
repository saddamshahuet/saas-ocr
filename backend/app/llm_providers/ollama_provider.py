"""Ollama self-hosted LLM provider"""
from typing import Dict, Any, Optional
import logging
import time
import requests
from .base import BaseLLMProvider, LLMConfig, ExtractionResult, LLMProviderType

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """LLM provider using locally hosted Ollama"""

    def __init__(self, config: LLMConfig):
        """
        Initialize Ollama provider

        Args:
            config: LLM configuration
        """
        super().__init__(config)
        self.base_url = config.api_base or "http://localhost:11434"
        self.session = requests.Session()

    def _validate_config(self) -> None:
        """Validate configuration"""
        if self.config.provider_type != LLMProviderType.SELF_HOSTED_OLLAMA:
            raise ValueError(
                f"Invalid provider type: {self.config.provider_type}. "
                f"Expected {LLMProviderType.SELF_HOSTED_OLLAMA}"
            )

        if not self.config.model_name:
            raise ValueError("model_name is required for Ollama provider")

    def is_available(self) -> bool:
        """Check if Ollama server is available"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Ollama server not available: {e}")
            return False

    def generate_completion(self, prompt: str, **kwargs) -> str:
        """
        Generate text completion using Ollama

        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        try:
            # Build request payload
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "top_p": kwargs.get("top_p", self.config.top_p),
                    "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                }
            }

            # Add custom parameters
            if self.config.custom_params:
                payload["options"].update(self.config.custom_params.get('options', {}))

            # Make request
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            return result.get("response", "")

        except requests.exceptions.Timeout:
            self.logger.error(f"Ollama request timed out after {self.config.timeout}s")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ollama request failed: {e}")
            raise
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

            processing_time = time.time() - start_time

            return ExtractionResult(
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                raw_response=raw_response,
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                tokens_used=None,  # Ollama doesn't always provide token count
                processing_time=processing_time,
                metadata={
                    "base_url": self.base_url
                }
            )

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            raise

    def generate_with_chat(
        self,
        messages: list[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Generate completion using chat API

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        try:
            payload = {
                "model": self.config.model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                    "top_p": kwargs.get("top_p", self.config.top_p),
                    "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
                }
            }

            response = self.session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            return result.get("message", {}).get("content", "")

        except Exception as e:
            self.logger.error(f"Chat generation failed: {e}")
            raise

    def list_models(self) -> list[str]:
        """
        List available models on Ollama server

        Returns:
            List of model names
        """
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            response.raise_for_status()

            models_data = response.json()
            return [model["name"] for model in models_data.get("models", [])]

        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")
            return []

    def pull_model(self, model_name: str) -> bool:
        """
        Pull a model to Ollama server

        Args:
            model_name: Name of model to pull

        Returns:
            True if successful
        """
        try:
            self.logger.info(f"Pulling model: {model_name}")

            payload = {"name": model_name}
            response = self.session.post(
                f"{self.base_url}/api/pull",
                json=payload,
                timeout=600  # 10 minutes for large models
            )

            response.raise_for_status()
            self.logger.info(f"Model {model_name} pulled successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to pull model: {e}")
            return False
