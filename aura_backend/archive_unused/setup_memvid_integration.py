#!/usr/bin/env python3
"""
Setup script for Aura + Memvid Integration
Works with UV environment and existing Aura setup
"""

import subprocess
from pathlib import Path

def run_uv_command(args: list, cwd: str | None = None) -> bool:
    """Run UV command safely"""
    try:
        cmd = ["uv"] + args
        print(f"🔧 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ UV not found. Please install UV first!")
        return False

def install_memvid_deps():
    """Install memvid and related dependencies"""
    print("📦 Installing Memvid dependencies...")

    aura_backend = Path("/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend")
    memvid_repo = Path("/home/ty/Repositories/memvid")

    # Dependencies to add
    deps = [
        "opencv-python",
        "qrcode[pil]",
        "faiss-cpu",
        "pypdf",
        "ebooklib",
        "beautifulsoup4"
    ]

    # Install memvid from local repo if available
    if memvid_repo.exists():
        print(f"📦 Installing memvid from local repo: {memvid_repo}")
        success = run_uv_command(["add", "--editable", str(memvid_repo)], cwd=str(aura_backend))
        if not success:
            print("⚠️  Local install failed, trying PyPI...")
            run_uv_command(["add", "memvid"], cwd=str(aura_backend))
    else:
        print("📦 Installing memvid from PyPI...")
        run_uv_command(["add", "memvid"], cwd=str(aura_backend))

    # Install additional dependencies
    for dep in deps:
        print(f"📦 Adding {dep}...")
        run_uv_command(["add", dep], cwd=str(aura_backend))

    return True

def create_memvid_mcp_tools():
    """Create enhanced MCP tools for memvid integration"""
    print("🔧 Creating Memvid MCP tools...")

    tools_code = '''"""
Enhanced Aura MCP Tools with Memvid Integration
"""

from fastmcp import FastMCP
import mcp.types as types
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import logging

# Import the hybrid system
from aura_memvid_hybrid import AuraMemvidHybrid

logger = logging.getLogger(__name__)

class MemvidSearchParams(BaseModel):
    query: str
    user_id: str
    max_results: int = 10

class MemvidArchiveParams(BaseModel):
    archive_name: Optional[str] = None

class KnowledgeImportParams(BaseModel):
    source_path: str
    archive_name: str

# Global hybrid system instance
_hybrid_system = None

def get_hybrid_system():
    """Get or create the hybrid system instance"""
    global _hybrid_system
    if _hybrid_system is None:
        _hybrid_system = AuraMemvidHybrid()
    return _hybrid_system

def add_memvid_tools(mcp_server):
    """Add memvid tools to existing MCP server"""

    @mcp_server.tool()
    async def search_hybrid_memory(params: MemvidSearchParams) -> types.CallToolResult:
        """
        Search across both active ChromaDB memory and Memvid archives
        """
        try:
            hybrid_system = get_hybrid_system()
            results = hybrid_system.unified_search(
                query=params.query,
                user_id=params.user_id,
                max_results=params.max_results
            )

            response_data = {
                "status": "success",
                "results": results
            }

            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )

        except Exception as e:
            logger.error("Error in hybrid memory search: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2)
                )],
                isError=True
            )

    @mcp_server.tool()
    async def archive_old_memories(params: MemvidArchiveParams) -> types.CallToolResult:
        """
        Archive old conversations to compressed Memvid format
        """
        try:
            hybrid_system = get_hybrid_system()
            result = hybrid_system.archive_old_memories(params.archive_name)

            response_data = {
                "status": "success",
                "archival_result": result
            }

            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )

        except Exception as e:
            logger.error("Error archiving memories: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2)
                )],
                isError=True
            )

    @mcp_server.tool()
    async def import_knowledge_base(params: KnowledgeImportParams) -> types.CallToolResult:
        """
        Import documents/PDFs into compressed Memvid archives
        """
        try:
            hybrid_system = get_hybrid_system()
            result = hybrid_system.import_knowledge_base(
                params.source_path,
                params.archive_name
            )

            response_data = {
                "status": "success",
                "import_result": result
            }

            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )

        except Exception as e:
            logger.error("Error importing knowledge: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2)
                )],
                isError=True
            )

    @mcp_server.tool()
    async def get_hybrid_system_stats() -> types.CallToolResult:
        """
        Get hybrid memory system statistics
        """
        try:
            hybrid_system = get_hybrid_system()
            stats = hybrid_system.get_system_stats()

            response_data = {
                "status": "success",
                "stats": stats
            }

            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2, default=str)
                )]
            )

        except Exception as e:
            logger.error("Error getting stats: %s", e)
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=json.dumps({"status": "error", "error": str(e)}, indent=2)
                )],
                isError=True
            )

    logger.info("✅ Added Memvid tools to Aura MCP server")
'''

    tools_file = Path("/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend/aura_memvid_mcp_tools.py")
    with open(tools_file, 'w') as f:
        f.write(tools_code)

    print(f"✅ Created: {tools_file}")

