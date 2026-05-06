"""
OpenRouter Provider for Aura.
Handles LLM execution via OpenRouter's OpenAI-compatible API.
"""

import json
import logging
import traceback
from typing import Any, AsyncIterator, Dict, List, Optional

from openai import AsyncOpenAI

from aura_backend.providers.base import (
    BaseProvider,
    Message,
    ProviderResponse,
)

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseProvider):
    """
    OpenRouter implementation of the Model Provider.
    Uses OpenAI-compatible API to support a wide range of models.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "deepseek/deepseek-r1",
        base_url: str = "https://openrouter.ai/api/v1",
        mcp_client_manager: Any = None,
        aura_internal_tools: Any = None,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url
        self.mcp_client_manager = mcp_client_manager
        self.aura_internal_tools = aura_internal_tools

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers={
                "HTTP-Referer": "https://aura-ai.com",  # Optional
                "X-Title": "Aura AI",  # Optional
            },
        )

        self._openai_tools: List[Dict[str, Any]] = []
        self._tool_mapping: Dict[str, Dict[str, Any]] = {}

    async def convert_mcp_tools(self, mcp_tools: List[Dict[str, Any]]) -> Any:
        """
        Convert MCP tools to OpenAI function calling format.
        """
        self._openai_tools = []
        self._tool_mapping = {}

        for tool in mcp_tools:
            try:
                tool_name = tool["name"]

                # OpenAI name constraints: a-z, A-Z, 0-9, underscores and dashes
                clean_name = tool_name.replace(".", "_")

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
        Generate a response with manual tool-calling loop.
        """
        try:
            # 1. Prepare messages
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
                    # role for tool result is 'tool'
                openai_messages.append(m)

            # 2. Tool loop (Max 10 turns to prevent infinite loops)
            max_turns = 10
            current_turn = 0
            all_thoughts = []

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

                # Extract thoughts if available (DeepSeek-R1 style or tag style)
                thoughts = getattr(message, "reasoning_content", None)
                if thoughts:
                    all_thoughts.append(thoughts)

                # If content has <thought> tags, we could extract them too

                if not message.tool_calls:
                    # Final response
                    return ProviderResponse(
                        content=message.content or "",
                        role="assistant",
                        thoughts="\\n\\n".join(all_thoughts) if all_thoughts else None,
                        raw_response=response,
                    )

                # Handle tool calls
                openai_messages.append(message)  # Add assistant's tool call to history

                for tool_call in message.tool_calls:
                    tc_id = tool_call.id
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    logger.info("🔧 OpenRouter calling tool: %s", func_name)

                    # Execute tool
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
                content="Error: Maximum tool call turns exceeded",
                role="assistant",
                error="Max turns exceeded",
            )

        except Exception as e:
            logger.error("❌ OpenRouterProvider generation failed: %s", e)
            logger.error(traceback.format_exc())
            return ProviderResponse(
                content=f"Error: {str(e)}", role="assistant", error=str(e)
            )

    async def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by its clean name."""
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
                    # Call external MCP tool
                    return await self.mcp_client_manager.execute_tool(
                        server, mcp_name, arguments
                    )
                return "Error: MCP client manager not available"
        except Exception as e:
            logger.error("❌ Tool execution failed: %s", e)
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
        """Streaming for OpenRouter (Manual tool loop in stream is complex)."""
        # Simplified: just return generate_response for now
        response = await self.generate_response(
            messages, system_instruction, tools, temperature, max_tokens, session_id
        )
        yield response

    async def clear_session(self, session_id: str) -> None:
        """Clear a specific chat session (stateless for OpenRouter)."""
        logger.info("🧹 Clearing OpenRouter session: %s", session_id)
        # OpenRouter implementation is currently stateless per request
        pass
