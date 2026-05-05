# Architecture - Emotion AI / Aura

## High-Level Overview
Aura is built on a **Reflective Agent Architecture (RAA)** designed for adaptive, emotional AI companionship. It combines real-time sensory input (vision, audio) with deep semantic memory and cognitive reflection.

## Key Architectural Components

### 1. Reflective Agent Architecture (RAA)
- **Thinking Processor**: A central component that handles complex reasoning, planning, and self-correction. It orchestrates between direct responses and "thinking" phases.
- **ASEKE Framework**: Adaptive Semantic Emotional Knowledge Engine. This framework governs how emotional states are processed and how they influence the agent's behavior and memory.

### 2. Hybrid Communication Model
- **Direct Client-to-AI**: The frontend can communicate directly with Google Gemini for low-latency tasks.
- **Agentic Backend**: The frontend uses `AuraAPI` to interact with the Python backend for heavy-duty tasks:
    - Long-term memory retrieval.
    - Emotional analysis.
    - Video archival and search.
    - Complex tool execution.

### 3. Intelligent Memory Management
- **Semantic Memory**: Uses ChromaDB to store vector embeddings of past conversations and experiences.
- **Video Memory (Memvid)**: Manages video recordings, allowing the agent to "remember" visual interactions.
- **Memory Manager**: `aura_intelligent_memory_manager.py` handles the lifecycle of memories, including importance ranking and archival.

### 4. MCP Ecosystem
- The system treats tools as first-class citizens using the Model Context Protocol. This allows for a modular and extensible capability set where tools can be added or updated without changing the core agent logic.

## Data Flow
1. **Input**: User message (text) or sensor data (video/audio).
2. **Analysis**: Real-time emotional and cognitive state extraction.
3. **Retrieval**: Semantic memory search for relevant context.
4. **Reflection**: Thinking processor evaluates the goal and context.
5. **Execution**: Tool calls (MCP) or direct response generation.
6. **Persistence**: New interaction is embedded and saved to long-term memory.
