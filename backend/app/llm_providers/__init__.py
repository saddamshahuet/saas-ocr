"""LLM Providers module - Factory and utilities"""
from typing import Optional, Dict, Any
import logging
from .base import (
    BaseLLMProvider,
    LLMConfig,
    LLMProviderType,
    ExtractionResult
)
from .huggingface_provider import HuggingFaceProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .cloud_providers import (
    GeminiProvider,
    DeepSeekProvider,
    AnthropicProvider,
    CohereProvider,
    MistralProvider,
    GroqProvider,
    TogetherProvider
)

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating LLM providers"""

    @staticmethod
    def create_provider(config: LLMConfig) -> BaseLLMProvider:
        """
        Create LLM provider based on configuration

        Args:
            config: LLM configuration

        Returns:
            LLM provider instance

        Raises:
            ValueError: If provider type is not supported
        """
        provider_map = {
            LLMProviderType.SELF_HOSTED_HUGGINGFACE: HuggingFaceProvider,
            LLMProviderType.SELF_HOSTED_OLLAMA: OllamaProvider,
            LLMProviderType.OPENAI: OpenAIProvider,
            LLMProviderType.GEMINI: GeminiProvider,
            LLMProviderType.DEEPSEEK: DeepSeekProvider,
            LLMProviderType.ANTHROPIC: AnthropicProvider,
            LLMProviderType.COHERE: CohereProvider,
            LLMProviderType.MISTRAL: MistralProvider,
            LLMProviderType.GROQ: GroqProvider,
            LLMProviderType.TOGETHER: TogetherProvider,
        }

        provider_class = provider_map.get(config.provider_type)

        if not provider_class:
            raise ValueError(f"Unsupported provider type: {config.provider_type}")

        logger.info(f"Creating {config.provider_type.value} provider with model: {config.model_name}")

        return provider_class(config)

    @staticmethod
    def from_env(
        provider_name: str,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        Create provider from environment or parameters

        Args:
            provider_name: Name of provider (openai, gemini, ollama, etc.)
            model_name: Model name (optional, uses default if not provided)
            api_key: API key (optional, reads from env if not provided)
            **kwargs: Additional configuration parameters

        Returns:
            LLM provider instance
        """
        import os

        # Map provider name to type
        provider_type_map = {
            'huggingface': LLMProviderType.SELF_HOSTED_HUGGINGFACE,
            'ollama': LLMProviderType.SELF_HOSTED_OLLAMA,
            'openai': LLMProviderType.OPENAI,
            'gemini': LLMProviderType.GEMINI,
            'deepseek': LLMProviderType.DEEPSEEK,
            'anthropic': LLMProviderType.ANTHROPIC,
            'claude': LLMProviderType.ANTHROPIC,
            'cohere': LLMProviderType.COHERE,
            'mistral': LLMProviderType.MISTRAL,
            'groq': LLMProviderType.GROQ,
            'together': LLMProviderType.TOGETHER,
        }

        provider_type = provider_type_map.get(provider_name.lower())
        if not provider_type:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Get API key from environment if not provided
        if not api_key and provider_type not in [
            LLMProviderType.SELF_HOSTED_OLLAMA,
            LLMProviderType.SELF_HOSTED_HUGGINGFACE
        ]:
            env_key_map = {
                LLMProviderType.OPENAI: 'OPENAI_API_KEY',
                LLMProviderType.GEMINI: 'GEMINI_API_KEY',
                LLMProviderType.DEEPSEEK: 'DEEPSEEK_API_KEY',
                LLMProviderType.ANTHROPIC: 'ANTHROPIC_API_KEY',
                LLMProviderType.COHERE: 'COHERE_API_KEY',
                LLMProviderType.MISTRAL: 'MISTRAL_API_KEY',
                LLMProviderType.GROQ: 'GROQ_API_KEY',
                LLMProviderType.TOGETHER: 'TOGETHER_API_KEY',
            }

            env_key = env_key_map.get(provider_type)
            if env_key:
                api_key = os.getenv(env_key)

        # Create config
        config = LLMConfig(
            provider_type=provider_type,
            model_name=model_name or kwargs.pop('model', ''),
            api_key=api_key,
            **kwargs
        )

        return LLMProviderFactory.create_provider(config)

    @staticmethod
    def get_supported_providers() -> Dict[str, Dict[str, Any]]:
        """
        Get information about all supported providers

        Returns:
            Dictionary with provider information
        """
        return {
            'self_hosted': {
                'huggingface': {
                    'name': 'HuggingFace',
                    'description': 'Self-hosted models from HuggingFace Hub',
                    'requires_api_key': False,
                    'requires_gpu': True,
                    'example_models': ['meta-llama/Llama-2-7b-chat-hf', 'mistralai/Mistral-7B-Instruct-v0.1']
                },
                'ollama': {
                    'name': 'Ollama',
                    'description': 'Locally hosted Ollama models',
                    'requires_api_key': False,
                    'requires_gpu': False,
                    'example_models': ['llama2', 'mistral', 'codellama', 'mixtral']
                }
            },
            'cloud': {
                'openai': {
                    'name': 'OpenAI',
                    'description': 'OpenAI GPT models',
                    'requires_api_key': True,
                    'example_models': ['gpt-4-turbo-preview', 'gpt-3.5-turbo']
                },
                'gemini': {
                    'name': 'Google Gemini',
                    'description': 'Google Gemini models',
                    'requires_api_key': True,
                    'example_models': ['gemini-pro', 'gemini-pro-vision']
                },
                'deepseek': {
                    'name': 'DeepSeek',
                    'description': 'DeepSeek AI models',
                    'requires_api_key': True,
                    'example_models': ['deepseek-chat', 'deepseek-coder']
                },
                'anthropic': {
                    'name': 'Anthropic Claude',
                    'description': 'Anthropic Claude models',
                    'requires_api_key': True,
                    'example_models': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229']
                },
                'cohere': {
                    'name': 'Cohere',
                    'description': 'Cohere language models',
                    'requires_api_key': True,
                    'example_models': ['command', 'command-light']
                },
                'mistral': {
                    'name': 'Mistral AI',
                    'description': 'Mistral AI models',
                    'requires_api_key': True,
                    'example_models': ['mistral-medium', 'mistral-small']
                },
                'groq': {
                    'name': 'Groq',
                    'description': 'Groq fast inference',
                    'requires_api_key': True,
                    'example_models': ['mixtral-8x7b-32768', 'llama2-70b-4096']
                },
                'together': {
                    'name': 'Together AI',
                    'description': 'Together AI models',
                    'requires_api_key': True,
                    'example_models': ['mistralai/Mixtral-8x7B-Instruct-v0.1']
                }
            }
        }


# Convenience function
def create_llm_provider(
    provider_name: str,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> BaseLLMProvider:
    """
    Convenience function to create LLM provider

    Args:
        provider_name: Name of provider
        model_name: Model name
        api_key: API key
        **kwargs: Additional parameters

    Returns:
        LLM provider instance
    """
    return LLMProviderFactory.from_env(
        provider_name=provider_name,
        model_name=model_name,
        api_key=api_key,
        **kwargs
    )


# Export main classes
__all__ = [
    'BaseLLMProvider',
    'LLMConfig',
    'LLMProviderType',
    'ExtractionResult',
    'LLMProviderFactory',
    'create_llm_provider',
    'HuggingFaceProvider',
    'OllamaProvider',
    'OpenAIProvider',
    'GeminiProvider',
    'DeepSeekProvider',
    'AnthropicProvider',
    'CohereProvider',
    'MistralProvider',
    'GroqProvider',
    'TogetherProvider',
]
