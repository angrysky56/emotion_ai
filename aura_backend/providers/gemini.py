"""
Gemini Provider for Aura.
Handles LLM execution via Google's Gemini API with thinking support.
"""

import logging
import os
import traceback
from typing import Any, AsyncIterator, Dict, List, Optional

from google import genai
from google.genai import types

from aura_backend.mcp_to_gemini_bridge import MCPGeminiBridge
from aura_backend.providers.base import BaseProvider, Message, ProviderResponse
from aura_backend.thinking_processor import ThinkingProcessor

logger = logging.getLogger(__name__)

# Configuration for Gemini Provider
TOOL_CALL_MAX_RETRIES = int(os.getenv("TOOL_CALL_MAX_RETRIES", "3"))
TOOL_CALL_RETRY_DELAY = float(os.getenv("TOOL_CALL_RETRY_DELAY", "1.0"))


class GeminiProvider(BaseProvider):
    """
    Google Gemini implementation of the Model Provider.
    Supports thinking, tool calling, and MCP integration.
    """

    def __init__(
        self,
        api_key: str,
        model_name: Optional[str] = None,
        thinking_budget: int = 16000,
        mcp_client_manager: Any = None,
        aura_internal_tools: Any = None,
    ):
        self.api_key = api_key
        self.model_name = model_name or os.getenv(
            "AURA_MODEL", "gemini-2.0-flash-thinking-exp-01-21"
        )
        self.thinking_budget = thinking_budget
        self.mcp_client_manager = mcp_client_manager
        self.aura_internal_tools = aura_internal_tools

        # Initialize Gemini Client
        self.client = genai.Client(
            api_key=self.api_key, http_options={"api_version": "v1alpha"}
        )

        # Initialize Thinking Processor
        self.thinking_processor = ThinkingProcessor(self.client)

        # Initialize MCP Bridge for tool execution
        self.mcp_bridge = MCPGeminiBridge(mcp_client_manager, aura_internal_tools)

        # Internal state
        self._gemini_tools: List[types.Tool] = []
        self._chat_sessions: Dict[str, Any] = {}

    async def convert_mcp_tools(self, mcp_tools: List[Dict[str, Any]]) -> Any:
        """Convert MCP tools using the bridge."""
        if not self.mcp_bridge:
            return []
        self._gemini_tools = (
            await self.mcp_bridge.convert_mcp_tools_to_gemini_functions()
        )
        return self._gemini_tools

    async def clear_session(self, session_id: str) -> None:
        """Clear a specific chat session."""
        if session_id in self._chat_sessions:
            del self._chat_sessions[session_id]
            logger.info("🧹 Cleared Gemini chat session: %s", session_id)

    def _convert_messages_to_history(
        self, messages: List[Message]
    ) -> List[types.Content]:
        """Convert our Message format to Gemini Content format."""
        history = []
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            parts = [types.Part(text=msg.content)]

            # Simple conversion for now
            history.append(types.Content(role=role, parts=parts))
        return history

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
        Generate a response using Gemini's thinking processor and tool-calling loop.
        """
        try:
            if not messages:
                return ProviderResponse(
                    content="Error: No messages provided",
                    role="assistant",
                    error="No messages provided",
                )

            # 1. Prepare history and last message
            last_message = messages[-1].content
            user_id = "unknown_user"

            # 2. Configure thinking and tools
            config_kwargs = {
                "temperature": temperature,
            }
            if max_tokens:
                config_kwargs["max_output_tokens"] = max_tokens

            if self.thinking_budget > 0:
                config_kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_budget=self.thinking_budget, include_thoughts=True
                )

            active_tools = tools if tools is not None else self._gemini_tools

            # 3. Get or Create Chat Session
            chat = None
            if session_id and session_id in self._chat_sessions:
                chat = self._chat_sessions[session_id]
            else:
                history = self._convert_messages_to_history(messages[:-1])
                chat = self.client.chats.create(
                    model=self.model_name,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        tools=active_tools if active_tools else None,
                        **config_kwargs,
                    ),
                    history=history,
                )
                if session_id:
                    self._chat_sessions[session_id] = chat

            # 4. Process with ThinkingProcessor
            logger.info(
                "🧠 Processing Gemini request (Session: %s, Model: %s)",
                session_id,
                self.model_name,
            )

            thinking_result = (
                await self.thinking_processor.process_with_function_calls_and_thinking(
                    chat=chat,
                    message=last_message,
                    user_id=user_id,
                    mcp_bridge=self.mcp_bridge,
                    include_thinking_in_response=False,
                )
            )

            return ProviderResponse(
                content=thinking_result.answer,
                role="assistant",
                thoughts=(
                    thinking_result.thoughts if thinking_result.has_thinking else None
                ),
                raw_response=thinking_result,
            )

        except Exception as e:
            logger.error("❌ GeminiProvider generation failed: %s", e)
            logger.error(traceback.format_exc())
            return ProviderResponse(
                content=f"I encountered an error: {str(e)}",
                role="assistant",
                error=str(e),
            )

    async def stream_response(
        self,
        messages: List[Message],
        system_instruction: Optional[str] = None,
        tools: Optional[Any] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[ProviderResponse]:
        response = await self.generate_response(
            messages, system_instruction, tools, temperature, max_tokens, session_id
        )
        yield response