def create_test_script():
    """Create test script for the integration"""
    print("📝 Creating test script...")

    test_code = '''#!/usr/bin/env python3
"""
Test Aura + Memvid Integration
"""

import asyncio
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_memvid_integration():
    """Test the memvid integration"""
    print("🧪 Testing Aura + Memvid Integration")
    print("=" * 50)

    try:
        # Test memvid import
        try:
            from memvid import MemvidEncoder, MemvidRetriever
            print("✅ Memvid import successful")
        except ImportError as e:
            print(f"❌ Memvid import failed: {e}")
            return False

        # Test hybrid system import
        try:
            from aura_memvid_hybrid import AuraMemvidHybrid
            print("✅ Hybrid system import successful")
        except ImportError as e:
            print(f"❌ Hybrid system import failed: {e}")
            return False

        # Initialize hybrid system
        try:
            hybrid = AuraMemvidHybrid()
            print("✅ Hybrid system initialization successful")
        except Exception as e:
            print(f"❌ Hybrid system initialization failed: {e}")
            return False

        # Test system stats
        try:
            stats = hybrid.get_system_stats()
            print(f"✅ System stats: {stats}")
        except Exception as e:
            print(f"❌ System stats failed: {e}")
            return False

        # Test conversation storage
        try:
            memory_id = hybrid.store_conversation(
                user_id="test_user",
                message="Hello, this is a test message",
                response="Hello! This is Aura's test response",
                emotional_state="Happy",
                cognitive_focus="Learning"
            )
            print(f"✅ Conversation storage successful: {memory_id}")
        except Exception as e:
            print(f"❌ Conversation storage failed: {e}")
            return False

        # Test unified search
        try:
            results = hybrid.unified_search("test", "test_user")
            print(f"✅ Unified search successful: {results['total_results']} results")
        except Exception as e:
            print(f"❌ Unified search failed: {e}")
            return False

        # Test MCP tools import
        try:
            from aura_memvid_mcp_tools import add_memvid_tools
            print("✅ MCP tools import successful")
        except ImportError as e:
            print(f"❌ MCP tools import failed: {e}")
            return False

        print("\\n🎉 All tests passed! Integration is ready.")
        return True

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_memvid_integration())
'''

    test_file = Path("/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend/test_memvid_integration.py")
    with open(test_file, 'w') as f:
        f.write(test_code)

    print(f"✅ Created: {test_file}")

def create_server_patch():
    """Create a patch to add memvid tools to the existing aura_server.py"""
    print("📋 Creating server integration patch...")

    patch_code = '''"""
Patch to add Memvid tools to existing aura_server.py

Add these lines to your aura_server.py after the MCP server is created:

# Add at the top with other imports:
try:
    from aura_memvid_mcp_tools import add_memvid_tools
    MEMVID_AVAILABLE = True
except ImportError:
    MEMVID_AVAILABLE = False
    logger.warning("Memvid tools not available")

# Add after creating the MCP server (after mcp = FastMCP(...)):
if MEMVID_AVAILABLE:
    add_memvid_tools(mcp)
    logger.info("✅ Added Memvid tools to MCP server")

That's it! This will add the new tools without breaking existing functionality.
"""
'''

    patch_file = Path("/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend/server_integration_patch.txt")
    with open(patch_file, 'w') as f:
        f.write(patch_code)

    print(f"✅ Created: {patch_file}")

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")

    base_path = Path("/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend")

    directories = [
        "memvid_data",
        "memvid_data/archives",
        "memvid_data/imports"
    ]

    for directory in directories:
        dir_path = base_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {dir_path}")

def main():
    """Main setup function"""
    print("🚀 Setting up Aura + Memvid Integration")
    print("=" * 50)

    try:
        # Install dependencies
        if not install_memvid_deps():
            print("❌ Failed to install dependencies")
            return False

        # Create directories
        create_directories()

        # Create files
        create_memvid_mcp_tools()
        create_test_script()
        create_server_patch()

        print("\n✅ Setup Complete!")
        print("\nNext steps:")
        print("1. Test the integration:")
        print("   cd /home/ty/Repositories/ai_workspace/emotion_ai/aura_backend")
        print("   uv run test_memvid_integration.py")
        print()
        print("2. Add Memvid tools to your aura_server.py:")
        print("   See server_integration_patch.txt for instructions")
        print()
        print("3. Start your enhanced Aura server:")
        print("   uv run aura_server.py")
        print()
        print("🎉 Your Aura system now has revolutionary video-based memory!")

        return True

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

if __name__ == "__main__":
    main()
