"""Cloud-based LLM providers (Gemini, DeepSeek, Anthropic, Cohere, Mistral, Groq, Together)"""
from typing import Dict, Any, Optional
import logging
import time
import requests
from .base import BaseLLMProvider, LLMConfig, ExtractionResult, LLMProviderType

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API provider"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _validate_config(self) -> None:
        if not self.config.api_key:
            raise ValueError("api_key is required for Gemini provider")
        if not self.config.model_name:
            self.config.model_name = "gemini-pro"

    def _initialize_client(self) -> None:
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.config.api_key)
            self.client = genai.GenerativeModel(self.config.model_name)
            self.logger.info(f"Gemini client initialized with model: {self.config.model_name}")

        except ImportError:
            self.logger.error("google-generativeai not available. Install with: pip install google-generativeai")
            raise

    def is_available(self) -> bool:
        return self.client is not None

    def generate_completion(self, prompt: str, **kwargs) -> str:
        if not self.client:
            raise RuntimeError("Gemini client not initialized")

        try:
            generation_config = {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }

            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )

            return response.text

        except Exception as e:
            self.logger.error(f"Gemini generation failed: {e}")
            raise

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        start_time = time.time()

        try:
            prompt = self.build_extraction_prompt(text, schema, prompt_template)

            def generate():
                return self.generate_completion(prompt, **kwargs)

            raw_response = self.retry_with_backoff(generate)
            extracted_data = self.parse_json_response(raw_response)
            confidence_scores = self.calculate_confidence_scores(extracted_data)

            return ExtractionResult(
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                raw_response=raw_response,
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Gemini extraction failed: {e}")
            raise


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API provider"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_url = config.api_base or "https://api.deepseek.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        })

    def _validate_config(self) -> None:
        if not self.config.api_key:
            raise ValueError("api_key is required for DeepSeek provider")
        if not self.config.model_name:
            self.config.model_name = "deepseek-chat"

    def is_available(self) -> bool:
        try:
            response = self.session.get(f"{self.api_url}/models", timeout=10)
            return response.status_code == 200
        except:
            return False

    def generate_completion(self, prompt: str, **kwargs) -> str:
        try:
            payload = {
                "model": self.config.model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant for data extraction."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }

            response = self.session.post(
                f"{self.api_url}/chat/completions",
                json=payload,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            return result["choices"][0]["message"]["content"]

        except Exception as e:
            self.logger.error(f"DeepSeek generation failed: {e}")
            raise

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        start_time = time.time()

        try:
            prompt = self.build_extraction_prompt(text, schema, prompt_template)

            def generate():
                return self.generate_completion(prompt, **kwargs)

            raw_response = self.retry_with_backoff(generate)
            extracted_data = self.parse_json_response(raw_response)
            confidence_scores = self.calculate_confidence_scores(extracted_data)

            return ExtractionResult(
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                raw_response=raw_response,
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"DeepSeek extraction failed: {e}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API provider"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _validate_config(self) -> None:
        if not self.config.api_key:
            raise ValueError("api_key is required for Anthropic provider")
        if not self.config.model_name:
            self.config.model_name = "claude-3-sonnet-20240229"

    def _initialize_client(self) -> None:
        try:
            from anthropic import Anthropic

            self.client = Anthropic(api_key=self.config.api_key)
            self.logger.info(f"Anthropic client initialized with model: {self.config.model_name}")

        except ImportError:
            self.logger.error("anthropic not available. Install with: pip install anthropic")
            raise

    def is_available(self) -> bool:
        return self.client is not None

    def generate_completion(self, prompt: str, **kwargs) -> str:
        if not self.client:
            raise RuntimeError("Anthropic client not initialized")

        try:
            message = self.client.messages.create(
                model=self.config.model_name,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            self.logger.error(f"Anthropic generation failed: {e}")
            raise

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        start_time = time.time()

        try:
            prompt = self.build_extraction_prompt(text, schema, prompt_template)

            def generate():
                return self.generate_completion(prompt, **kwargs)

            raw_response = self.retry_with_backoff(generate)
            extracted_data = self.parse_json_response(raw_response)
            confidence_scores = self.calculate_confidence_scores(extracted_data)

            return ExtractionResult(
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                raw_response=raw_response,
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Anthropic extraction failed: {e}")
            raise


class CohereProvider(BaseLLMProvider):
    """Cohere API provider"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
        self._initialize_client()

    def _validate_config(self) -> None:
        if not self.config.api_key:
            raise ValueError("api_key is required for Cohere provider")
        if not self.config.model_name:
            self.config.model_name = "command"

    def _initialize_client(self) -> None:
        try:
            import cohere

            self.client = cohere.Client(api_key=self.config.api_key)
            self.logger.info(f"Cohere client initialized with model: {self.config.model_name}")

        except ImportError:
            self.logger.error("cohere not available. Install with: pip install cohere")
            raise

    def is_available(self) -> bool:
        return self.client is not None

    def generate_completion(self, prompt: str, **kwargs) -> str:
        if not self.client:
            raise RuntimeError("Cohere client not initialized")

        try:
            response = self.client.generate(
                model=self.config.model_name,
                prompt=prompt,
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                temperature=kwargs.get("temperature", self.config.temperature),
                p=kwargs.get("top_p", self.config.top_p),
            )

            return response.generations[0].text

        except Exception as e:
            self.logger.error(f"Cohere generation failed: {e}")
            raise

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        start_time = time.time()

        try:
            prompt = self.build_extraction_prompt(text, schema, prompt_template)

            def generate():
                return self.generate_completion(prompt, **kwargs)

            raw_response = self.retry_with_backoff(generate)
            extracted_data = self.parse_json_response(raw_response)
            confidence_scores = self.calculate_confidence_scores(extracted_data)

            return ExtractionResult(
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                raw_response=raw_response,
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Cohere extraction failed: {e}")
            raise


class MistralProvider(BaseLLMProvider):
    """Mistral AI API provider"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_url = config.api_base or "https://api.mistral.ai/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        })

    def _validate_config(self) -> None:
        if not self.config.api_key:
            raise ValueError("api_key is required for Mistral provider")
        if not self.config.model_name:
            self.config.model_name = "mistral-medium"

    def is_available(self) -> bool:
        try:
            response = self.session.get(f"{self.api_url}/models", timeout=10)
            return response.status_code == 200
        except:
            return False

    def generate_completion(self, prompt: str, **kwargs) -> str:
        try:
            payload = {
                "model": self.config.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }

            response = self.session.post(
                f"{self.api_url}/chat/completions",
                json=payload,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            return result["choices"][0]["message"]["content"]

        except Exception as e:
            self.logger.error(f"Mistral generation failed: {e}")
            raise

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        start_time = time.time()

        try:
            prompt = self.build_extraction_prompt(text, schema, prompt_template)

            def generate():
                return self.generate_completion(prompt, **kwargs)

            raw_response = self.retry_with_backoff(generate)
            extracted_data = self.parse_json_response(raw_response)
            confidence_scores = self.calculate_confidence_scores(extracted_data)

            return ExtractionResult(
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                raw_response=raw_response,
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Mistral extraction failed: {e}")
            raise


class GroqProvider(BaseLLMProvider):
    """Groq API provider"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_url = config.api_base or "https://api.groq.com/openai/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        })

    def _validate_config(self) -> None:
        if not self.config.api_key:
            raise ValueError("api_key is required for Groq provider")
        if not self.config.model_name:
            self.config.model_name = "mixtral-8x7b-32768"

    def is_available(self) -> bool:
        try:
            response = self.session.get(f"{self.api_url}/models", timeout=10)
            return response.status_code == 200
        except:
            return False

    def generate_completion(self, prompt: str, **kwargs) -> str:
        try:
            payload = {
                "model": self.config.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }

            response = self.session.post(
                f"{self.api_url}/chat/completions",
                json=payload,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            return result["choices"][0]["message"]["content"]

        except Exception as e:
            self.logger.error(f"Groq generation failed: {e}")
            raise

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        start_time = time.time()

        try:
            prompt = self.build_extraction_prompt(text, schema, prompt_template)

            def generate():
                return self.generate_completion(prompt, **kwargs)

            raw_response = self.retry_with_backoff(generate)
            extracted_data = self.parse_json_response(raw_response)
            confidence_scores = self.calculate_confidence_scores(extracted_data)

            return ExtractionResult(
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                raw_response=raw_response,
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Groq extraction failed: {e}")
            raise


class TogetherProvider(BaseLLMProvider):
    """Together AI API provider"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_url = config.api_base or "https://api.together.xyz/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        })

    def _validate_config(self) -> None:
        if not self.config.api_key:
            raise ValueError("api_key is required for Together provider")
        if not self.config.model_name:
            self.config.model_name = "mistralai/Mixtral-8x7B-Instruct-v0.1"

    def is_available(self) -> bool:
        try:
            response = self.session.get(f"{self.api_url}/models", timeout=10)
            return response.status_code == 200
        except:
            return False

    def generate_completion(self, prompt: str, **kwargs) -> str:
        try:
            payload = {
                "model": self.config.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }

            response = self.session.post(
                f"{self.api_url}/chat/completions",
                json=payload,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            result = response.json()

            return result["choices"][0]["message"]["content"]

        except Exception as e:
            self.logger.error(f"Together generation failed: {e}")
            raise

    def extract_structured_data(
        self,
        text: str,
        schema: Dict[str, Any],
        prompt_template: Optional[str] = None,
        **kwargs
    ) -> ExtractionResult:
        start_time = time.time()

        try:
            prompt = self.build_extraction_prompt(text, schema, prompt_template)

            def generate():
                return self.generate_completion(prompt, **kwargs)

            raw_response = self.retry_with_backoff(generate)
            extracted_data = self.parse_json_response(raw_response)
            confidence_scores = self.calculate_confidence_scores(extracted_data)

            return ExtractionResult(
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                raw_response=raw_response,
                model_used=self.config.model_name,
                provider_type=self.config.provider_type.value,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            self.logger.error(f"Together extraction failed: {e}")
            raise
