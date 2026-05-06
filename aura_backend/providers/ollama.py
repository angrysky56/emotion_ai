"""
Ollama Provider for Aura.
Handles local LLM execution via Ollama's OpenAI-compatible API.
"""

import json
import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional

from openai import AsyncOpenAI

from aura_backend.providers.base import (
    BaseProvider,
    Message,
    ProviderResponse,
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """
    Ollama implementation of the Model Provider.
    Supports local model execution with tool calling.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model_name: str = "llama3.1",
        mcp_client_manager: Any = None,
        aura_internal_tools: Any = None,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.mcp_client_manager = mcp_client_manager
        self.aura_internal_tools = aura_internal_tools

        # Ollama usually doesn't need an API key for local use
        self.client = AsyncOpenAI(api_key="ollama", base_url=self.base_url)

        self._openai_tools: List[Dict[str, Any]] = []
        self._tool_mapping: Dict[str, Dict[str, Any]] = {}

    async def convert_mcp_tools(self, mcp_tools: List[Dict[str, Any]]) -> Any:
        """Convert MCP tools to Ollama (OpenAI) format."""
        self._openai_tools = []
        self._tool_mapping = {}

        for tool in mcp_tools:
            try:
                tool_name = tool.get("name")
                if not tool_name:
                    continue

                # Clean name for OpenAI compatibility (alphanumeric and underscores)
                clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", tool_name)

                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": clean_name,
                        "description": tool.get("description", ""),
                        "parameters": tool.get(
                            "inputSchema", {"type": "object", "properties": {}}
                        ),
                    },
                }

                self._openai_tools.append(openai_tool)
                self._tool_mapping[clean_name] = {
                    "mcp_name": tool_name,
                    "server": tool.get("server", "unknown"),
                    "original_tool": tool,
                }
            except Exception as e:
                logger.error("❌ Failed to convert tool %s: %s", tool.get("name"), e)

        return self._openai_tools

    async def generate_response(
        self,
        messages: List[Message],
        system_instruction: Optional[str] = None,
        tools: Optional[Any] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> ProviderResponse:
        """
        Generate a response using Ollama's local API.
        """
        try:
            openai_messages = []
            if system_instruction:
                openai_messages.append(
                    {"role": "system", "content": system_instruction}
                )

            for msg in messages:
                m = {"role": msg.role, "content": msg.content}
                if msg.tool_calls:
                    m["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                if msg.tool_result_id:
                    m["tool_call_id"] = msg.tool_result_id
                openai_messages.append(m)

            max_turns = 5  # Ollama might be slower or loopier
            current_turn = 0

            active_tools = tools if tools is not None else self._openai_tools

            while current_turn < max_turns:
                current_turn += 1

                kwargs = {
                    "model": self.model_name,
                    "messages": openai_messages,
                    "temperature": temperature,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                if active_tools:
                    kwargs["tools"] = active_tools

                response = await self.client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message = choice.message

                if not message.tool_calls:
                    return ProviderResponse(
                        content=message.content or "",
                        role="assistant",
                        raw_response=response,
                    )

                openai_messages.append(message)

                for tool_call in message.tool_calls:
                    tc_id = tool_call.id
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    logger.info("🏠 Ollama calling tool: %s", func_name)

                    result = await self._execute_tool(func_name, func_args)

                    openai_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "name": func_name,
                            "content": json.dumps(result),
                        }
                    )

            return ProviderResponse(
                content="Error: Maximum tool call turns exceeded (Ollama)",
                role="assistant",
                error="Max turns exceeded",
            )

        except Exception as e:
            logger.error("❌ OllamaProvider generation failed: %s", e)
            return ProviderResponse(
                content=f"Local model error: {str(e)}", role="assistant", error=str(e)
            )

    async def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Helper to execute tools."""
        mapping = self._tool_mapping.get(name, {})
        mcp_name = mapping.get("mcp_name", name)
        server = mapping.get("server", "unknown")

        try:
            if server == "aura-internal":
                if self.aura_internal_tools:
                    return await self.aura_internal_tools.execute_tool(
                        mcp_name, arguments
                    )
                return "Error: Internal tools not available"
            else:
                if self.mcp_client_manager:
                    return await self.mcp_client_manager.execute_tool(
                        server, mcp_name, arguments
                    )
                return "Error: MCP client manager not available"
        except Exception as e:
            return f"Error: {str(e)}"

    async def stream_response(
        self,
        messages: List[Message],
        system_instruction: Optional[str] = None,
        tools: Optional[Any] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[ProviderResponse]:
        """Streaming for Ollama."""
        response = await self.generate_response(
            messages, system_instruction, tools, temperature, max_tokens, session_id
        )
        yield response

    async def clear_session(self, session_id: str) -> None:
        """Clear a specific chat session (stateless for Ollama)."""
        logger.info("🧹 Clearing Ollama session: %s", session_id)
        # Ollama implementation is currently stateless per request
        pass
