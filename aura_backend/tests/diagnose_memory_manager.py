
import sys
import logging
import asyncio
from pathlib import Path

# Configure logging to see messages from the modules
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the aura_backend directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

async def run_diagnostic():
    try:
        from aura_real_memvid import get_aura_real_memvid, REAL_MEMVID_AVAILABLE as REAL_MEMVID_AVAILABLE_FROM_REAL_MEMVID
        from aura_internal_memvid_tools import get_aura_internal_memvid_tools
        from aura_intelligent_memory_manager import get_intelligent_memory_manager

        logger.info("✅ All modules imported successfully")
        logger.info("Initial check: REAL_MEMVID_AVAILABLE from aura_real_memvid.py: %s", REAL_MEMVID_AVAILABLE_FROM_REAL_MEMVID)

        # --- Step 1: Attempt to initialize AuraRealMemvid ---
        logger.info("🔄 Step 1: Attempting to get AuraRealMemvid instance...")
        real_memvid_instance = None
        try:
            real_memvid_instance = get_aura_real_memvid()
            logger.info("✅ AuraRealMemvid instance obtained: %s", real_memvid_instance is not None)
            if real_memvid_instance:
                # Check ChromaDB connection
                try:
                    chroma_client = real_memvid_instance.chroma_client
                    collections = chroma_client.list_collections()
                    logger.info("✅ ChromaDB connected with %s collections", len(collections))
                    for collection in collections:
                        logger.info("   - Collection: %s", collection.name)
                except Exception as e:
                    logger.error("❌ ChromaDB connection issue: %s", e)

                # Check memvid availability
                logger.info("🎬 REAL_MEMVID_AVAILABLE: %s", REAL_MEMVID_AVAILABLE_FROM_REAL_MEMVID)

                # Test basic functionality
                try:
                    stats = real_memvid_instance.get_system_stats()
                    logger.info("📊 System stats retrieved: %s", stats.get('memvid_type', 'unknown'))
                    logger.info("   - Active conversations: %s", stats.get('active_memory', {}).get('conversations', 0))
                    logger.info("   - Video archives: %s", len(stats.get('video_archives', {})))
                except Exception as e:
                    logger.error("❌ Error getting system stats: %s", e)
        except Exception as e:
            logger.error("❌ Error getting AuraRealMemvid instance: %s", e)
            import traceback
            logger.error("Traceback: %s", traceback.format_exc())

        # --- Step 2: Attempt to initialize AuraInternalMemvidTools ---
        logger.info("🔄 Step 2: Attempting to get AuraInternalMemvidTools instance...")
        internal_tools_instance = None
        if real_memvid_instance:
            try:
                # AuraInternalMemvidTools only needs the vector_db_client
                internal_tools_instance = get_aura_internal_memvid_tools(
                    vector_db_client=real_memvid_instance.chroma_client
                )
                logger.info("✅ AuraInternalMemvidTools instance obtained: %s", internal_tools_instance is not None)

                if internal_tools_instance:
                    # Test basic functionality
                    try:
                        available = getattr(internal_tools_instance, 'is_available', True)
                        logger.info("📋 Internal tools available: %s", available)

                        # Test archive listing (async method)
                        archives_result = await internal_tools_instance.list_video_archives()
                        archives = archives_result.get('archives', [])
                        logger.info("📂 Found %s existing archives", len(archives))
                        for archive in archives[:3]:  # Show first 3
                            logger.info("   - %s: %sMB", archive.get('name', 'unknown'), archive.get('video_size_mb', 0))
                    except Exception as e:
                        logger.error("❌ Error testing internal tools functionality: %s", e)
            except Exception as e:
                logger.error("❌ Error getting AuraInternalMemvidTools instance: %s", e)
                import traceback
                logger.error("Traceback: %s", traceback.format_exc())
        else:
            logger.warning("⚠️ Skipping AuraInternalMemvidTools as AuraRealMemvid was not obtained.")

        # --- Step 3: Attempt to initialize AuraIntelligentMemoryManager ---
        logger.info("🔄 Step 3: Attempting to get AuraIntelligentMemoryManager instance...")
        intelligent_mem_manager = None
        if real_memvid_instance:
            try:
                # The get_intelligent_memory_manager takes a vector_db_client
                intelligent_mem_manager = get_intelligent_memory_manager(
                    vector_db_client=real_memvid_instance.chroma_client
                )
                logger.info("✅ AuraIntelligentMemoryManager instance obtained: %s", intelligent_mem_manager is not None)

                if intelligent_mem_manager:
                    # Test basic functionality
                    try:
                        available = getattr(intelligent_mem_manager, 'is_available', True)
                        logger.info("🧠 Intelligent memory manager available: %s", available)

                        # Test memory organization suggestions (async method)
                        suggestions = await intelligent_mem_manager.suggest_archive_opportunities("test_user")
                        logger.info("💡 Generated %s archive suggestions", len(suggestions))
                        for suggestion in suggestions[:2]:  # Show first 2
                            logger.info("   - %s", suggestion.get('title', 'Unknown suggestion'))

                    except Exception as e:
                        logger.error("❌ Error testing intelligent memory manager functionality: %s", e)
            except Exception as e:
                logger.error("❌ Error getting AuraIntelligentMemoryManager instance: %s", e)
                import traceback
                logger.error("Traceback: %s", traceback.format_exc())
        else:
            logger.warning("⚠️ Skipping AuraIntelligentMemoryManager as AuraRealMemvid was not obtained.")

        # --- Step 4: Integration Test ---
        logger.info("🔄 Step 4: Testing integration between components...")
        if real_memvid_instance and internal_tools_instance and intelligent_mem_manager:
            try:
                # Test a simple search operation that uses all components
                test_query = "test integration query"
                search_results = real_memvid_instance.search_unified(
                    query=test_query,
                    user_id="test_user",
                    max_results=5
                )
                logger.info("🔍 Integration test search completed:")
                logger.info("   - Total results: %s", search_results.get('total_results', 0))
                logger.info("   - Active results: %s", len(search_results.get('active_results', [])))
                logger.info("   - Video archive results: %s", len(search_results.get('video_archive_results', [])))
                logger.info("   - Errors: %s", len(search_results.get('errors', [])))

                if search_results.get('errors'):
                    for error in search_results['errors']:
                        logger.warning("   ⚠️ Search error: %s", error)

            except Exception as e:
                logger.error("❌ Integration test failed: %s", e)
                import traceback
                logger.error("Traceback: %s", traceback.format_exc())
        else:
            logger.warning("⚠️ Skipping integration test as not all components were initialized.")

        logger.info("--- 🏁 Diagnostic Script Finished ---")

    except ImportError as e:
        logger.error("Failed to import one or more Aura memory modules. Please ensure all files are in the correct path or sys.path is configured: %s", e)
    except Exception as e:
        logger.error("An unexpected error occurred during diagnostic script execution: %s", e)

if __name__ == "__main__":
    asyncio.run(run_diagnostic())