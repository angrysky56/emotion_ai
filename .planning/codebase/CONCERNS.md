# Concerns & Technical Debt - Emotion AI / Aura

## Technical Concerns

### 1. Dependency Complexity
- The project has a massive list of heavy dependencies (Torch, OpenCV, multiple AI SDKs, Chromadb). This makes the environment fragile and slow to build/update.
- Version pinning (e.g., `torch==2.7.0`) is strict, which may lead to conflicts with newer system libraries.

### 2. Database Integrity
- There are multiple scripts dedicated to fixing ChromaDB conflicts and recovering the database. This suggests underlying instability in how the vector DB handles concurrent access or state persistence.
- "Database Protection" logic exists but may need further hardening.

### 3. State Management
- The hybrid communication model (Frontend to Gemini vs. Frontend to Backend) could lead to state desynchronization if not carefully managed.
- The `AuraUIManager` in `index.tsx` is becoming a "God Object" that manages everything from DOM to API state.

### 4. Performance
- Real-time video processing and frequent vector searches could become a bottleneck on consumer-grade hardware.
- High memory usage is expected due to the nature of the models being loaded.

## Technical Debt
- **Frontend Framework**: The project is using a "Vanilla TypeScript" approach in a way that mimics a framework. As complexity grows, migrating to a formal framework like React or Next.js might be necessary for maintainability.
- **Error Handling**: While `auraApi.ts` has robust error handling, the backend logic occasionally relies on fallback implementations or broad warning logs.
- **Documentation**: Many files are complex (`main.py`, `index.tsx`) and would benefit from more granular modularization and internal documentation.

## Security
- API keys are managed via `.env` but exposed to the frontend build via Vite's `define`. Ensure that non-essential keys are not leaked in production bundles.
