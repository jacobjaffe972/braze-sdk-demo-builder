"""LLM Factory for model-agnostic LLM instantiation.

This module provides a centralized factory for creating LLM instances
across OpenAI, Anthropic, and Google providers using LangChain abstractions.
"""

import logging
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel

from braze_code_gen.core.models import LLMConfig, ModelProvider, ModelTier

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM instances with provider abstraction."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM factory.

        Args:
            config: LLM configuration. If None, loads from environment.

        Raises:
            ValueError: If API key is missing for the selected provider.
        """
        self.config = config or self._load_from_env()

        # Validate configuration
        if not self.config.validate_api_key():
            raise ValueError(
                f"Missing API key for provider: {self.config.provider.value}. "
                f"Please set {self.config.provider.value.upper()}_API_KEY environment variable."
            )

        logger.info(f"LLM Factory initialized with provider: {self.config.provider.value}")

    @staticmethod
    def _load_from_env() -> LLMConfig:
        """Load LLM configuration from environment variables.

        Returns:
            LLMConfig: Configuration loaded from environment variables.
        """
        # Get provider from env (default to openai for backward compatibility)
        provider_str = os.getenv("MODEL_PROVIDER", "openai").lower()

        # Map string to enum
        try:
            provider = ModelProvider(provider_str)
        except ValueError:
            logger.warning(
                f"Invalid MODEL_PROVIDER '{provider_str}', defaulting to OpenAI. "
                f"Valid options: {', '.join([p.value for p in ModelProvider])}"
            )
            provider = ModelProvider.OPENAI

        # Load API keys
        config = LLMConfig(
            provider=provider,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

        return config

    def create_llm(
        self,
        tier: ModelTier,
        temperature: float,
        **kwargs
    ) -> BaseChatModel:
        """Create LLM instance for given tier and temperature.

        Args:
            tier: Model tier (primary/research/validation)
            temperature: Temperature for generation (0.0-1.0)
            **kwargs: Additional provider-specific arguments

        Returns:
            BaseChatModel: LangChain chat model instance

        Raises:
            ValueError: If provider is not supported
        """
        model_name = self.config.get_model_name(tier)
        provider = self.config.provider

        logger.debug(
            f"Creating {provider.value} LLM: {model_name} "
            f"(tier={tier.value}, temperature={temperature})"
        )

        if provider == ModelProvider.OPENAI:
            return self._create_openai_llm(model_name, temperature, **kwargs)
        elif provider == ModelProvider.ANTHROPIC:
            return self._create_anthropic_llm(model_name, temperature, **kwargs)
        elif provider == ModelProvider.GOOGLE:
            return self._create_google_llm(model_name, temperature, **kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _create_openai_llm(
        self,
        model: str,
        temperature: float,
        **kwargs
    ) -> ChatOpenAI:
        """Create OpenAI LLM instance.

        Args:
            model: OpenAI model name
            temperature: Temperature for generation
            **kwargs: Additional OpenAI-specific arguments

        Returns:
            ChatOpenAI: OpenAI chat model instance
        """
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=self.config.openai_api_key,
            streaming=True,  # Enable token-level streaming
            **kwargs
        )

    def _create_anthropic_llm(
        self,
        model: str,
        temperature: float,
        **kwargs
    ) -> ChatAnthropic:
        """Create Anthropic LLM instance.

        Args:
            model: Anthropic model name
            temperature: Temperature for generation
            **kwargs: Additional Anthropic-specific arguments

        Returns:
            ChatAnthropic: Anthropic chat model instance
        """
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            anthropic_api_key=self.config.anthropic_api_key,
            streaming=True,  # Enable token-level streaming
            **kwargs
        )

    def _create_google_llm(
        self,
        model: str,
        temperature: float,
        **kwargs
    ) -> ChatGoogleGenerativeAI:
        """Create Google LLM instance.

        Args:
            model: Google model name
            temperature: Temperature for generation
            **kwargs: Additional Google-specific arguments

        Returns:
            ChatGoogleGenerativeAI: Google chat model instance
        """
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=self.config.google_api_key,
            streaming=True,  # Enable token-level streaming
            **kwargs
        )


# Global factory instance (lazy loaded via singleton pattern)
_factory_instance: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """Get global LLM factory instance (singleton pattern).

    Returns:
        LLMFactory: Global factory instance

    Raises:
        ValueError: If factory initialization fails (e.g., missing API key)
    """
    global _factory_instance

    if _factory_instance is None:
        _factory_instance = LLMFactory()

    return _factory_instance


def create_llm(tier: ModelTier, temperature: float, **kwargs) -> BaseChatModel:
    """Convenience function to create LLM without directly using factory.

    This is the recommended way to create LLM instances in agents.

    Args:
        tier: Model tier (primary/research/validation)
        temperature: Temperature for generation
        **kwargs: Additional provider-specific arguments

    Returns:
        BaseChatModel: LLM instance

    Example:
        >>> from braze_code_gen.core.llm_factory import create_llm
        >>> from braze_code_gen.core.models import ModelTier
        >>> llm = create_llm(tier=ModelTier.PRIMARY, temperature=0.7)
    """
    factory = get_llm_factory()
    return factory.create_llm(tier, temperature, **kwargs)
