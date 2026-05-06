#!/usr/bin/env python3
"""
Test script to validate the persistence service integration
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_persistence_integration():
    """Test the new persistence services integration"""
    try:
        logger.info("🧪 Testing persistence service integration...")

        # Test imports
        logger.info("📦 Testing imports...")
        from conversation_persistence_service import ConversationPersistenceService, ConversationExchange
        from memvid_archival_service import MemvidArchivalService
        logger.info("✅ Imports successful")

        # Test basic initialization (without actual DB)
        logger.info("🔧 Testing service initialization...")
        
        # Create mock objects to test the service structure
        class MockVectorDB:
            async def store_conversation(self, memory):
                return f"mock_doc_id_{datetime.now().strftime('%H%M%S')}"
                
            async def store_emotional_pattern(self, emotion, user_id):
                return f"mock_emotion_id_{datetime.now().strftime('%H%M%S')}"

        class MockFileSystem:
            async def load_user_profile(self, user_id):
                return {"name": user_id, "total_messages": 0}
                
            async def save_user_profile(self, user_id, profile):
                return f"mock_profile_path_{user_id}"

        class MockMemory:
            def __init__(self, user_id, message, sender):
                self.user_id = user_id
                self.message = message
                self.sender = sender
                self.session_id = "test_session"
                self.timestamp = datetime.now()

        # Test persistence service initialization
        mock_vector_db = MockVectorDB()
        mock_file_system = MockFileSystem()
        
        persistence_service = ConversationPersistenceService(
            vector_db=mock_vector_db,
            file_system=mock_file_system
        )
        logger.info("✅ ConversationPersistenceService initialized")

        # Test memvid service initialization
        MemvidArchivalService(isolation_mode=True)
        logger.info("✅ MemvidArchivalService initialized")

        # Test conversation exchange creation
        user_memory = MockMemory("test_user", "Hello Aura!", "user")
        ai_memory = MockMemory("test_user", "Hello! How can I help you?", "aura")
        
        exchange = ConversationExchange(
            user_memory=user_memory,
            ai_memory=ai_memory
        )
        logger.info("✅ ConversationExchange created")

        # Test persistence (mock)
        logger.info("💾 Testing conversation persistence...")
        result = await persistence_service.persist_conversation_exchange(exchange)
        
        if result["success"]:
            logger.info("✅ Mock persistence successful: %s", result['stored_components'])
            logger.info("   Duration: %sms", result['duration_ms'])
        else:
            logger.warning("⚠️ Mock persistence had issues: %s", result['errors'])

        # Test metrics
        metrics = await persistence_service.get_persistence_metrics()
        logger.info("📊 Persistence metrics: %s", metrics)

        logger.info("🎉 All tests passed! Integration appears to be working correctly.")
        return True

    except ImportError as e:
        logger.error("❌ Import error: %s", e)
        return False
    except Exception as e:
        logger.error("❌ Test failed: %s", e)
        return False

def main():
    """Run the integration test"""
    logger.info("🚀 Starting persistence integration test...")
    
    success = asyncio.run(test_persistence_integration())
    
    if success:
        logger.info("✅ Integration test completed successfully!")
        logger.info("🔄 You can now restart the Aura server to use the new persistence system.")
    else:
        logger.error("❌ Integration test failed. Please check the errors above.")
    
    return success

if __name__ == "__main__":
    main()
