# Project Context: Aura Modernization

## Mission
Aura is an **Advanced Reflective Companion** built on a unique **Reflective Agent Architecture (RAA)** and the **ASEKE Framework**. The goal of this modernization phase is to transform a "sloppy" legacy codebase into a high-performance, stable, and cutting-edge Emotion AI system using modern LLM providers and coding best practices.

## Core Vision
- **Emotionally Intelligent**: Deep analysis of user states and cognitive patterns.
- **Persistent Memory**: Semantic long-term memory via ChromaDB and Visual Memory via Memvid.
- **Reflective Reasoning**: A "Thinking Processor" that allows the agent to self-correct and plan before responding.
- **Modern Infrastructure**: Leveraging OpenRouter (Primary) and Ollama (Secondary) for model agnostic flexibility.

## Current State & Challenges
- **Technical Debt**: Legacy spaghetti code, outdated dependencies, and instability.
- **Complexity**: Unique hybrid architecture (Frontend direct-to-AI + Backend services) that needs refinement.
- **Memory Integrity**: Known instability in the vector database and inter-process handling.

## Modernization Strategy
1. **Provider Shift**: Migrate core LLM logic to OpenRouter (Primary) and Ollama (Local/Secondary).
2. **Structural Refinement**: Modularize the monolithic backend and polish the "Vanilla TS" frontend.
3. **Dependency Hardening**: Update to latest stable versions of Torch, ChromaDB, and FastAPI.
4. **Stability Fixes**: Resolve database conflicts and inter-process locking issues.
5. **Optimization**: Improve performance of vector searches and real-time processing.
