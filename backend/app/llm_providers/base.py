"""Base LLM provider interface"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LLMProviderType(Enum):
    """Types of LLM providers"""
    SELF_HOSTED_HUGGINGFACE = "huggingface"
    SELF_HOSTED_OLLAMA = "ollama"
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    MISTRAL = "mistral"
    GROQ = "groq"
    TOGETHER = "together"
    REPLICATE = "replicate"


@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    provider_type: LLMProviderType
    model_name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    timeout: int = 120
    max_retries: int = 3
    enable_streaming: bool = False
    custom_params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "provider_type": self.provider_type.value,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "enable_streaming": self.enable_streaming,
            "custom_params": self.custom_params or {}
        }


@dataclass
class ExtractionResult:
    """Result from LLM extraction"""
    extracted_data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    raw_response: str
    model_used: str
    provider_type: str
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "extracted_data": self.extracted_data,
            "confidence_scores": self.confidence_scores,
            "raw_response": self.raw_response,
            "model_used": self.model_used,
            "provider_type": self.provider_type,
            "tokens_used": self.tokens_used,
            "processing_time": self.processing_time,
            "metadata": self.metadata or {}
        }


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM provider

        Args:
            config: LLM configuration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider-specific configuration"""
        pass

    @abstractmethod
    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        """
        Extract structured data from text using LLM

        Args:
            text: Input text to extract from
            schema: JSON schema defining the structure to extract
            prompt_template: Optional custom prompt template
            **kwargs: Additional provider-specific arguments

        Returns:
            ExtractionResult object
        """
        pass

    @abstractmethod
    def generate_completion(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        Generate text completion

        Args:
            prompt: Input prompt
            **kwargs: Additional provider-specific arguments

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available and configured correctly"""
        pass

    def build_extraction_prompt(
        self,
        text: str,
        schema: Dict[str, Any],
        custom_template: Optional[str] = None
    ) -> str:
        """
        Build extraction prompt from text and schema

        Args:
            text: Input text
            schema: Extraction schema
            custom_template: Optional custom template

        Returns:
            Formatted prompt
        """
        if custom_template:
            return custom_template.format(text=text, schema=schema)

        # Default template
        schema_description = self._format_schema_description(schema)

        prompt = f"""You are a medical document data extraction expert. Extract structured information from the following document text.

Document Text:
{text}

Required Fields to Extract:
{schema_description}

Instructions:
1. Extract only the information present in the document
2. Return results in JSON format matching the schema
3. Use null for missing fields
4. Provide confidence scores (0-1) for each field
5. For medical terminology, use standard abbreviations

Return your response as a valid JSON object."""

        return prompt

    def _format_schema_description(self, schema: Dict[str, Any]) -> str:
        """Format schema into human-readable description"""
        lines = []
        for field_name, field_info in schema.get("properties", {}).items():
            field_type = field_info.get("type", "string")
            description = field_info.get("description", "")
            required = field_name in schema.get("required", [])
            req_marker = " (required)" if required else " (optional)"
            lines.append(f"- {field_name} ({field_type}){req_marker}: {description}")

        return "\n".join(lines)

    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON object
        """
        import json
        import re

        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
        else:
            # Try to find JSON object in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.debug(f"Response: {response}")
            return {}

    def calculate_confidence_scores(
        self,
        extracted_data: Dict[str, Any],
        default_confidence: float = 0.85
    ) -> Dict[str, float]:
        """
        Calculate confidence scores for extracted fields

        Args:
            extracted_data: Extracted data dictionary
            default_confidence: Default confidence for fields without explicit scores

        Returns:
            Dictionary of field confidence scores
        """
        scores = {}

        def extract_scores(data: Dict, prefix: str = ""):
            for key, value in data.items():
                field_path = f"{prefix}.{key}" if prefix else key

                if isinstance(value, dict):
                    # Check if it's a confidence dict
                    if "value" in value and "confidence" in value:
                        scores[field_path] = float(value.get("confidence", default_confidence))
                        extract_scores({"value": value["value"]}, field_path)
                    else:
                        extract_scores(value, field_path)
                elif value is not None and value != "":
                    scores[field_path] = default_confidence
                else:
                    scores[field_path] = 0.0

        extract_scores(extracted_data)
        return scores

    def retry_with_backoff(
        self,
        func,
        max_retries: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Retry function with exponential backoff

        Args:
            func: Function to retry
            max_retries: Maximum number of retries (uses config if not provided)
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        import time

        max_retries = max_retries or self.config.max_retries
        last_exception = None

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, ...
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {max_retries} attempts failed")

        raise last_exception
