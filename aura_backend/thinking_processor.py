"""Async compatibility processor for legacy Gemini thinking call sites.

The primary Gemini adapter now translates directly into Aura's typed provider
contract.  This module remains import-compatible for older callers, but it uses
only awaitable chat sends and exposes a fixed reflection summary rather than raw
provider reasoning, prompts, tool results, or exception text.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from aura_backend.providers.errors import ProviderErrorCode, ProviderFailure


_REFLECTION_SUMMARY = "Internal reasoning was used."


def _field(value: object, name: str, default: Any = None) -> Any:
    """Read one field from an SDK-like mapping or object."""
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


@dataclass(frozen=True, slots=True)
class ThinkingResult:
    """Normalized legacy result with no raw SDK or hidden-reasoning values."""

    thoughts: str
    answer: str
    total_chunks: int
    thinking_chunks: int
    answer_chunks: int
    processing_time_ms: float
    has_thinking: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class _ParsedResponse:
    answer: str
    function_calls: tuple[object, ...]
    total_chunks: int
    thinking_chunks: int
    answer_chunks: int

    @property
    def has_thinking(self) -> bool:
        return self.thinking_chunks > 0


class ThinkingProcessor:
    """Await Gemini-compatible chats without exposing raw thought content."""

    def __init__(self, client: object) -> None:
        self._client = client
        self.thinking_budget = int(os.getenv("THINKING_BUDGET", "-1"))
        self._max_tool_turns = max(
            1,
            int(os.getenv("TOOL_CALL_MAX_RETRIES", "3")),
        )

    @staticmethod
    def _failure(
        code: ProviderErrorCode,
        *,
        retryable: bool = False,
    ) -> ProviderFailure:
        return ProviderFailure(
            code=code,
            provider="gemini",
            retryable=retryable,
        )

    @classmethod
    def _map_send_error(cls, error: BaseException) -> ProviderFailure:
        if isinstance(error, ProviderFailure):
            return error
        if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            return cls._failure(ProviderErrorCode.TIMEOUT, retryable=True)
        return cls._failure(ProviderErrorCode.UNAVAILABLE, retryable=True)

    @classmethod
    async def _send(cls, chat: object, message: object) -> object:
        """Await one chat send and normalize transport errors without their text."""
        try:
            send = getattr(chat, "send_message")
            return await send(message)
        except asyncio.CancelledError:
            raise
        except ProviderFailure:
            raise
        except Exception as error:
            raise cls._map_send_error(error) from error

    @classmethod
    def _parse(cls, response: object) -> _ParsedResponse:
        """Extract answer metadata while discarding provider thought text."""
        try:
            candidates = _field(response, "candidates")
            if not isinstance(candidates, (list, tuple)) or not candidates:
                raise ValueError
            content = _field(candidates[0], "content")
            parts = _field(content, "parts") if content is not None else None
            if not isinstance(parts, (list, tuple)) or not parts:
                raise ValueError

            answers: list[str] = []
            function_calls: list[object] = []
            thinking_chunks = 0
            answer_chunks = 0
            for part in parts:
                if _field(part, "thought") is True:
                    thinking_chunks += 1
                    continue
                text = _field(part, "text")
                if text is not None:
                    if not isinstance(text, str):
                        raise ValueError
                    if text:
                        answers.append(text)
                        answer_chunks += 1
                call = _field(part, "function_call")
                if call is not None:
                    name = _field(call, "name")
                    arguments = _field(call, "args")
                    if (
                        not isinstance(name, str)
                        or not name
                        or not isinstance(arguments, Mapping)
                    ):
                        raise ValueError
                    function_calls.append(call)
        except (AttributeError, TypeError, ValueError):
            raise cls._failure(ProviderErrorCode.MALFORMED_RESPONSE) from None

        return _ParsedResponse(
            answer="".join(answers),
            function_calls=tuple(function_calls),
            total_chunks=len(parts),
            thinking_chunks=thinking_chunks,
            answer_chunks=answer_chunks,
        )

    @staticmethod
    def _result(
        parsed: _ParsedResponse,
        answer: str,
        started: float,
        *,
        total_chunks: int | None = None,
        thinking_chunks: int | None = None,
        answer_chunks: int | None = None,
    ) -> ThinkingResult:
        return ThinkingResult(
            thoughts=_REFLECTION_SUMMARY if (thinking_chunks or parsed.has_thinking) else "",
            answer=answer,
            total_chunks=parsed.total_chunks if total_chunks is None else total_chunks,
            thinking_chunks=(
                parsed.thinking_chunks if thinking_chunks is None else thinking_chunks
            ),
            answer_chunks=parsed.answer_chunks if answer_chunks is None else answer_chunks,
            processing_time_ms=(perf_counter() - started) * 1000,
            has_thinking=bool(thinking_chunks or parsed.has_thinking),
        )

    async def process_message_with_thinking(
        self,
        chat: object,
        message: str,
        user_id: str,
        include_thinking_in_response: bool = False,
    ) -> ThinkingResult:
        """Await a response and return its answer plus safe reasoning metadata."""
        del user_id, include_thinking_in_response
        started = perf_counter()
        parsed = self._parse(await self._send(chat, message))
        if parsed.function_calls or not parsed.answer.strip():
            raise self._failure(ProviderErrorCode.MALFORMED_RESPONSE)
        return self._result(parsed, parsed.answer, started)

    async def process_with_function_calls_and_thinking(
        self,
        chat: object,
        message: str,
        user_id: str,
        mcp_bridge: object | None = None,
        include_thinking_in_response: bool = False,
    ) -> ThinkingResult:
        """Await bounded tool follow-ups and return only normalized answer data."""
        del include_thinking_in_response
        started = perf_counter()
        next_message: object = message
        answer_parts: list[str] = []
        total_chunks = 0
        thinking_chunks = 0
        answer_chunks = 0
        for tool_turn in range(1, self._max_tool_turns + 1):
            parsed = self._parse(await self._send(chat, next_message))
            answer_parts.append(parsed.answer)
            total_chunks += parsed.total_chunks
            thinking_chunks += parsed.thinking_chunks
            answer_chunks += parsed.answer_chunks

            if not parsed.function_calls:
                answer = "".join(answer_parts)
                if not answer.strip():
                    raise self._failure(ProviderErrorCode.MALFORMED_RESPONSE)
                return self._result(
                    parsed,
                    answer,
                    started,
                    total_chunks=total_chunks,
                    thinking_chunks=thinking_chunks,
                    answer_chunks=answer_chunks,
                )

            if tool_turn >= self._max_tool_turns:
                raise self._failure(ProviderErrorCode.RESOURCE_LIMIT)
            if mcp_bridge is None:
                raise self._failure(ProviderErrorCode.UNAVAILABLE)

            function_responses: list[dict[str, object]] = []
            for call in parsed.function_calls:
                try:
                    execute = getattr(mcp_bridge, "execute_function_call")
                    execution = await execute(call, user_id)
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    raise self._map_send_error(error) from error
                if _field(execution, "success") is not True:
                    raise self._failure(ProviderErrorCode.UNAVAILABLE)
                result_is_missing = (
                    "result" not in execution
                    if isinstance(execution, Mapping)
                    else not hasattr(execution, "result")
                )
                if result_is_missing:
                    raise self._failure(ProviderErrorCode.MALFORMED_RESPONSE)
                function_responses.append(
                    {
                        "function_response": {
                            "name": _field(call, "name"),
                            "response": {"result": _field(execution, "result")},
                        }
                    }
                )
            next_message = function_responses

        raise self._failure(ProviderErrorCode.RESOURCE_LIMIT)

    @staticmethod
    def _looks_like_thinking_content(content: str) -> bool:
        """Retain the legacy helper without using it to expose model reasoning."""
        return bool(content and content.strip())

    @staticmethod
    def _clean_follow_up_content(content: str) -> str:
        """Retain the legacy helper for callers that normalize display text."""
        return content.strip() if content else ""


def create_thinking_enabled_chat(
    client: object,
    model: str,
    system_instruction: str,
    tools: list[object] | None = None,
    thinking_budget: int | None = None,
) -> object:
    """Create an ephemeral async chat through ``client.aio`` only."""
    if thinking_budget is None:
        thinking_budget = int(os.getenv("THINKING_BUDGET", "-1"))
    config: dict[str, object] = {
        "temperature": 0.7,
        "max_output_tokens": int(os.getenv("AURA_MAX_OUTPUT_TOKENS", "1000000")),
        "system_instruction": system_instruction,
        "thinking_config": {
            "include_thoughts": True,
            "thinking_budget": thinking_budget,
        },
    }
    if tools:
        config["tools"] = tools
    try:
        return getattr(client, "aio").chats.create(
            model=model,
            config=config,
        )
    except ProviderFailure:
        raise
    except Exception as error:
        raise ProviderFailure(
            code=ProviderErrorCode.CONFIGURATION,
            provider="gemini",
            retryable=False,
        ) from error
