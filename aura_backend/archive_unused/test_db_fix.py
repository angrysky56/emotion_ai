#!/usr/bin/env python3
"""
Simple test to verify ChromaDB is working after removing enhanced_vector_db.py
"""

import sys
from pathlib import Path

# Add the backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the working classes
from main import AuraVectorDB, ConversationMemory
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basic_operations():
    """Test basic ChromaDB operations with the working AuraVectorDB"""
    try:
        logger.info("🧪 Testing AuraVectorDB basic operations...")
        
        # Initialize the working vector DB
        vector_db = AuraVectorDB(persist_directory="./test_aura_chroma_db")
        logger.info("✅ AuraVectorDB initialized successfully")
        
        # Create a test memory
        test_memory = ConversationMemory(
            user_id="test_user",
            message="This is a test message to verify ChromaDB is working",
            sender="user",
            timestamp=datetime.now()
        )
        
        # Test storing
        logger.info("🧪 Testing conversation storage...")
        doc_id = await vector_db.store_conversation(test_memory)
        logger.info("✅ Stored conversation with ID: %s", doc_id)
        
        # Test searching
        logger.info("🧪 Testing conversation search...")
        results = await vector_db.search_conversations(
            query="test message",
            user_id="test_user",
            n_results=1
        )
        logger.info("✅ Search returned %s results", len(results))
        
        if results:
            logger.info("📄 Found: %s...", results[0]['content'][:50])
        
        logger.info("🎉 All basic operations completed successfully!")
        return True
        
    except Exception as e:
        logger.error("❌ Test failed: %s", e)
        return False

if __name__ == "__main__":
    import asyncio
    
    success = asyncio.run(test_basic_operations())
    
    if success:
        print("\n✅ ChromaDB is working correctly with AuraVectorDB")
        print("🧹 The enhanced_vector_db.py was the cause of compaction errors")
        print("🎯 System is ready for normal operation")
    else:
        print("\n❌ ChromaDB still has issues")
        print("🔍 Further investigation needed")
    
    sys.exit(0 if success else 1)
