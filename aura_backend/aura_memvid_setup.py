#!/usr/bin/env python3
"""
Aura + Memvid Integration Setup Script
Installs dependencies and sets up the hybrid memory system
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_command(
    cmd: list, check: bool = True, capture_output: bool = False
) -> Optional[str]:
    """Run a command and optionally capture output"""
    print(f"Running: {' '.join(cmd)}")

    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return result.stdout.strip()
    else:
        subprocess.run(cmd, check=check)
        return None


def check_dependencies():
    """Check if required dependencies are available"""
    print("🔍 Checking dependencies...")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False

    # Check if in virtual environment
    if not (
        hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    ):
        print("⚠️  Warning: Not in virtual environment")
        print("   Recommended: python -m venv venv && source venv/bin/activate")

    # Check for required system packages
    import importlib.util

    if importlib.util.find_spec("cv2") is not None:
        print("✅ OpenCV available")
    else:
        print("❌ OpenCV not available - will install")

    if importlib.util.find_spec("chromadb") is not None:
        print("✅ ChromaDB available")
    else:
        print("❌ ChromaDB not available - will install")

    return True


def install_memvid():
    """Install Memvid package"""
    print("📦 Installing Memvid...")

    # Try to install from the local repo first
    # Check for local memvid repo (optional, for development)
    memvid_repo = Path.cwd().parent / "memvid"

    if memvid_repo.exists():
        print(f"Installing from local repo: {memvid_repo}")
        run_command([sys.executable, "-m", "pip", "install", "-e", str(memvid_repo)])
    else:
        print("Installing from PyPI...")
        run_command([sys.executable, "-m", "pip", "install", "memvid"])

    # Install additional dependencies
    run_command(
        [sys.executable, "-m", "pip", "install", "pypdf", "ebooklib", "beautifulsoup4"]
    )


def install_aura_dependencies():
    """Install Aura-specific dependencies"""
    print("📦 Installing Aura dependencies...")

    dependencies = [
        "chromadb>=0.4.0",
        "fastapi>=0.115.0",
        "uvicorn",
        "google-generativeai",
        "sentence-transformers",
        "numpy",
        "scikit-learn",
        "python-dotenv",
        "pydantic",
    ]

    run_command([sys.executable, "-m", "pip", "install"] + dependencies)


def setup_project_structure(base_path: str):
    """Set up the project directory structure"""
    print("📁 Setting up project structure...")

    base = Path(base_path)
    directories = [
        "aura_data/active_memory",
        "aura_data/exports",
        "memvid_data/archives",
        "memvid_data/imports",
        "config",
        "logs",
    ]

    for directory in directories:
        dir_path = base / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {dir_path}")


def create_config_files(base_path: str):
    """Create configuration files"""
    print("⚙️ Creating configuration files...")

    base = Path(base_path)

    # Main configuration
    config = {
        "aura_memvid": {
            "active_memory_days": 30,
            "emotional_memory_retention": 90,
            "auto_archival": True,
            "archival_interval_days": 7,
            "max_active_memories": 10000,
        },
        "memvid": {
            "default_codec": "h265",
            "chunk_size": 512,
            "overlap": 50,
            "compression_quality": "high",
        },
        "aura": {
            "model": "gemini-2.5-flash-preview-05-20",
            "max_output_tokens": 8192,
            "enable_emotional_analysis": True,
            "enable_cognitive_tracking": True,
        },
    }

    config_path = base / "config" / "aura_memvid_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"✅ Created config: {config_path}")

    # Environment template
    env_template = """# Aura + Memvid Configuration
GOOGLE_API_KEY=your_api_key_here

# Aura Settings
AURA_DATA_DIRECTORY=./aura_data
AURA_MODEL=gemini-2.5-flash
AURA_MAX_OUTPUT_TOKENS=1000000

# Memvid Settings
MEMVID_DATA_DIRECTORY=./memvid_data
MEMVID_DEFAULT_CODEC=h265

# Server Settings
HOST=0.0.0.0
PORT=8000

