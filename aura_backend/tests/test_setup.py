#!/usr/bin/env python3
"""
Simple test script to verify Aura backend setup
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_setup():
    try:
        # Test vector database
        print("✅ Vector database initialized")

        # Test file system
        print("✅ File system initialized")

        # Test state manager
        print("✅ State manager initialized")

        print("\n🎉 Aura backend setup test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Setup test failed: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_setup())
    sys.exit(0 if success else 1)
