"""Local Ollama policy over Aura's shared OpenAI-compatible transport."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from openai import APIConnectionError, APITimeoutError

from .base import ProviderHealth, ProviderHealthStatus
from .config import ProviderSettings
from .errors import ProviderErrorCode, ProviderFailure
from .openai_compatible import ClientFactory, OpenAICompatibleProvider
from .tools import ToolExecutor


def _normalize_ollama_settings(settings: ProviderSettings) -> ProviderSettings:
    """Require Ollama's documented root or ``/v1`` compatible endpoint."""
    if settings.provider.value != "ollama" or settings.base_url is None:
        raise ProviderFailure(
            code=ProviderErrorCode.CONFIGURATION,
            provider="ollama",
            setting_name="AURA_DEFAULT_PROVIDER",
        )
    parsed = urlsplit(settings.base_url)
    path = parsed.path.rstrip("/")
    if path not in {"", "/v1"}:
        raise ProviderFailure(
            code=ProviderErrorCode.CONFIGURATION,
            provider="ollama",
            setting_name="OLLAMA_BASE_URL",
        )
    normalized = urlunsplit(
        (parsed.scheme, parsed.netloc, "/v1", "", "")
    )
    return replace(settings, base_url=normalized)


class OllamaProvider(OpenAICompatibleProvider):
    """Complete local provider with bounded, generation-free model readiness."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        mcp_client_manager: Any = None,
        aura_internal_tools: Any = None,
        *,
        settings: ProviderSettings | None = None,
        client: Any = None,
        client_factory: ClientFactory | None = None,
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        # Legacy constructor arguments remain accepted until the factory migration.
        # Tool routing itself is owned only by the neutral ToolExecutor.
        del mcp_client_manager, aura_internal_tools
        if settings is None:
            mapping: dict[str, str] = {"AURA_DEFAULT_PROVIDER": "ollama"}
            if base_url is not None:
                mapping["OLLAMA_BASE_URL"] = base_url
            if model_name is not None:
                mapping["OLLAMA_MODEL"] = model_name
            settings = ProviderSettings.from_mapping(mapping)
        settings = _normalize_ollama_settings(settings)
        kwargs: dict[str, object] = {
            "settings": settings,
            "provider_name": "ollama",
            "api_key": "ollama",
            "client": client,
            "tool_executor": tool_executor,
        }
        if client_factory is not None:
            kwargs["client_factory"] = client_factory
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.base_url = settings.base_url

    async def health(self) -> ProviderHealth:
        """List installed model metadata within a finite local readiness bound."""
        timeout_seconds = min(
            self._settings.connect_timeout_seconds,
            self._settings.request_timeout_seconds,
        )
        try:
            async with asyncio.timeout(timeout_seconds):
                response = await self._client.models.list()
        except asyncio.CancelledError:
            raise
        except (TimeoutError, APITimeoutError, APIConnectionError, httpx.NetworkError):
            return ProviderHealth(
                provider="ollama",
                model=self.model_name,
                status=ProviderHealthStatus.UNAVAILABLE,
                retryable=True,
            )
        except Exception as error:
            raise ProviderFailure(
                code=ProviderErrorCode.MALFORMED_RESPONSE,
                provider="ollama",
                model=self.model_name,
                retryable=False,
            ) from error

        data = getattr(response, "data", None)
        if not isinstance(data, (list, tuple)):
            raise ProviderFailure(
                code=ProviderErrorCode.MALFORMED_RESPONSE,
                provider="ollama",
                model=self.model_name,
                retryable=False,
            )
        model_ids: set[str] = set()
        for item in data:
            model_id = getattr(item, "id", None)
            if not isinstance(model_id, str) or not model_id:
                raise ProviderFailure(
                    code=ProviderErrorCode.MALFORMED_RESPONSE,
                    provider="ollama",
                    model=self.model_name,
                    retryable=False,
                )
            model_ids.add(model_id)
        status = (
            ProviderHealthStatus.READY
            if self.model_name in model_ids
            else ProviderHealthStatus.MODEL_NOT_FOUND
        )
        return ProviderHealth(
            provider="ollama",
            model=self.model_name,
            status=status,
            retryable=False,
        )
