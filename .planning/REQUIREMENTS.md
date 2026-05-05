# Requirements: Aura Modernization

## 1. Provider Integration
- **[MUST]** Implement a unified `ModelProvider` abstraction in the backend.
- **[MUST]** Integrate **OpenRouter** as the primary backend for LLM completion.
- **[MUST]** Integrate **Ollama** as the secondary/fallback backend for local execution.
- **[SHOULD]** Update frontend `auraApi.ts` to support routing through these new providers.

## 2. Code Quality & Modernization
- **[MUST]** Run a full dependency audit and update to latest compatible versions (FastAPI, Pydantic v2, ChromaDB 0.5+, etc.).
- **[MUST]** Modularize `aura_backend/main.py` into routers/services.
- **[MUST]** Refactor `index.tsx` to reduce "God Object" complexity (separate UI from State).
- **[MUST]** Enforce strict typing across all modernized modules.

## 3. Stability & Reliability
- **[MUST]** Resolve ChromaDB conflict issues by hardening the persistence layer and adding better locking.
- **[MUST]** Fix JSON serialization issues for NumPy/Torch types in API responses.
- **[SHOULD]** Implement a robust health check system for all sub-services (Memory, Vision, MCP).

## 4. Optimization & Performance
- **[SHOULD]** Optimize vector search queries for lower latency.
- **[SHOULD]** Implement response streaming where applicable.
- **[COULD]** Add frontend caching for repeated memory queries.

## 5. Polish & UI/UX
- **[SHOULD]** Refine the "Thinking" UI to show the agent's reflection process more clearly.
- **[COULD]** Enhance visual feedback for emotional state changes.
