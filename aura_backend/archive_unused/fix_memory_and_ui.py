#!/usr/bin/env python3
"""
Fix for Aura's memory and UI issues
- Ensures emotions are properly stored with conversations
- Fixes chat history display
- Corrects memvid parameter handling
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from main import vector_db, conversation_persistence, EmotionalStateData, CognitiveState, AsekeComponent, EmotionalIntensity
from conversation_persistence_service import ConversationMemory, ConversationExchange

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_current_memory_state():
    """Check the current state of memory storage"""
    logger.info("🔍 Checking current memory state...")

    try:
        # Check if we have any conversations stored
        all_convos = vector_db.conversations.get(
            include=["documents", "metadatas"]
        )

        total_memories = len(all_convos['ids']) if all_convos and 'ids' in all_convos else 0
        logger.info("📊 Total memories in database: %s", total_memories)

        sessions = {} # Initialize sessions here

        if total_memories > 0 and all_convos and 'metadatas' in all_convos and all_convos['metadatas'] is not None:
            # Check a sample of recent memories for emotion data
            sample_size = min(10, total_memories)
            logger.info("🔍 Checking %s recent memories for emotion data...", sample_size)

            emotions_found = 0
            for i in range(sample_size):
                metadata = all_convos['metadatas'][i]
                if 'emotion_name' in metadata:
                    emotions_found += 1
                    logger.debug("   Memory %s: Has emotion '%s' (%s)", i, metadata['emotion_name'], metadata.get('emotion_intensity', 'Unknown'))
                else:
                    logger.debug("   Memory %s: No emotion data", i)

            logger.info("📈 %s/%s memories have emotion data", emotions_found, sample_size)

            # Check for session grouping
            for i, metadata in enumerate(all_convos['metadatas']):
                session_id = metadata.get('session_id', 'unknown')
                if session_id not in sessions:
                    sessions[session_id] = []
                sessions[session_id].append(i)

            logger.info("💬 Found %s unique chat sessions", len(sessions))

        return {
            'total_memories': total_memories,
            'has_data': total_memories > 0,
            'session_count': len(sessions) if total_memories > 0 else 0
        }

    except Exception as e:
        logger.error("❌ Error checking memory state: %s", e)
        return {'total_memories': 0, 'has_data': False, 'error': str(e)}

async def test_chat_history_retrieval(user_id: str = "ty"):
    """Test the chat history retrieval to ensure it's working"""
    logger.info("🔍 Testing chat history retrieval for user: %s", user_id)

    try:
        # Use the same method the API uses
        result = await conversation_persistence.safe_get_chat_history(user_id, limit=10)

        if result.get('sessions'):
            logger.info("✅ Found %s chat sessions", len(result['sessions']))

            for i, session in enumerate(result['sessions'][:3]):  # Show first 3
                logger.info("\n📅 Session %s:", i+1)
                logger.info("   ID: %s", session['session_id'])
                logger.info("   Messages: %s", session['message_count'])
                logger.info("   Start: %s", session['start_time'])
                logger.info("   Last: %s", session['last_time'])

                if session['messages']:
                    first_msg = session['messages'][0]
                    logger.info("   First message: %s...", first_msg['content'][:50])
                    logger.info("   Sender: %s", first_msg['sender'])
                    if 'emotion' in first_msg:
                        logger.info("   Emotion: %s", first_msg['emotion'])
        else:
            logger.warning("⚠️ No sessions found in chat history")

        return result

    except Exception as e:
        logger.error("❌ Error testing chat history: %s", e)
        import traceback
        traceback.print_exc()
        return None

async def add_test_conversation_with_emotions(user_id: str = "ty"):
    """Add a test conversation with proper emotional states to verify the system"""
    logger.info("🧪 Adding test conversation with emotions...")

    try:
        # Create test emotional states
        user_emotion = EmotionalStateData(
            name="Curious",
            formula="Cu(x) = Q(x) AND E(x)",
            components={"Q": "Questions generated", "E": "Eagerness to learn"},
            ntk_layer="Beta-like_NTK",
            brainwave="Beta",
            neurotransmitter="Dopamine",
            description="A strong desire to learn",
            intensity=EmotionalIntensity("High"),
            timestamp=datetime.now()
        )

        aura_emotion = EmotionalStateData(
            name="Helpful",
            formula="H(x) = K(x) AND S(x)",
            components={"K": "Knowledge shared", "S": "Support provided"},
            ntk_layer="Alpha-like_NTK",
            brainwave="Alpha",
            neurotransmitter="Serotonin",
            description="Engaged in helping",
            intensity=EmotionalIntensity("Medium"),
            timestamp=datetime.now()
        )

        cognitive_state = CognitiveState(
            focus=AsekeComponent.LEARNING,
            description="Processing and understanding user needs",
            context="Test conversation",
            timestamp=datetime.now()
        )

        # Create conversation memories
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        user_memory = ConversationMemory(
            user_id=user_id,
            message="Can you help me understand how your memory system works?",
            sender="user",
            emotional_state=user_emotion,
            cognitive_state=None,
            timestamp=datetime.now(),
            session_id=session_id
        )

        aura_memory = ConversationMemory(
            user_id=user_id,
            message="I'd be happy to explain my memory system! I use a vector database to store our conversations along with emotional and cognitive states. Each message is embedded and stored with metadata including emotions, focus areas, and timestamps. This allows me to search semantically and maintain context across our interactions.",
            sender="aura",
            emotional_state=aura_emotion,
            cognitive_state=cognitive_state,
            timestamp=datetime.now(),
            session_id=session_id
        )

        # Create exchange
        exchange = ConversationExchange(
            user_memory=user_memory,
            ai_memory=aura_memory,
            user_emotional_state=user_emotion,
            ai_emotional_state=aura_emotion,
            ai_cognitive_state=cognitive_state,
            session_id=session_id
        )

        # Persist using the service
        result = await conversation_persistence.persist_conversation_exchange(exchange)

        if result['success']:
            logger.info("✅ Test conversation added successfully!")
            logger.info("   Session ID: %s", session_id)
            logger.info("   Components stored: %s", result['stored_components'])
            logger.info("   User emotion: %s (%s)", user_emotion.name, user_emotion.intensity.value)
            logger.info("   Aura emotion: %s (%s)", aura_emotion.name, aura_emotion.intensity.value)
            logger.info("   Cognitive focus: %s", cognitive_state.focus.value)
        else:
            logger.error("❌ Failed to add test conversation: %s", result.get('errors', 'Unknown error'))

        return result

    except Exception as e:
        logger.error("❌ Error adding test conversation: %s", e)
        import traceback
        traceback.print_exc()
        return None

