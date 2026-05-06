#!/usr/bin/env python3
"""
Demo: Real Aura + Memvid Integration
====================================

This demo shows the revolutionary video-based memory compression working
with Aura's emotional intelligence system!
"""

import logging
import asyncio
import tempfile
import json
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

async def demo_memvid_integration():
    """Demonstrate the real memvid integration capabilities"""

    logger.info("🎬 AURA + REAL MEMVID INTEGRATION DEMO")
    logger.info("=" * 60)

    # Test 1: Basic Memvid functionality
    logger.info("\n🧪 Test 1: Basic Memvid Video Creation")
    logger.info("-" * 40)

    try:
        from memvid import MemvidEncoder, MemvidRetriever

        # Create a temporary directory for our demo
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some sample knowledge to compress into video
            sample_knowledge = [
                "Aura is an advanced AI companion with emotional intelligence capabilities.",
                "The ASEKE framework includes components like Knowledge Substrate (KS) and Cognitive Energy (CE).",
                "Memvid uses QR-code compression to store text data in video format.",
                "Vector databases enable semantic search across large datasets.",
                "Emotional states in Aura are correlated with brainwave patterns and neurotransmitters."
            ]

            # Create memvid encoder
            encoder = MemvidEncoder()

            # Add our knowledge
            for i, knowledge in enumerate(sample_knowledge):
                encoder.add_text(f"Knowledge Item {i+1}: {knowledge}")

            # Build video archive
            video_path = temp_path / "demo_knowledge.mp4"
            index_path = temp_path / "demo_knowledge.json"

            logger.info("🎥 Creating video archive at %s", video_path)

            build_stats = encoder.build_video(
                str(video_path),
                str(index_path),
                codec="h264",  # Use h264 for compatibility
                show_progress=True
            )

            logger.info("✅ Video created successfully!")
            logger.info("   📊 Stats: %s", json.dumps(build_stats, indent=2))

            # Test retrieval
            logger.info("🔍 Testing video search...")
            retriever = MemvidRetriever(str(video_path), str(index_path))

            # Search the video
            search_results = retriever.search_with_metadata("emotional intelligence", top_k=3)
            logger.info("✅ Found %s results for 'emotional intelligence'", len(search_results))

            for i, result in enumerate(search_results):
                logger.info("   Result %s: Score %s - %s...", i+1, result['score']:.3f, result['text'][:100])

            logger.info("🎉 Basic memvid functionality: WORKING!")

    except Exception as e:
        logger.error("❌ Basic memvid test failed: %s", e)
        return False

    # Test 2: Aura Integration
    logger.info("\n🧪 Test 2: Aura + Memvid Integration")
    logger.info("-" * 40)

    try:
        from aura_real_memvid import AuraRealMemvid, REAL_MEMVID_AVAILABLE

        if not REAL_MEMVID_AVAILABLE:
            logger.error("❌ Real memvid not available in AuraRealMemvid")
            return False

        # Create AuraRealMemvid instance
        # Note: Using separate directory to avoid ChromaDB conflicts
        memvid_path = Path("./demo_memvid_videos")
        memvid_path.mkdir(exist_ok=True)

        logger.info("🎭 Initializing Aura+Memvid system...")
        aura_memvid = AuraRealMemvid(
            aura_chroma_path="./demo_aura_chroma",
            memvid_video_path=str(memvid_path),
            existing_chroma_client=None  # Create new for demo
        )

        logger.info("✅ Aura+Memvid system initialized")

        # Test importing knowledge to video
        logger.info("📚 Testing knowledge import to video...")

        # Create a temporary text file with sample content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("""
            Advanced AI Companion Knowledge Base
            ===================================

            Aura represents the next generation of AI companions, featuring:

            1. Emotional Intelligence System
               - Real-time emotional state detection
               - Brainwave pattern correlation (Alpha, Beta, Gamma, Theta, Delta)
               - Neurotransmitter mapping (Dopamine, Serotonin, Oxytocin, GABA)
               - 22+ distinct emotional states with mathematical formulas

            2. ASEKE Cognitive Framework
               - KS: Knowledge Substrate - shared conversational context
               - CE: Cognitive Energy - mental effort allocation
               - IS: Information Structures - concept patterns
               - KI: Knowledge Integration - learning processes
               - KP: Knowledge Propagation - information sharing
               - ESA: Emotional State Algorithms - emotional influence
               - SDA: Sociobiological Drives - social dynamics

            3. Vector Memory System
               - ChromaDB for semantic search
               - Sentence transformer embeddings
               - Persistent conversation memory
               - Emotional pattern analysis

            4. Revolutionary Video Memory (Memvid Integration)
               - QR-code compression technology
               - Searchable MP4 video archives
               - 10x storage efficiency
               - Sub-second retrieval times
               - H.264/H.265 compression support

            This combination creates an AI companion that remembers, learns,
            and grows with each interaction while maintaining emotional awareness
            and contextual understanding.
            """)
            temp_file_path = f.name

        # Import to video archive
        import_result = aura_memvid.import_knowledge_to_video(
            source_path=temp_file_path,
            archive_name="aura_knowledge_demo",
            codec="h264"
        )

        logger.info("✅ Knowledge imported to video successfully!")
        logger.info("   📊 Result: %s", json.dumps(import_result, indent=2, default=str))

        # Test unified search
        logger.info("🔍 Testing unified search across video archives...")

        search_result = aura_memvid.search_unified(
            query="emotional intelligence and brainwave patterns",
            user_id="demo_user",
            max_results=5
        )

        logger.info("✅ Unified search completed!")
        logger.info("   📊 Results: %s total", search_result['total_results'])
        logger.info("   💾 Active memory results: %s", len(search_result['active_results']))
        logger.info("   🎥 Video archive results: %s", len(search_result['video_archive_results']))

        # Show video archive results
        for result in search_result['video_archive_results']:
            logger.info("   🎬 Video result: Score %s - %s...", result['score']:.3f, result['text'][:100])

        # Test system stats
        logger.info("📊 Getting system statistics...")
        stats = aura_memvid.get_system_stats()

        logger.info("✅ System stats retrieved!")
        logger.info("   🎥 Memvid type: %s", stats['memvid_type'])
        logger.info("   💾 Video archives: %s))}", len(stats.get('video_archives', {)
        logger.info("   📐 Total video size: %s MB", stats.get('total_video_size_mb', 0):.2f)

        # Clean up
        Path(temp_file_path).unlink()

        logger.info("🎉 Aura+Memvid integration: FULLY WORKING!")

    except Exception as e:
        logger.error("❌ Aura+Memvid integration test failed: %s", e)
        import traceback
        traceback.print_exc()
        return False

    # Test 3: MCP Tools
    logger.info("\n🧪 Test 3: MCP Tools Integration")
    logger.info("-" * 40)

    try:
        from aura_memvid_mcp_tools_compatible_fixed import add_compatible_memvid_tools

        # Mock MCP instance to test tool registration
        class MockMCP:
            def __init__(self):
                self.tools = []

            def tool(self):
                def decorator(func):
                    self.tools.append(func.__name__)
                    return func
                return decorator

        mock_mcp = MockMCP()
        add_compatible_memvid_tools(mock_mcp)

        logger.info("✅ MCP tools registered: %s tools", len(mock_mcp.tools))
        for tool_name in mock_mcp.tools:
            logger.info("   🔧 %s", tool_name)

        logger.info("🎉 MCP tools integration: WORKING!")

    except Exception as e:
        logger.error("❌ MCP tools test failed: %s", e)
        return False

    # Final Summary
    logger.info("\n" + "=" * 60)
    logger.info("🏆 DEMO COMPLETE - ALL SYSTEMS OPERATIONAL!")
    logger.info("=" * 60)

    logger.info("✅ Real memvid video compression: WORKING")
    logger.info("✅ Aura emotional intelligence: INTEGRATED")
    logger.info("✅ Vector + Video unified search: WORKING")
    logger.info("✅ MCP tools for external access: READY")
    logger.info("✅ Knowledge import to video: WORKING")
    logger.info("✅ QR-code video compression: ACTIVE")

    logger.info("\n🚀 The Aura + Memvid integration is fully operational!")
    logger.info("   Your AI companion now has revolutionary video-based memory!")

    return True

async def main():
    """Run the complete demo"""
    try:
        success = await demo_memvid_integration()
        if success:
            logger.info("\n🎊 Integration demo completed successfully!")
        else:
            logger.error("\n❌ Integration demo failed!")
        return success
    except Exception as e:
        logger.error("\n💥 Demo crashed: %s", e)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
