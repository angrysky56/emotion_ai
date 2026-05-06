# Research: Unified Model Provider

## OpenRouter Integration
- **API Format**: OpenAI-compatible.
- **Tool Calling**:
  - Uses the `tools` array in the request.
  - Requires handling the `tool_calls` response and sending back `tool` messages.
- **Thinking/Reasoning**:
  - Enable with `"include_reasoning": true`.
  - Reasoning trace is available in the `reasoning` field of the message.
  - Use `:thinking` suffix for some models (e.g., `deepseek/deepseek-r1:thinking`).

## Ollama Integration
- **API Format**: Custom REST API or OpenAI-compatible (via `/v1/chat/completions`).
- **Tool Calling**:
  - Supported in recent versions via the `tools` parameter in `/api/chat`.
  - Format is similar to OpenAI's tool calling.

## ModelProvider Interface Requirements
To support all three (Gemini, OpenRouter, Ollama), the interface needs:
1. **`generate_response(messages: List[Message], tools: Optional[List[Tool]] = None) -> Response`**
2. **`stream_response(...) -> AsyncIterator[Chunk]`**
3. **`convert_mcp_tool(mcp_tool: dict) -> dict`**: Each provider will have its own schema requirements.
4. **`extract_thoughts(response: Any) -> str`**: Standardize how reasoning is pulled from different providers.

## Fallback Strategy
1. **Config-driven**: `PRIMARY_PROVIDER` (default: `gemini`).
2. **Sequential Fallback**: If `gemini` fails (or 429), try `openrouter`. If both fail, try `ollama` (local).
3. **Capability Matching**: Some models might not support thinking or tool calling; the system should handle this gracefully (e.g., by omitting tools or using prompt-based fallbacks).
