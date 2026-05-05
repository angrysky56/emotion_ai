# Tech Stack - Emotion AI / Aura

## Frontend
- **Framework**: Vanilla TypeScript / React-style Components (Single Page Application)
- **Build Tool**: [Vite](https://vitejs.dev/) (v6.2.0)
- **Languages**: TypeScript (v5.7.2), HTML5, CSS3
- **AI SDK**: `@google/genai` (v0.8.0)
- **Utilities**: `marked` (Markdown parsing), `uuid`

## Backend
- **Language**: Python (>=3.12, actively using 3.13)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (v0.115.6)
- **Server**: Uvicorn (v0.34.0)
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **Data Handling**: Pydantic (v2.10.4), NumPy (v1.x), Pandas

## AI & Machine Learning
- **Models**: Google Gemini (1.5 Flash/Pro), Anthropic (Claude), OpenAI
- **Frameworks**: 
  - [FastMCP](https://github.com/jlowin/fastmcp) / [MCP SDK](https://modelcontextprotocol.io/)
  - [Torch](https://pytorch.org/) (v2.7.0)
  - [Sentence Transformers](https://www.sbert.net/) (v3.3.1)
  - [Memvid](https://github.com/memvid/memvid) (Video memory)
- **Computer Vision**: OpenCV, Pillow, PyZbar

## Data & Persistence
- **Vector Database**: [ChromaDB](https://www.trychroma.com/) (v0.5.23), FAISS (CPU/GPU)
- **Storage**: Local filesystem (`aura_data`, `memvid_data`), Firebase (debug logs)
- **Database Layer**: Robust Vector DB implementation

## Infrastructure
- **Containerization**: Docker, Docker Compose
- **DevOps**: Shell scripts for lifecycle management (`setup.sh`, `start_all.sh`, etc.)
- **Linting/Formatting**: [Trunk](https://trunk.io/) (Ruff, Black, Isort, Prettier, Shellcheck)
