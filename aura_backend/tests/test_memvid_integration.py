#!/usr/bin/env python3
"""
Test script to verify memvid integration status
"""

import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_memvid_integration():
    """Test the memvid archival service integration"""

    print("🔍 Testing Memvid Integration...")

    # Test 1: Import check
    try:
        import memvid_sdk

        print("✅ Memvid SDK (v2) import successful")
    except ImportError as e:
        print(f"❌ Memvid SDK import failed: {e}")
        return False

    # Test 2: Archival service import
    try:
        from memvid_archival_service import MemvidArchivalService

        print("✅ MemvidArchivalService import successful")
    except ImportError as e:
        print(f"❌ MemvidArchivalService import failed: {e}")
        return False

    # Test 3: Initialize service
    try:
        service = MemvidArchivalService()
        print("✅ MemvidArchivalService initialization successful")
    except Exception as e:
        print(f"❌ MemvidArchivalService initialization failed: {e}")
        return False

    # Test 4: List archives
    try:
        archives = await service.list_archives()
        print(f"✅ list_archives() successful - found {len(archives)} archives")

        if archives:
            print("📁 Available archives:")
            for i, archive in enumerate(archives[:3]):  # Show first 3
                print(f"   {i+1}. {archive}")
        else:
            print("   No archives found (this is normal for a new installation)")

    except Exception as e:
        print(f"❌ list_archives() failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 5: Real memvid initialization
    try:
        from aura_real_memvid import REAL_MEMVID_AVAILABLE, AuraRealMemvid

        print(
            f"✅ AuraRealMemvid import successful - Available: {REAL_MEMVID_AVAILABLE}"
        )

        if REAL_MEMVID_AVAILABLE:
            # Test creating an instance
            real_memvid = AuraRealMemvid(
                aura_chroma_path="./test_chroma_db",
                memvid_video_path="./test_memvid_videos",
                active_memory_days=30,
                existing_chroma_client=None,
            )
            print("✅ AuraRealMemvid instance creation successful")

            # Test list archives
            archives = real_memvid.list_video_archives()
            print(
                f"✅ AuraRealMemvid.list_video_archives() successful - found {len(archives)} archives"
            )

    except Exception as e:
        print(f"❌ AuraRealMemvid test failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n🎉 Memvid integration test completed!")
    return True


if __name__ == "__main__":
    asyncio.run(test_memvid_integration())
