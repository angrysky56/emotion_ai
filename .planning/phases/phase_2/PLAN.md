# Phase Plan: Unified Model Provider

This phase focuses on abstracting the LLM interaction layer to provide a unified interface for multiple model providers (Gemini, OpenRouter, and Ollama). This will improve system resilience through fallback mechanisms and allow for easy testing of different models.

## 1. Research & Analysis
- [x] Identify current Gemini-specific code in `main.py` and `mcp_to_gemini_bridge.py`.
- [ ] Research OpenRouter API (OpenAI compatible) for tool calling and thinking support.
- [ ] Research Ollama API for tool calling capabilities.
- [ ] Define the `ModelProvider` interface requirements.

## 2. Implementation Tasks

### 2.1. Core Abstraction
- [ ] Create `aura_backend/providers/base.py` defining the `ModelProvider` abstract base class.
- [ ] Define common types for messages, tool definitions, and tool execution results.
- [ ] Implement `ModelProviderFactory` to manage provider instantiation.

### 2.2. Gemini Provider (Primary)
- [ ] Create `aura_backend/providers/gemini.py`.
- [ ] Port the existing Gemini logic from `main.py` and `mcp_to_gemini_bridge.py`.
- [ ] Maintain support for "Thinking" and native function calling.

### 2.3. OpenRouter Provider
- [ ] Create `aura_backend/providers/openrouter.py`.
- [ ] Implement the OpenAI-compatible client for OpenRouter.
- [ ] Map MCP tool schemas to OpenAI tool formats.
- [ ] Support thinking/reasoning models (like o1, o3-mini) if available via OpenRouter.

### 2.4. Ollama Provider (Local Fallback)
- [ ] Create `aura_backend/providers/ollama.py`.
- [ ] Implement the local Ollama client.
- [ ] Implement tool calling fallback (prompt-based) if native tool calling is limited.

### 2.5. Integration & Fallback Logic
- [ ] Update `main.py` to use `ModelProviderFactory` instead of direct Gemini client calls.
- [ ] Implement fallback logic: try OpenRouter/Gemini first, then Ollama.
- [ ] Refactor `mcp_to_gemini_bridge.py` to be `mcp_to_llm_bridge.py` (model-agnostic).

## 3. Verification & Testing
- [ ] Unit tests for each provider's tool conversion logic.
- [ ] Integration tests for the fallback mechanism.
- [ ] E2E test with Gemini (existing functionality).
- [ ] E2E test with OpenRouter (mock or real API).
- [ ] E2E test with Ollama (local).

## 4. Success Criteria
- [ ] System can successfully switch between Gemini, OpenRouter, and Ollama via config.
- [ ] Tool calling works across all providers (with fallback where necessary).
- [ ] "Thinking" visualization still works for providers that support it.
- [ ] No regression in performance or stability for the primary Gemini flow.
