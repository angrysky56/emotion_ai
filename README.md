# Aura Backend - Advanced AI Companion

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![uv](https://img.shields.io/badge/uv-Python%20Packager-green.svg)](https://github.com/astral-sh/uv)
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
3. **AI Processing** → Gemini API → Response Generation
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
- Cost and Memory-efficient local all-minilm vector embedding generation
- Autonomous sub-model background Focus gating and task processing for state updates and tool use
- Tool learning adapter
- [MemVid](https://github.com/Olow304/memvid) infinite QR code video long term memory!

### Monitoring
- Health check endpoint
- Performance metrics collection
- Error tracking and reporting
- Resource usage monitoring

### MCP Client now fully functional!!! Memvid integration attempted- still testing.

 I am not a coder so hopefully it sets up right if anyone tries it.

## 🚀 Quick Start with Aura

This section guides you through setting up and running Aura with a single command.

### Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.12+**: Required for the backend.
  - Verify with: `python3 --version`
- **uv**: A fast Python package installer and resolver, used for managing the backend environment and dependencies.
  - Installation: `pip install uv` or `pipx install uv`. See [uv documentation](https://github.com/astral-sh/uv) for more options.
  - Verify with: `uv --version`
- **Node.js**: Required for the frontend. (LTS version recommended)
  - This typically includes `npm` (Node Package Manager).
  - Verify with: `node --version` and `npm --version`
- **Git**: For cloning the repository.
- **Google API Key**: From [Google AI Studio](https://aistudio.google.com/app/apikey) for Gemini model access. The `setup_aura.sh` script will prompt you for this for the backend.
  - *For the frontend*: You will also need to configure this key. See `Frontend-README.md` for instructions on creating a `.env.local` file in the project root with `VITE_GOOGLE_API_KEY=your_key_here`.
- **System Resources**:
  - At least 4GB RAM (recommended for vector embeddings and model operations).
  - 2GB+ free storage space.

### Installation & Setup

1.  **Clone the Repository**:
    If you haven't already, clone the Aura repository to your local machine:
    ```bash
    git clone https://github.com/USERNAME/REPOSITORY_NAME.git # Replace with the actual repository URL
    cd REPOSITORY_NAME # Or your repository's root folder name
    ```

2.  **Run the Automated Setup Script**:
    Execute the `setup_aura.sh` script located in the project root. This script will:
    - Check for all prerequisites.
    - Set up the Python virtual environment for the backend using `uv`.
    - Install all backend Python dependencies.
    - Guide you through configuring your `GOOGLE_API_KEY`.
    - Install frontend Node.js dependencies using `npm`.

    ```bash
    chmod +x setup_aura.sh
    ./setup_aura.sh
    ```
    Follow any on-screen prompts, especially for providing your Google API Key.

### Starting Aura

Once the setup script completes successfully:

1.  **Navigate to the Backend Directory and Activate Environment**:
    The Python virtual environment must be active to run the backend.
    ```bash
    cd aura_backend
    source .venv/bin/activate
    ```
    *Note: You'll need to do this every time you open a new terminal session to work with the backend.*

2.  **Start the Services**:
    The `start.sh` script in the `aura_backend` directory is used to launch the application.

    -   **To start both backend and frontend (recommended for development)**:
        ```bash
        ./start.sh --with-frontend
        ```
        This will:
        - Start the Aura FastAPI backend server.
        - Start the frontend development server (`npm run dev`).

    -   **To start only the backend API server**:
        ```bash
        ./start.sh
        ```

3.  **Access Aura**:
    -   **Backend API**: `http://localhost:8000`
    -   **Interactive API Docs (Swagger UI)**: `http://localhost:8000/docs`
    -   **Frontend UI** (if started with `--with-frontend`): `http://localhost:5173`

    Open these URLs in your web browser.

### Stopping Aura

-   Press `Ctrl+C` in the terminal where `start.sh` is running to stop all services launched by it.
-   If you started services separately, stop them individually using `Ctrl+C`.
-   To deactivate the Python virtual environment:
    ```bash
    deactivate
    ```


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
        "run",
        "--cwd",
        "/path/to/your/cloned_repository/aura_backend", # Adjust this path
        "aura_as_mcp_server.py" # Assuming aura_as_mcp_server.py is the entry point for MCP
      ]
    }
  }
}
```
*Note: The exact command and arguments for running the MCP server might vary. The `aura_as_mcp_server.py` script seems like a plausible candidate for an MCP server entry point. Adjust the path and script name as per your actual setup.*

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

### Systemd Service (Example - Outdated)
The following shows an example of how one might set up a systemd service. However, the specific `aura-backend.service` file previously included in `docs/archive/` has been removed as it was potentially outdated. If you need to run Aura as a systemd service, you will need to create a suitable service file for your environment.
```bash
# Example steps (you would need to create your own aura-backend.service file):
# sudo cp your-aura-backend.service /etc/systemd/system/
# sudo systemctl enable your-aura-backend
# sudo systemctl start your-aura-backend
```

## 🤝 Integration with Frontend

### API Endpoints to Update
Update your frontend to use these endpoints:

```typescript
const API_BASE = 'http://localhost:8000';

// Replace localStorage with API calls
const response = await fetch(`${API_BASE}/conversation`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: userId,
    message: userMessage,
    session_id: sessionId
  })
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

### Common Issues

1. **API Key Issues**:
   ```bash
   # Check environment
   source venv/bin/activate
   echo $GOOGLE_API_KEY
   ```

3. **Vector DB Issues**: If you encounter problems with the vector database, or wish to start with a clean slate:
   ```bash
   # Reset database (deletes existing ChromaDB data in the backend directory)
   rm -rf aura_backend/aura_chroma_db/
   # Then, re-initialize. For example, if test_setup.py handles this:
   # cd aura_backend && python tests/test_setup.py # Adjust path/command as needed
   ```
   *Note: Ensure you understand what data will be lost before running `rm -rf`.*

4. **Memory Issues**:
   - Increase system memory allocation
   - Reduce vector embedding batch sizes
   - Use lightweight embedding models

### Logs
Check logs in:
- Console output during development
- System logs: `journalctl -u aura-backend` (if using systemd)
- Application logs: `./aura_data/logs/`

## 🔒 Security- WARNING! AI Generated so I have 0 trust in these features

### Data Protection
- All user data stored locally
- No external data transmission (except Google API)
- Vector embeddings are anonymized
- Session data encrypted in transit

### Access Control
- API key authentication
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

This project is primarily licensed under the MIT License. (It's recommended to add a `LICENSE` file to the repository with the full text of the MIT License).

Please be aware that some dependencies included in this project have their own licenses that must be respected:
- `google-generativeai` is typically licensed under the Apache 2.0 License.
- Other third-party libraries will have their own respective licenses.

If components from other projects like MemVid are integrated, their specific licenses would also apply to those parts.

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines and submit pull requests for review.

## 📞 Support

For issues and support:
1. Check troubleshooting section
2. Review logs and error messages
3. Create detailed issue reports
4. Join community discussions

---

**Aura Emotion AI** - *Powering the future of AI companionship and assistance through advanced emotional intelligence and sophisticated memory systems.*
