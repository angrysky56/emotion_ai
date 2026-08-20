"""Explicit OpenRouter cloud policy over the shared compatible transport."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from .config import ProviderSettings
from .errors import ProviderErrorCode, ProviderFailure
from .openai_compatible import ClientFactory, OpenAICompatibleProvider
from .tools import ToolExecutor


_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/angrysky56/emotion_ai",
    "X-Title": "Aura",
}


def _value_field(value: object, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _validate_openrouter_settings(settings: ProviderSettings) -> None:
    """Fail before client construction for implicit or unsafe cloud config."""
    if settings.provider.value != "openrouter":
        raise ProviderFailure(
            code=ProviderErrorCode.CONFIGURATION,
            provider="openrouter",
            setting_name="AURA_DEFAULT_PROVIDER",
        )
    if settings.api_key is None:
        raise ProviderFailure(
            code=ProviderErrorCode.CONFIGURATION,
            provider="openrouter",
            setting_name="OPENROUTER_API_KEY",
        )
    if settings.base_url is None:
        raise ProviderFailure(
            code=ProviderErrorCode.CONFIGURATION,
            provider="openrouter",
            setting_name="OPENROUTER_BASE_URL",
        )
    parsed = urlsplit(settings.base_url)
    if parsed.scheme != "https" or parsed.path.rstrip("/") != "/api/v1":
        raise ProviderFailure(
            code=ProviderErrorCode.CONFIGURATION,
            provider="openrouter",
            setting_name="OPENROUTER_BASE_URL",
        )


class OpenRouterProvider(OpenAICompatibleProvider):
    """Explicit cloud adapter with documented in-band error detection."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "deepseek/deepseek-r1",
        base_url: str = "https://openrouter.ai/api/v1",
        mcp_client_manager: Any = None,
        aura_internal_tools: Any = None,
        *,
        settings: ProviderSettings | None = None,
        client: object | None = None,
        client_factory: ClientFactory | None = None,
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        # Compatibility arguments remain until the factory moves to validated
        # settings. Neutral ToolExecutor is the only supported routing path.
        del mcp_client_manager, aura_internal_tools
        if settings is None:
            mapping: dict[str, str | None] = {
                "AURA_DEFAULT_PROVIDER": "openrouter",
                "OPENROUTER_API_KEY": api_key,
                "OPENROUTER_MODEL": model_name,
                "OPENROUTER_BASE_URL": base_url,
            }
            settings = ProviderSettings.from_mapping(mapping)
        _validate_openrouter_settings(settings)
        kwargs: dict[str, object] = {
            "settings": settings,
            "provider_name": "openrouter",
            "api_key": settings.api_key,
            "default_headers": _OPENROUTER_HEADERS,
            "client": client,
            "tool_executor": tool_executor,
        }
        if client_factory is not None:
            kwargs["client_factory"] = client_factory
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.base_url = settings.base_url

    @staticmethod
    def _error_status(value: object) -> int | None:
        """Detect top-level and Chat Completions embedded error envelopes."""
        direct_error = _value_field(value, "error")
        if direct_error is not None:
            code = _value_field(direct_error, "code")
            return code if isinstance(code, int) and not isinstance(code, bool) else 500

        choices = _value_field(value, "choices")
        if not isinstance(choices, (list, tuple)) or not choices:
            return None
        choice = choices[0]
        embedded_error = _value_field(choice, "error")
        if embedded_error is None:
            message = _value_field(choice, "message")
            embedded_error = _value_field(message, "error")
        if embedded_error is not None:
            code = _value_field(embedded_error, "code")
            return code if isinstance(code, int) and not isinstance(code, bool) else 500
        if _value_field(choice, "finish_reason") == "error":
            return 500
        return None