# Features
ENABLE_EMOTIONAL_ANALYSIS=true
ENABLE_COGNITIVE_TRACKING=true
ENABLE_MEMVID_INTEGRATION=true
"""

    env_path = base / ".env.template"
    with open(env_path, "w") as f:
        f.write(env_template)
    print(f"✅ Created env template: {env_path}")


def copy_integration_files(base_path: str):
    """Copy integration files to the project"""
    print("📋 Setting up integration files...")

    base = Path(base_path)

    # Create the hybrid memory system file
    hybrid_file = base / "aura_memvid_hybrid.py"
    if not hybrid_file.exists():
        print(f"⚠️  Copy the hybrid system code to: {hybrid_file}")
        print("   (The code from the first artifact)")

    # Create MCP tools file
    mcp_tools_file = base / "aura_memvid_mcp_tools.py"
    if not mcp_tools_file.exists():
        print(f"⚠️  Copy the MCP tools code to: {mcp_tools_file}")
        print("   (The code from the second artifact)")


def create_example_scripts(base_path: str):
    """Create example usage scripts"""
    print("📝 Creating example scripts...")

    base = Path(base_path)

    # Basic example
    basic_example = '''#!/usr/bin/env python3
"""
Basic Aura + Memvid Example
Demonstrates core functionality
"""

import os
from pathlib import Path
from aura_memvid_hybrid import AuraMemvidHybrid

def main():
    # Initialize hybrid system
    memory_system = AuraMemvidHybrid()

    # Store a conversation with emotional context
    memory_id = memory_system.store_conversation(
        user_id="example_user",
        message="I'm feeling anxious about my upcoming presentation",
        response="I understand that presentations can feel overwhelming. Let's break down some strategies that might help you feel more confident.",
        emotional_state="anxiety",
        cognitive_focus="problem_solving"
    )

    print(f"Stored conversation: {memory_id}")

    # Search memory
    results = memory_system.unified_search(
        "presentation anxiety",
        "example_user"
    )

    print("Search results:")
    for result in results["active_memory"]:
        print(f"- {result['text'][:100]}...")

    # Import a knowledge base (example with a text file)
    # knowledge_file = Path("example_knowledge.txt")
    # if knowledge_file.exists():
    #     archive_result = memory_system.import_knowledge_base(
    #         str(knowledge_file),
    #         "example_knowledge"
    #     )
    #     print(f"Created knowledge archive: {archive_result}")

if __name__ == "__main__":
    main()
'''

    example_path = base / "example_basic.py"
    with open(example_path, "w") as f:
        f.write(basic_example)
    print(f"✅ Created: {example_path}")

    # MCP server example
    mcp_example = '''#!/usr/bin/env python3
"""
Aura + Memvid MCP Server Example
Start the enhanced MCP server
"""

import asyncio
import logging
from aura_memvid_hybrid import AuraMemvidHybrid
from aura_memvid_mcp_tools import create_aura_memvid_mcp_server

logging.basicConfig(level=logging.INFO)

async def main():
    # Create server and hybrid system
    server, hybrid_system = await create_aura_memvid_mcp_server()

    print("🚀 Starting Aura + Memvid MCP Server...")
    print("📡 Available tools:")

    tools = server.list_tools()
    for tool in tools:
        print(f"   - {tool.name}: {tool.description}")

    # Start server (this would typically be handled by the MCP runtime)
    print("✅ Server ready for MCP connections")

if __name__ == "__main__":
    asyncio.run(main())
'''

    mcp_path = base / "start_mcp_server.py"
    with open(mcp_path, "w") as f:
        f.write(mcp_example)
    print(f"✅ Created: {mcp_path}")


def create_integration_guide(base_path: str):
    """Create integration guide"""
    guide = """# Aura + Memvid Integration Guide

## Overview
This integration combines Aura's emotional intelligence with Memvid's revolutionary video-based memory storage.

## Architecture
- **Active Memory (ChromaDB)**: Recent conversations, emotional states, cognitive patterns
- **Archive Memory (Memvid)**: Compressed long-term storage in video format
- **Hybrid Search**: Unified search across both systems

