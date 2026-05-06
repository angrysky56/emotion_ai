"""
Model Provider Factory for Aura.
Handles instantiation of different LLM providers (Gemini, OpenRouter, Ollama).
"""

import logging
import os
from typing import Any, List, Optional

from .base import BaseProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


class ModelProviderFactory:
    """
    Factory class for creating and managing model providers.
    Handles configuration and instantiation based on environment variables.
    """

    @staticmethod
    def get_provider(
        provider_type: Optional[str] = None,
        mcp_client_manager: Any = None,
        aura_internal_tools: Any = None,
    ) -> BaseProvider:
        """
        Instantiate the requested provider or the default one.
        """
        # 1. Determine provider type
        ptype = provider_type or os.getenv("AURA_DEFAULT_PROVIDER", "gemini").lower()

        logger.info("🏗️ Creating model provider: %s", ptype)

        # 2. Instantiate based on type
        if ptype == "gemini":
            return GeminiProvider(
                api_key=os.getenv("GEMINI_API_KEY", ""),
                model_name=os.getenv(
                    "AURA_MODEL", "gemini-2.0-flash-thinking-exp-01-21"
                ),
                thinking_budget=int(os.getenv("THINKING_BUDGET", "-1")),
                mcp_client_manager=mcp_client_manager,
                aura_internal_tools=aura_internal_tools,
            )

        elif ptype == "openrouter":
            return OpenRouterProvider(
                api_key=os.getenv("OPENROUTER_API_KEY", ""),
                model_name=os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1"),
                mcp_client_manager=mcp_client_manager,
                aura_internal_tools=aura_internal_tools,
            )

        elif ptype == "ollama":
            return OllamaProvider(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                model_name=os.getenv("OLLAMA_MODEL", "llama3.1"),
                mcp_client_manager=mcp_client_manager,
                aura_internal_tools=aura_internal_tools,
            )

        else:
            logger.warning(
                "⚠️ Unknown provider type '%s', falling back to Gemini", ptype
            )
            return GeminiProvider(
                api_key=os.getenv("GEMINI_API_KEY", ""),
                mcp_client_manager=mcp_client_manager,
                aura_internal_tools=aura_internal_tools,
            )

    @staticmethod
    def get_all_available_providers() -> List[str]:
        """List all implemented provider types."""
        return ["gemini", "openrouter", "ollama"]
