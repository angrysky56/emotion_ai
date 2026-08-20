"""Deterministic ownership of Aura application resources.

Concrete provider, storage, and tool construction belongs in a later composition
root.  This module only invokes injected asynchronous factories and owns the
resources they successfully return.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable, Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .config import RuntimeSettings

AsyncClose = Callable[[], Awaitable[None]]
AsyncStart = Callable[[], Awaitable["StartedResource | None"]]
_RESOURCE_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class ResourceState(str, Enum):
    """Safe lifecycle states exposed without resource or exception details."""

    NOT_STARTED = "not_started"
    NOT_CONFIGURED = "not_configured"
    READY = "ready"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class StartedResource:
    """One constructed value paired with its already-bound async cleanup."""

    value: object
    close: AsyncClose

    def __post_init__(self) -> None:
        if not callable(self.close):
            raise TypeError("close must be callable")


@dataclass(frozen=True, slots=True)
class ResourceFactory:
    """Declarative resource stage; ``None`` means optional and not configured."""

    name: str
    start: AsyncStart
    required: bool = True

    def __post_init__(self) -> None:
        if _RESOURCE_NAME.fullmatch(self.name) is None:
            raise ValueError("resource name must be safe diagnostic metadata")
        if not callable(self.start):
            raise TypeError("start must be callable")
        if not isinstance(self.required, bool):
            raise TypeError("required must be a bool")


@dataclass(frozen=True, slots=True)
class ResourceStatus:
    """Content-free status for one declared runtime resource."""

    name: str
    required: bool
    state: ResourceState
    code: str | None = None


@dataclass(frozen=True, slots=True)
class ApplicationRuntimeSnapshot:
    """Cached application lifecycle truth; reading it performs no work."""

    ready: bool
    accepting_work: bool
    closed: bool
    code: str | None
    resources: tuple[ResourceStatus, ...]


class RuntimeStartupError(RuntimeError):
    """Safe required-resource startup failure."""

    def __init__(self, *, code: str, resource: str | None = None) -> None:
        self.code = code
        self.resource = resource
        suffix = f" resource={resource}" if resource is not None else ""
        super().__init__(f"application runtime startup: code={code}{suffix}")


class RuntimeShutdownError(RuntimeError):
    """Safe resource-shutdown failure."""

    def __init__(self) -> None:
        self.code = "shutdown_failed"
        super().__init__("application runtime shutdown: code=shutdown_failed")


class ApplicationRuntime:
    """Start resources in order and close successful stages in reverse order."""

    def __init__(
        self,
        *,
        settings: RuntimeSettings,
        resources: Sequence[ResourceFactory],
    ) -> None:
        if not isinstance(settings, RuntimeSettings):
            raise TypeError("settings must be RuntimeSettings")
        resource_tuple = tuple(resources)
        names = tuple(resource.name for resource in resource_tuple)
        if len(set(names)) != len(names):
            raise ValueError("resource names must be unique")
        self.settings = settings
        self._resources = resource_tuple
        self._statuses = {
            resource.name: ResourceStatus(
                name=resource.name,
                required=resource.required,
                state=ResourceState.NOT_STARTED,
            )
            for resource in resource_tuple
        }
        self._values: dict[str, object] = {}
        self._exit_stack = AsyncExitStack()
        self._start_lock = asyncio.Lock()
        self._close_lock = asyncio.Lock()
        self._ready = False
        self._accepting_work = False
        self._closed = False
        self._code: str | None = None

    def _set_status(
        self,
        resource: ResourceFactory,
        state: ResourceState,
        code: str | None = None,
    ) -> None:
        self._statuses[resource.name] = ResourceStatus(
            name=resource.name,
            required=resource.required,
            state=state,
            code=code,
        )

    def snapshot(self) -> ApplicationRuntimeSnapshot:
        """Return cached, content-free lifecycle state without probing resources."""
        return ApplicationRuntimeSnapshot(
            ready=self._ready,
            accepting_work=self._accepting_work,
            closed=self._closed,
            code=self._code,
            resources=tuple(
                self._statuses[resource.name] for resource in self._resources
            ),
        )

    def resource(self, name: str) -> object:
        """Return a ready resource or fail without exposing internal state."""
        if not self._accepting_work or name not in self._values:
            raise RuntimeStartupError(code="runtime_unavailable", resource=name)
        return self._values[name]

    async def _close_resource(
        self,
        resource: ResourceFactory,
        close: AsyncClose,
    ) -> None:
        try:
            await close()
        except asyncio.CancelledError:
            self._set_status(resource, ResourceState.FAILED, "shutdown_cancelled")
            raise
        except Exception:
            self._set_status(resource, ResourceState.FAILED, "shutdown_failed")
            raise
        else:
            self._set_status(resource, ResourceState.CLOSED)
        finally:
            self._values.pop(resource.name, None)

    async def start(self) -> ApplicationRuntime:
        """Construct declared stages and become ready only after required success."""
        async with self._start_lock:
            if self._ready:
                return self
            if self._closed:
                raise RuntimeStartupError(code="runtime_closed")

            for resource in self._resources:
                try:
                    started = await resource.start()
                    if started is None:
                        if resource.required:
                            raise RuntimeStartupError(
                                code="required_resource_missing",
                                resource=resource.name,
                            )
                        self._set_status(resource, ResourceState.NOT_CONFIGURED)
                        continue
                    if not isinstance(started, StartedResource):
                        raise TypeError("factory must return StartedResource or None")
                    self._values[resource.name] = started.value
                    self._exit_stack.push_async_callback(
                        self._close_resource,
                        resource,
                        started.close,
                    )
                    self._set_status(resource, ResourceState.READY)
                except asyncio.CancelledError:
                    self._set_status(resource, ResourceState.FAILED, "startup_cancelled")
                    self._code = "startup_cancelled"
                    await self._exit_stack.aclose()
                    self._closed = True
                    raise
                except Exception as error:
                    if not resource.required:
                        self._set_status(
                            resource,
                            ResourceState.FAILED,
                            "optional_resource_failed",
                        )
                        continue
                    code = (
                        error.code
                        if isinstance(error, RuntimeStartupError)
                        else "required_resource_failed"
                    )
                    self._set_status(resource, ResourceState.FAILED, code)
                    self._code = code
                    try:
                        await self._exit_stack.aclose()
                    finally:
                        self._closed = True
                    if isinstance(error, RuntimeStartupError):
                        raise
                    raise RuntimeStartupError(
                        code=code,
                        resource=resource.name,
                    ) from error

            self._ready = True
            self._accepting_work = True
            self._code = None
            return self

    async def aclose(self) -> None:
        """Reject new access and close every started resource at most once."""
        async with self._close_lock:
            if self._closed:
                return
            self._ready = False
            self._accepting_work = False
            try:
                await self._exit_stack.aclose()
            except asyncio.CancelledError:
                self._code = "shutdown_cancelled"
                raise
            except Exception as error:
                self._code = "shutdown_failed"
                raise RuntimeShutdownError() from error
            finally:
                self._closed = True

    async def __aenter__(self) -> ApplicationRuntime:
        return await self.start()

    async def __aexit__(self, *_exc_info: Any) -> None:
        await self.aclose()