## Quick Start

1. **Activate your environment**:
   ```bash
   source venv/bin/activate  # or conda activate your_env
   ```

2. **Set up your API key**:
   ```bash
   cp .env.template .env
   # Edit .env and add your Google API key
   ```

3. **Run basic example**:
   ```bash
   python example_basic.py
   ```

4. **Test MCP integration**:
   ```bash
   python start_mcp_server.py
   ```

## Key Features

### 1. Enhanced Memory Storage
```python
memory_system.store_conversation(
    user_id="user123",
    message="user message",
    response="aura response",
    emotional_state="happy",
    cognitive_focus="creativity"
)
```

### 2. Unified Search
```python
results = memory_system.unified_search("query", "user123")
# Returns both active and archived memories
```

### 3. Knowledge Import
```python
# Import PDFs/documents into compressed archives
memory_system.import_knowledge_base(
    "/path/to/documents",
    "knowledge_archive_name"
)
```

### 4. Automatic Archival
Old memories are automatically compressed into video archives for efficient storage.

## MCP Tools Available

1. `search_hybrid_memory` - Search across all memory systems
2. `store_enhanced_memory` - Store with emotional/cognitive context
3. `create_knowledge_archive` - Import documents to video archives
4. `archive_old_memories` - Compress old memories
5. `analyze_memory_patterns` - Analyze emotional/cognitive patterns
6. `get_memory_statistics` - System statistics and health

## Integration with Existing Aura

To integrate with your existing Aura system:

1. Copy the hybrid system files to your Aura backend directory
2. Modify your Aura MCP server to include Memvid tools
3. Update your conversation processing to use the hybrid storage
4. Configure automatic archival in your deployment

## Video Compression Benefits

- **10x storage reduction** compared to traditional vector databases
- **Sub-second search** across millions of text chunks
- **Offline-first** - no external database dependencies
- **Portable** - entire knowledge bases as MP4 files

## Troubleshooting

### Installation Issues
- Ensure Python 3.8+
- Use virtual environment
- Install system dependencies (opencv, ffmpeg for advanced codecs)

### Memory Issues
- Monitor active memory size
- Adjust archival thresholds
- Use more aggressive compression (h265)

### Search Performance
- Tune chunk sizes for your use case
- Balance active memory retention vs archive frequency
- Consider prefetching for predictable access patterns

## Next Steps

1. Experiment with different archival strategies
2. Tune compression settings for your storage needs
3. Integrate with your existing Aura UI
4. Set up automated monitoring and maintenance

For more information, see the source code and examples in this directory.
"""

    guide_path = Path(base_path) / "INTEGRATION_GUIDE.md"
    with open(guide_path, "w") as f:
        f.write(guide)
    print(f"✅ Created: {guide_path}")


def main():
    """Main setup function"""
    print("🚀 Aura + Memvid Integration Setup")
    print("=" * 50)

    # Get setup path
    aura_path = Path("/home/ty/Repositories/ai_workspace/emotion_ai")
    if not aura_path.exists():
        print(f"❌ Aura path not found: {aura_path}")
        aura_path = Path.cwd()
        print(f"Using current directory: {aura_path}")

    print(f"Setting up in: {aura_path}")

    # Setup steps
    if not check_dependencies():
        print("❌ Dependency check failed")
        return

    try:
        install_memvid()
        install_aura_dependencies()
        setup_project_structure(str(aura_path))
        create_config_files(str(aura_path))
        copy_integration_files(str(aura_path))
        create_example_scripts(str(aura_path))
        create_integration_guide(str(aura_path))

        print("\n✅ Setup Complete!")
        print("\nNext steps:")
        print(f"1. cd {aura_path}")
        print("2. Copy the integration code files (see artifacts)")
        print("3. cp .env.template .env")
        print("4. Edit .env with your Google API key")
        print("5. python example_basic.py")
        print("\nSee INTEGRATION_GUIDE.md for detailed instructions")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return


if __name__ == "__main__":
    main()