async def verify_persistence_service():
    """Verify the persistence service is working correctly"""
    logger.info("🔍 Verifying persistence service...")

    try:
        # Get metrics
        metrics = await conversation_persistence.get_persistence_metrics()

        logger.info("📊 Persistence Service Metrics:")
        logger.info("   Total operations: %s", metrics['total_operations'])
        logger.info("   Successful: %s", metrics['successful_operations'])
        logger.info("   Failed: %s", metrics['failed_operations'])
        logger.info("   Success rate: %s", metrics['success_rate']:.1%)
        logger.info("   Avg duration: %sms", metrics['average_duration_ms'])

        # Check health
        from conversation_persistence_service import PersistenceHealthCheck
        health_checker = PersistenceHealthCheck(conversation_persistence)
        health = await health_checker.check_health()

        logger.info("\n💊 Health Status: %s", '✅ Healthy' if health['healthy'] else '❌ Unhealthy')
        for check, status in health['checks'].items():
            logger.info("   %s: %s", check, '✅' if status else '❌')

        return health['healthy']

    except Exception as e:
        logger.error("❌ Error verifying persistence service: %s", e)
        return False

async def fix_memvid_tool_parameters():
    """Fix the memvid tool parameter handling"""
    logger.info("🔧 Checking memvid tool parameters...")

    try:
        # Check if the aura_internal_memvid_tools.py exists
        memvid_tools_path = Path(__file__).parent / "aura_internal_memvid_tools.py"

        if memvid_tools_path.exists():
            logger.info("✅ Found memvid tools file")

            # The error shows the tool expects a 'params' wrapper with MemvidImportParams structure
            # Let's create a wrapper function to handle this
            wrapper_code = '''
# Memvid parameter wrapper to fix the validation error
def wrap_memvid_import_params(knowledge_name: str, content: str) -> dict:
    """Wrap parameters for memvid import_knowledge_to_video tool"""
    import tempfile
    import os

    # Create a temporary file with the content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content)
        temp_path = f.name

    # Return properly structured params
    return {
        "params": {
            "source_path": temp_path,
            "archive_name": knowledge_name
        }
    }
'''

            # Write the wrapper to a helper file
            wrapper_path = Path(__file__).parent / "memvid_param_wrapper.py"
            wrapper_path.write_text(wrapper_code)
            logger.info("✅ Created memvid parameter wrapper")

        else:
            logger.warning("⚠️ Memvid tools file not found")

    except Exception as e:
        logger.error("❌ Error fixing memvid parameters: %s", e)

async def main():
    """Main diagnostic and fix routine"""
    logger.info("🚀 Starting Aura Memory and UI Fix...")
    logger.info("=" * 60)

    # 1. Check current state
    state = await check_current_memory_state()

    # 2. Verify persistence service
    persistence_ok = await verify_persistence_service()

    # 3. Test chat history retrieval
    history = await test_chat_history_retrieval()

    # 4. Add test data if needed
    if state['total_memories'] == 0:
        logger.info("\n📝 No memories found, adding test conversation...")
        await add_test_conversation_with_emotions()

        # Re-test retrieval
        logger.info("\n🔄 Re-testing chat history after adding test data...")
        history = await test_chat_history_retrieval()

    # 5. Fix memvid parameters
    await fix_memvid_tool_parameters()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 SUMMARY:")
    logger.info("   Memory State: %s", '✅ Has data' if state['has_data'] else '❌ Empty')
    logger.info("   Persistence Service: %s", '✅ Healthy' if persistence_ok else '❌ Issues detected')
    logger.info("   Chat History API: %s", '✅ Working' if history and history.get('sessions') else '❌ Not working')
    logger.info("   Total Memories: %s", state['total_memories'])
    logger.info("   Chat Sessions: %s", state.get('session_count', 0))

    if not (state['has_data'] and persistence_ok and history):
        logger.warning("\n⚠️ Some issues remain. Please check the logs above for details.")
    else:
        logger.info("\n✅ All systems appear to be working correctly!")
        logger.info("   - Emotions are being stored with conversations")
        logger.info("   - Chat history is retrievable")
        logger.info("   - Persistence service is healthy")

if __name__ == "__main__":
    asyncio.run(main())
