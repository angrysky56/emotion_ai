"""Strict, local-first construction for Aura's selected model provider.

Concrete adapters are imported only inside their validated selection branch.
Importing this module therefore remains safe when optional cloud SDKs are absent.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from .base import Provider
from .config import ProviderKind, ProviderSettings
from .errors import ProviderErrorCode, ProviderFailure

if TYPE_CHECKING:
    from .tools import ToolExecutor

logger = logging.getLogger(__name__)


class ModelProviderFactory:
    """Construct exactly one explicitly selected provider adapter."""

    @staticmethod
    def create_provider(
        settings: ProviderSettings,
        *,
        tool_executor: ToolExecutor | None = None,
    ) -> Provider:
        """Build the validated adapter without probing any other provider.

        ``ProviderSettings.from_mapping`` owns validation and credential policy.
        This method deliberately contains one exact branch per supported kind so
        an Ollama-only runtime never imports a cloud adapter module.
        """
        if not isinstance(settings, ProviderSettings) or not isinstance(
            settings.kind,
            ProviderKind,
        ):
            raise ProviderFailure(
                code=ProviderErrorCode.CONFIGURATION,
                setting_name="AURA_DEFAULT_PROVIDER",
            )

        logger.info(
            "Creating model provider: provider=%s model=%s",
            settings.kind.value,
            settings.model,
        )

        if settings.kind is ProviderKind.OLLAMA:
            from .ollama import OllamaProvider

            return OllamaProvider(
                settings=settings,
                tool_executor=tool_executor,
            )

        if settings.kind is ProviderKind.GEMINI:
            from .gemini import GeminiProvider

            return GeminiProvider(
                api_key=settings.api_key,
                model_name=settings.model,
                thinking_budget=settings.thinking_budget,
                tool_executor=tool_executor,
                max_tool_turns=settings.max_tool_turns,
            )

        if settings.kind is ProviderKind.OPENROUTER:
            from .openrouter import OpenRouterProvider

            return OpenRouterProvider(
                settings=settings,
                tool_executor=tool_executor,
            )

        # Defensive fail-closed branch for malformed manually constructed values.
        raise ProviderFailure(
            code=ProviderErrorCode.CONFIGURATION,
            setting_name="AURA_DEFAULT_PROVIDER",
        )

    @staticmethod
    def get_provider(
        provider_type: str | None = None,
        mcp_client_manager: Any = None,
        aura_internal_tools: Any = None,
        *,
        tool_executor: ToolExecutor | None = None,
    ) -> Provider:
        """Compatibility wrapper using the process environment at composition.

        Legacy provider-specific tool arguments are retained in the signature so
        existing startup code remains callable.  Adapters now receive only the
        provider-neutral executor.
        """
        del mcp_client_manager, aura_internal_tools
        mapping: dict[str, str] = dict(os.environ)
        if provider_type is not None:
            mapping["AURA_DEFAULT_PROVIDER"] = provider_type
        settings = ProviderSettings.from_mapping(mapping)
        return ModelProviderFactory.create_provider(
            settings,
            tool_executor=tool_executor,
        )

    @staticmethod
    def get_all_available_providers() -> list[str]:
        """List all implemented provider types."""
        return [kind.value for kind in ProviderKind]
