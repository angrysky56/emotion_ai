"""Offline tests for strict, lazy, local-first provider selection."""

from __future__ import annotations

import logging
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

from aura_backend.providers.config import ProviderKind, ProviderSettings
from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure


ADAPTER_MODULES = {
    ProviderKind.OLLAMA: "aura_backend.providers.ollama",
    ProviderKind.GEMINI: "aura_backend.providers.gemini",
    ProviderKind.OPENROUTER: "aura_backend.providers.openrouter",
}
ADAPTER_CLASSES = {
    ProviderKind.OLLAMA: "OllamaProvider",
    ProviderKind.GEMINI: "GeminiProvider",
    ProviderKind.OPENROUTER: "OpenRouterProvider",
}
SECRET = "credential-SENTINEL-factory"


def _settings(kind: ProviderKind) -> ProviderSettings:
    mapping: dict[str, str] = {
        "AURA_DEFAULT_PROVIDER": kind.value,
        "OLLAMA_MODEL": "local-model",
        "GEMINI_API_KEY": SECRET,
        "AURA_MODEL": "gemini-model",
        "OPENROUTER_API_KEY": SECRET,
        "OPENROUTER_MODEL": "router/model",
    }
    return ProviderSettings.from_mapping(mapping)


def test_importing_factory_does_not_import_any_concrete_adapter() -> None:
    probe = """
import sys
import aura_backend.providers.factory

blocked = {
    'aura_backend.providers.ollama',
    'aura_backend.providers.gemini',
    'aura_backend.providers.openrouter',
}
loaded = sorted(blocked.intersection(sys.modules))
if loaded:
    raise SystemExit(f'eager adapters: {loaded}')
"""
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout


def _install_adapter_tripwires(
    monkeypatch: pytest.MonkeyPatch,
    *,
    selected: ProviderKind | None = None,
) -> tuple[list[tuple[ProviderKind, dict[str, Any]]], dict[ProviderKind, object]]:
    constructed: list[tuple[ProviderKind, dict[str, Any]]] = []
    instances: dict[ProviderKind, object] = {}

    for kind, module_name in ADAPTER_MODULES.items():
        monkeypatch.delitem(sys.modules, module_name, raising=False)
        if selected is not None and kind is not selected:
            continue
        module = ModuleType(module_name)
        instance = object()

        def constructor(
            *,
            _kind: ProviderKind = kind,
            _instance: object = instance,
            **kwargs: Any,
        ) -> object:
            constructed.append((_kind, kwargs))
            return _instance

        setattr(module, ADAPTER_CLASSES[kind], constructor)
        monkeypatch.setitem(sys.modules, module_name, module)
        instances[kind] = instance

    return constructed, instances


@pytest.mark.parametrize("kind", list(ProviderKind))
def test_create_provider_imports_and_constructs_only_selected_adapter(
    kind: ProviderKind,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aura_backend.providers.factory import ModelProviderFactory

    constructed, instances = _install_adapter_tripwires(monkeypatch, selected=kind)
    tool_executor = object()

    provider = ModelProviderFactory.create_provider(
        _settings(kind),
        tool_executor=tool_executor,
    )

    assert provider is instances[kind]
    assert [selected for selected, _ in constructed] == [kind]
    kwargs = constructed[0][1]
    assert kwargs["tool_executor"] is tool_executor
    for unselected, module_name in ADAPTER_MODULES.items():
        if unselected is not kind:
            assert module_name not in sys.modules


def test_default_wrapper_is_ollama_and_does_not_import_cloud_adapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aura_backend.providers.factory import ModelProviderFactory

    constructed, _ = _install_adapter_tripwires(
        monkeypatch,
        selected=ProviderKind.OLLAMA,
    )
    monkeypatch.delenv("AURA_DEFAULT_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    ModelProviderFactory.get_provider()

    assert [kind for kind, _ in constructed] == [ProviderKind.OLLAMA]


@pytest.mark.parametrize(
    ("provider_name", "credential_name"),
    [
        ("gemini", "GEMINI_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
    ],
)
def test_missing_selected_cloud_credential_constructs_no_adapter(
    provider_name: str,
    credential_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aura_backend.providers.factory import ModelProviderFactory

    constructed, _ = _install_adapter_tripwires(monkeypatch)
    monkeypatch.delenv(credential_name, raising=False)

    with pytest.raises(ProviderFailure) as captured:
        ModelProviderFactory.get_provider(provider_name)

    assert captured.value.code is ProviderErrorCode.CONFIGURATION
    assert captured.value.setting_name == credential_name
    assert constructed == []
    assert not set(ADAPTER_MODULES.values()).intersection(sys.modules)


def test_unknown_provider_constructs_no_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aura_backend.providers.factory import ModelProviderFactory

    constructed, _ = _install_adapter_tripwires(monkeypatch)

    with pytest.raises(ProviderFailure) as captured:
        ModelProviderFactory.get_provider("unknown-provider")

    assert captured.value.code is ProviderErrorCode.CONFIGURATION
    assert captured.value.setting_name == "AURA_DEFAULT_PROVIDER"
    assert constructed == []
    assert not set(ADAPTER_MODULES.values()).intersection(sys.modules)


def test_factory_diagnostics_exclude_credentials_and_endpoint_details(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aura_backend.providers.factory import ModelProviderFactory

    _install_adapter_tripwires(monkeypatch)
    settings = _settings(ProviderKind.OPENROUTER)

    with caplog.at_level(logging.INFO):
        ModelProviderFactory.create_provider(settings)

    assert "provider=openrouter" in caplog.text
    assert "model=router/model" in caplog.text
    assert SECRET not in caplog.text
    assert "https://" not in caplog.text
    assert "Authorization" not in caplog.text
