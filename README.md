# Aura Backend - Advanced AI Companion

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![Vector DB](https://img.shields.io/badge/ChromaDB-latest-purple.svg)](https://chromadb.ai)
[![MCP](https://img.shields.io/badge/MCP-enabled-orange.svg)](https://modelcontextprotocol.io)

> **Sophisticated AI Companion with Vector Database, Emotional Intelligence, and Model Context Protocol Integration**

# Two WARNINGS and a disclaimer

- AI generated code

- Aura could be dangerous despite my attempted safeguards in a number of ways including but not limited to
  PC damage
  User mental health and attachment
  Emotional agentic activity

# User assumes all liability.

![alt text](image-4.png)

![alt text](image-1.png)

## 🌟 Features

### 🧠 Advanced Cognitive Architecture

- **ASEKE Framework**: Adaptive Socio-Emotional Knowledge Ecosystem
- **Real-time Emotional State Detection** with neurological correlations
- **Cognitive Focus Tracking** across different mental frameworks
- **Adaptive Self-Reflection** for continuous improvement
- **🆕 Thinking Extraction**: Transparent AI reasoning with thought analysis and cognitive transparency

### 🗄️ Intelligent Memory System

- **Vector Database Integration** with ChromaDB for semantic search
- **Persistent Conversation Memory** with embedding-based retrieval
- **Emotional Pattern Analysis** over time
- **Cognitive State Tracking** and trend analysis
- **MemVid AI QR code mp4 memory** Infinite MP4 based memory
- **Internal AI guided Memory Organization tools** Move information from short to long term memory systems to avoid bottlenecks and categorize chats

### 🔗 MCP Integration

- **Model Context Client** Utilizes the same MCP config JSON format as Claude Desktop- Use ANY tools!
- **Model Context Protocol Server** for external tool integration
- **Standardized AI Agent Communication** following MCP specifications
- **Tool Ecosystem Compatibility** with other MCP-enabled systems
- **Bidirectional Data Exchange** with external AI agents

### 📊 Advanced Analytics

- **Emotional Trend Analysis** with stability metrics
- **Cognitive Pattern Recognition** and optimization
- **Personalized Recommendations** based on interaction history
- **Data Export** in multiple formats (JSON, CSV, etc.)

### Data Flow

1. **User Input** → Frontend → FastAPI
2. **Processing** → Vector DB Search → Context Retrieval
3. **AI Processing** → Explicitly Selected Provider → Response Generation
4. **State Updates** → Emotional/Cognitive Analysis → Pattern Storage
5. **Memory Storage** → Vector DB → Persistent Learning
6. **External Access** → MCP Server → Tool Integration

## 🧠 AI Thinking & Reasoning Transparency

### Thinking Extraction Capabilities

- **Real-time Reasoning Capture**: Extract and analyze AI thought processes during conversations
- **Thought Summarization**: Automatic generation of reasoning summaries for quick understanding
- **Cognitive Transparency**: Full visibility into how Aura approaches problems and makes decisions
- **Reasoning Metrics**: Detailed analytics on thinking patterns, processing time, and cognitive load

### Thinking Configuration

- **Thinking Budget**: Configurable reasoning depth (1024-32768 tokens)
- **Response Integration**: Optional inclusion of reasoning in user responses
- **Pattern Analysis**: Long-term analysis of reasoning patterns and cognitive development
- **Performance Optimization**: Thinking efficiency metrics and optimization recommendations

## 🎭 Emotional Intelligence System

### Supported Emotions

- **Basic**: Normal, Happy, Sad, Angry, Excited, Fear, Disgust, Surprise
- **Complex**: Joy, Love, Peace, Creativity, DeepMeditation
- **Combined**: Hope (Anticipation + Joy), Optimism, Awe, Remorse
- **Social**: RomanticLove, PlatonicLove, ParentalLove, Friendliness

### Neurological Correlations

- **Brainwave Patterns**: Alpha, Beta, Gamma, Theta, Delta
- **Neurotransmitters**: Dopamine, Serotonin, Oxytocin, GABA, Norepinephrine
- **NTK Layers**: Neural Tensor Kernel mapping for emotional states

## 🧠 ASEKE Cognitive Framework

### Components

- **KS** (Knowledge Substrate): Shared conversational context
- **CE** (Cognitive Energy): Mental effort and focus allocation
- **IS** (Information Structures): Ideas and concept patterns
- **KI** (Knowledge Integration): Learning and connection processes
- **KP** (Knowledge Propagation): Information sharing mechanisms
- **ESA** (Emotional State Algorithms): Emotional influence on processing
- **SDA** (Sociobiological Drives): Social dynamics and trust factors

## 📊 Analytics & Insights

### Emotional Analysis

- **Stability Metrics**: Emotional consistency over time
- **Dominant Patterns**: Most frequent emotional states
- **Transition Analysis**: Emotional state changes and triggers
- **Intensity Tracking**: Emotional intensity distribution
- **Brainwave Correlation**: Neural activity pattern analysis

### Cognitive Tracking

- **Focus Patterns**: ASEKE component utilization
- **Learning Efficiency**: Knowledge integration rates
- **Context Switching**: Cognitive flexibility metrics
- **Attention Allocation**: Cognitive energy distribution

## 🚦 Performance-

# Responses take some time to process depending on tasks, any coder wants to see if they can speed up the processes I would be grateful.

### Optimization

- Vector database indexing for fast searches
- Async processing for concurrent requests
- **Cost-Free Local Embeddings**: Support for `Ollama` and `fastembed` (BGE/Gemma) to avoid API costs
- Autonomous sub-model background Focus gating and task processing for state updates and tool use
- Tool learning adapter
- [MemVid](https://github.com/Olow304/memvid) Infinite memory with modern `.mv2` single-file archival!

### Monitoring

- Health check endpoint
- Performance metrics collection
- Error tracking and reporting
- Resource usage monitoring

### MCP Client now fully functional!!! Memvid integration attempted- still testing.

I am not a coder so hopefully it sets up right if anyone tries it.

<!-- aura-startup:start -->
## Supported local startup

Aura is a private, single-user local application. It has no sign-in layer and
binds to `127.0.0.1` by default. Run these commands from the repository root.

### One-time dependency setup

Setup is an explicit operator action. The startup command and wrapper scripts do
not install, synchronize, or download software or models.

<!-- aura-setup-command -->
```bash
uv sync --locked
```

<!-- aura-setup-command -->
```bash
npm ci
```

Copy `.env.example` to `.env` only if you want to customize the local defaults.
The example selects Ollama and contains no credential. Gemini and OpenRouter are
optional cloud providers and require an explicit provider selection plus the
corresponding credential in your private environment.

### Preflight, then serve

<!-- aura-runtime-command -->
```bash
uv run --locked --no-sync python -m aura_backend.runtime preflight
```

Preflight is report-only. It checks Python, uv, Node, npm, both lock contracts,
provider configuration, the selected port and storage paths, the selected
provider service and selected model, and application readiness. The provider
rows are a bounded live provider check; they are not part of the offline test
suite. Preflight never installs dependencies, downloads a model, creates storage,
changes permissions, kills another process, or starts Aura.

The JSON status is one of `pass` (exit 0), `missing` (2), `failed` (3),
`blocked` (4), `not_run` (5), or `not_applicable` (6). Only a complete `pass`
licenses startup. Other results name a safe remediation code; perform any repair
explicitly and rerun preflight rather than treating a blocked check as readiness.

<!-- aura-runtime-command -->
```bash
uv run --locked --no-sync python -m aura_backend.runtime serve
```

`serve` runs preflight first, starts only the requested local child processes,
waits for the backend `/ready` response, and returns a nonzero status if startup
or a child fails. Ctrl+C/SIGTERM cleans up only processes and local provider
sessions owned by this invocation. Cancellation cannot guarantee stopped remote
compute or billing at a cloud provider.

The cross-platform launchers are thin delegates to these same commands:
`./start_full_system.sh` and `start_full_system.bat` run full serve;
`./aura_backend/start_api.sh` and `./aura_backend/start_frontend.sh` select one
side. `./aura_backend/start_mcp.sh` is a separate optional MCP delegate and is
not part of normal Aura readiness.

For normal private use, keep the loopback default. Passing a non-loopback
`--host` is explicit LAN exposure; the runtime warns that Aura has no sign-in.
Do not expose Aura directly to the internet.

Once serve reports readiness, the local UI is at <http://localhost:5173>, the
API at <http://localhost:8000>, and API documentation at
<http://localhost:8000/docs>. Environment-blocked and live-provider results are
evidence about that machine only, not proof that every provider or model works.
<!-- aura-startup:end -->

![alt text](image-5.png)

## 📡 API Endpoints

### Core API

- **Health Check**: `GET /health`
- **Process Conversation**: `POST /conversation`
- **Search Memories**: `POST /search`
- **Emotional Analysis**: `GET /emotional-analysis/{user_id}`
- **Export Data**: `POST /export/{user_id}`

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## 🔗 MCP Integration

### Available MCP Tools- Working on emotional state records, hopefully fixed tomorrow

1. **search_aura_memories**: Semantic search through conversation history
2. **analyze_aura_emotional_patterns**: Deep emotional trend analysis
3. **store_aura_conversation**: Add memories to Aura's knowledge base
4. **get_aura_user_profile**: Retrieve user personalization data
5. **export_aura_user_data**: Data export functionality
6. **query_aura_emotional_states**: Information about emotional intelligence system
7. **query_aura_aseke_framework**: ASEKE cognitive architecture details

### Connecting External Tools

To connect external MCP clients to Aura:

# Example MCP client configuration- for Claude or other clients to talk to Aura or use as a system.

Edit your directory path and place in claude desktop config json.

```bash
{
  "mcpServers": {
    "aura-companion": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend",
        "run",
        "aura_server.py"
      ]
    }
  }
}
```

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────┐
│                  Frontend                       │
│              (React/TypeScript)                 │
└─────────────────┬───────────────────────────────┘
                  │ HTTP/WebSocket
┌─────────────────▼───────────────────────────────┐
│                FastAPI                          │
│             (REST API Layer)                    │
├─────────────────┬───────────────────────────────┤
│                 │                               │
│  ┌──────────────▼─────────────┐                │
│  │     Vector Database        │                │
│  │       (ChromaDB)           │                │
│  │                            │                │
│  │ • Conversation Memory      │                │
│  │ • Emotional Patterns       │                │
│  │ • Cognitive States         │                │
│  │ • Knowledge Substrate      │                │
│  └────────────────────────────┘                │
│                                                 │
│  ┌────────────────────────────┐                │
│  │     State Manager          │                │
│  │                            │                │
│  │ • Emotional Transitions    │                │
│  │ • Cognitive Focus Changes  │                │
│  │ • Automated DB Operations  │                │
│  │ • Pattern Recognition      │                │
│  └────────────────────────────┘                │
│                                                 │
│  ┌────────────────────────────┐                │
│  │     File System            │                │
│  │                            │                │
│  │ • User Profiles            │                │
│  │ • Data Exports             │                │
│  │ • Session Storage          │                │
│  │ • Backup Management        │                │
│  └────────────────────────────┘                │
└─────────────────┬───────────────────────────────┘
                  │ MCP Protocol
┌─────────────────▼───────────────────────────────┐
│              MCP Server                         │
│         (External Tool Access)                 │
│                                                 │
│ • Memory Search Tools                           │
│ • Emotional Analysis Tools                      │
│ • Data Export Tools                             │
│ • ASEKE Framework Access                        │
└─────────────────────────────────────────────────┘
```

## 🧪 Testing

### Health Check (Working)

```bash
curl http://localhost:8000/health
```

### Thinking Functionality Tests (New!)

```bash
# Test thinking extraction capabilities
cd aura_backend
python test_thinking.py

# Interactive thinking demonstration
python thinking_demo.py

# Check thinking system status
curl http://localhost:8000/thinking-status
```

### Unit Tests

```bash
pytest tests/
```

### Integration Tests

```bash
./test_setup.py
```

### Load Testing

```bash
# Example using wrk
wrk -t12 -c400 -d30s http://localhost:8000/health
```

### Local Development

I apologize for the mess, I do not know if any of this works below but feel free to try if you are brave or know what you are doing.

### Production (Docker)

```bash
# Build image
docker build -t aura-backend .

# Run container
docker run -p 8000:8000 -v ./aura_data:/app/aura_data aura-backend
```

### Systemd Service

```bash
# Copy service file
sudo cp aura-backend.service /etc/systemd/system/

# Enable and start
sudo systemctl enable aura-backend
sudo systemctl start aura-backend
```

## 🤝 Integration with Frontend

### API Endpoints to Update

Update your frontend to use these endpoints:

```typescript
const API_BASE = "http://localhost:8000";

// Replace localStorage with API calls
const response = await fetch(`${API_BASE}/conversation`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    user_id: userId,
    message: userMessage,
    session_id: sessionId,
  }),
});
```

### WebSocket Support (Future)

Real-time updates and streaming responses will be available via WebSocket connections.

## 📚 Advanced Usage

### Custom MCP Tools

Create custom MCP tools by extending the `mcp_server.py`:

```python
@tool
async def custom_aura_tool(params: CustomParams) -> Dict[str, Any]:
    """Your custom tool implementation"""
    # Implementation here
    pass
```

### Vector Database Queries

Direct vector database access for advanced queries:

```python
from main import vector_db
results = await vector_db.search_conversations(
    query="emotional support",
    user_id="user123",
    n_results=10
)
```

![alt text](image-3.png)

## 🐛 Troubleshooting

Use the safe remediation codes in the
[startup guide](aura_backend/STARTUP_GUIDE.md#troubleshooting-boundaries).
Aura never kills an unknown process, deletes a database, prints a credential, or
rebuilds an environment as part of troubleshooting. Storage diagnosis and repair
remain preservation-gated work; make a verified backup before any manual change.

### Logs

Check logs in:

- Console output during development
- System logs: `journalctl -u aura-backend` (if using systemd)
- Application logs: `./aura_data/logs/`

## 🔒 Security- WARNING! AI Generated so I have 0 trust in these features

### Data Protection

- All user data stored locally
- Local Ollama keeps model traffic local; explicitly selected cloud providers
  transmit requests under their own terms
- Vector embeddings are anonymized
- Session data encrypted in transit

### Access Control

- No sign-in or API authentication; keep the default loopback boundary
- Rate limiting enabled
- CORS configuration
- Input validation and sanitization

## 🛣️ Roadmap

### Upcoming Features

- [ ] Real-time WebSocket connections
- [ ] Advanced emotion prediction models
- [ ] Multi-user collaboration features
- [ ] Enhanced MCP tool ecosystem
- [ ] Mobile app backend support
- [ ] Advanced analytics dashboard
- [ ] Integration with external AI models

### Long-term Vision

- Multi-modal interaction (voice, video, text)
- Federated learning across Aura instances
- Advanced personality adaptation
- Enterprise deployment options
- Open-source community ecosystem

## 📄 License

My stuff is MIT I suppose but there is other software like google-genai and memvid so it is a mixed bag I think
ie don't steal my ideas and try to make money, without me. lol but I am super poor.

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests for review.

## 📞 Support

For issues and support:

1. Check troubleshooting section
2. Review logs and error messages
3. Create detailed issue reports
4. Join community discussions

---

**Aura Emotion AI** - _Powering the future of AI companionship and assistance through advanced emotional intelligence and sophisticated memory systems._
