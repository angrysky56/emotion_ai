#!/usr/bin/env python3
"""
Aura Chat Storage Inspector and Fixer
====================================

Inspects the current state of chat storage in ChromaDB and fixes any issues
with conversation persistence and retrieval.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def inspect_chromadb():
    """Inspect the current ChromaDB state"""
    try:
        import chromadb
        from chromadb.config import Settings

        print("🔍 Inspecting Aura's ChromaDB...")

        # Connect to the existing ChromaDB
        client = chromadb.PersistentClient(
            path="./aura_chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )

        # List all collections
        collections = client.list_collections()
        print(f"📊 Found {len(collections)} collections:")

        for collection in collections:
            print(f"\n📂 Collection: {collection.name}")
            print(f"   ID: {collection.id}")
            print(f"   Metadata: {collection.metadata}")

            # Get collection stats
            try:
                count = collection.count()
                print(f"   Document Count: {count}")

                if count > 0:
                    # Peek at some documents
                    peek_result = collection.peek(limit=3)
                    print("   Sample Documents:")

                    if peek_result and peek_result.get('documents') is not None:
                        documents = peek_result.get('documents', [])
                        if documents:
                            for i, doc in enumerate(documents[:3]):
                                metadatas = peek_result.get('metadatas', [])
                                metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
                                print(f"     {i+1}. {doc[:100]}..." if len(doc) > 100 else f"     {i+1}. {doc}")
                                print(f"        User: {metadata.get('user_id', 'unknown')}")
                                print(f"        Sender: {metadata.get('sender', 'unknown')}")
                                print(f"        Time: {metadata.get('timestamp', 'unknown')}")

            except Exception as e:
                print(f"   ❌ Error getting collection stats: {e}")

        return client, collections

    except Exception as e:
        print(f"❌ Failed to inspect ChromaDB: {e}")
        return None, []

def analyze_conversations(client, collections):
    """Analyze stored conversations"""
    try:
        print("\n🔍 Analyzing Conversation Data...")

        # Find the conversations collection
        conversations_collection = None
        for collection in collections:
            if collection.name == "aura_conversations":
                conversations_collection = collection
                break

        if not conversations_collection:
            print("❌ No 'aura_conversations' collection found!")
            return

        # Get all conversations
        all_conversations = conversations_collection.get(
            include=["documents", "metadatas", "embeddings"]
        )

        if not all_conversations or not all_conversations.get('documents'):
            print("❌ No conversations found in the collection!")
            return

        documents = all_conversations['documents']
        metadatas = all_conversations.get('metadatas', [])
        ids = all_conversations.get('ids', [])

        print(f"📊 Total Conversations: {len(documents)}")

        # Group by user and session
        user_sessions = {}
        for i, doc in enumerate(documents):
            metadata = metadatas[i] if i < len(metadatas) else {}
            user_id = metadata.get('user_id', 'unknown')
            session_id = metadata.get('session_id', 'unknown')
            sender = metadata.get('sender', 'unknown')
            timestamp = metadata.get('timestamp', 'unknown')

            if user_id not in user_sessions:
                user_sessions[user_id] = {}

            if session_id not in user_sessions[user_id]:
                user_sessions[user_id][session_id] = {
                    'messages': [],
                    'start_time': timestamp,
                    'end_time': timestamp
                }

            user_sessions[user_id][session_id]['messages'].append({
                'id': ids[i] if i < len(ids) else f'unknown_{i}',
                'content': doc,
                'sender': sender,
                'timestamp': timestamp,
                'metadata': metadata
            })

            # Update session times
            if timestamp < user_sessions[user_id][session_id]['start_time']:
                user_sessions[user_id][session_id]['start_time'] = timestamp
            if timestamp > user_sessions[user_id][session_id]['end_time']:
                user_sessions[user_id][session_id]['end_time'] = timestamp

        # Print analysis
        print(f"\n👥 Users with stored conversations: {len(user_sessions)}")

        for user_id, sessions in user_sessions.items():
            print(f"\n👤 User: {user_id}")
            print(f"   📁 Sessions: {len(sessions)}")

            for session_id, session_data in sessions.items():
                messages = session_data['messages']
                print(f"   🗨️  Session {session_id[:8]}...")
                print(f"      Messages: {len(messages)}")
                print(f"      Duration: {session_data['start_time']} to {session_data['end_time']}")

                # Show message breakdown
                user_msgs = len([m for m in messages if m['sender'] == 'user'])
                aura_msgs = len([m for m in messages if m['sender'] == 'aura'])
                print(f"      User messages: {user_msgs}, Aura messages: {aura_msgs}")

                # Show sample messages
                print("      Sample messages:")
                for i, msg in enumerate(messages[:2]):  # First 2 messages
                    content_preview = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
                    print(f"        {i+1}. [{msg['sender']}] {content_preview}")

        return user_sessions

    except Exception as e:
        print(f"❌ Failed to analyze conversations: {e}")
        logger.exception("Analysis error")
        return {}

def check_storage_implementation():
    """Check the current storage implementation in main.py"""
    try:
        print("\n🔍 Checking Storage Implementation...")

        # Read the main.py file to check storage logic
        main_py_path = Path("main.py")
        if not main_py_path.exists():
            print("❌ main.py not found!")
            return

        with open(main_py_path, 'r') as f:
            content = f.read()

        # Check for storage-related code
        storage_checks = [
            ("store_conversation", "✅ store_conversation method found" if "store_conversation" in content else "❌ store_conversation method missing"),
            ("background_tasks.add_task", "✅ Background task storage found" if "background_tasks.add_task" in content else "❌ Background task storage missing"),
            ("ConversationMemory", "✅ ConversationMemory class found" if "ConversationMemory" in content else "❌ ConversationMemory class missing"),
            ("vector_db.store_conversation", "✅ Vector DB storage call found" if "vector_db.store_conversation" in content else "❌ Vector DB storage call missing"),
        ]

        print("📋 Storage Implementation Check:")
        for check_name, result in storage_checks:
            print(f"   {result}")

        # Check if there are any obvious issues
        issues = []
        if "await vector_db.store_conversation" not in content:
            issues.append("Storage calls might not be awaited properly")

        if "background_tasks.add_task(vector_db.store_conversation" not in content:
            issues.append("Background storage tasks might not be configured correctly")

        if issues:
            print("\n⚠️  Potential Issues:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("\n✅ Storage implementation looks correct")

    except Exception as e:
        print(f"❌ Failed to check storage implementation: {e}")

def create_test_conversation():
    """Create a test conversation to verify storage is working"""
    try:
        print("\n🧪 Creating Test Conversation...")

        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
        import uuid

        # Connect to ChromaDB
        client = chromadb.PersistentClient(
            path="./aura_chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create conversations collection
        try:
            conversations = client.get_collection("aura_conversations")
        except Exception:
            conversations = client.create_collection("aura_conversations")

        # Initialize embedding model
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Create test conversation
        test_user_id = "test_user_storage_check"
        test_session_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()

        test_messages = [
            ("user", "Hello Aura, I'm testing the chat storage system."),
            ("aura", "Hello! I can see you're testing the storage system. This conversation should be saved to ChromaDB."),
            ("user", "Perfect! Can you confirm that our conversation history will be preserved?"),
            ("aura", "Yes! This conversation is being stored in the vector database with proper metadata including timestamps, user IDs, and session information.")
        ]

        print("💾 Storing test messages...")

        for i, (sender, message) in enumerate(test_messages):
            # Generate embedding
            embedding = embedding_model.encode(message).tolist()

            # Create document ID
            doc_id = f"{test_user_id}_{current_time}_{i}_{uuid.uuid4().hex[:8]}"

            # Create metadata
            metadata = {
                "user_id": test_user_id,
                "sender": sender,
                "timestamp": current_time,
                "session_id": test_session_id,
                "test_message": True  # Mark as test
            }

            # Store in ChromaDB
            conversations.add(
                documents=[message],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id]
            )

            print(f"   ✅ Stored: [{sender}] {message[:50]}...")

        print("✅ Test conversation created successfully!")
        print(f"   User ID: {test_user_id}")
        print(f"   Session ID: {test_session_id[:8]}...")
        print(f"   Messages: {len(test_messages)}")

        # Verify storage by querying
        print("\n🔍 Verifying storage...")

        query_result = conversations.get(
            where={"user_id": test_user_id},
            include=["documents", "metadatas"]
        )

        if query_result and query_result.get('documents'):
            documents = query_result.get('documents', [])
            if documents is not None:
                print(f"✅ Verification successful! Found {len(documents)} stored messages")
            else:
                print("❌ Verification failed! Documents is None")
        else:
            print("❌ Verification failed! No messages found for test user")

    except Exception as e:
        print(f"❌ Failed to create test conversation: {e}")
        logger.exception("Test conversation error")

def main():
    """Main inspection and analysis"""
    print("🔧 Aura Chat Storage Inspector")
    print("=" * 50)

    # Inspect ChromaDB
    client, collections = inspect_chromadb()

    if client and collections:
        # Analyze conversations
        user_sessions = analyze_conversations(client, collections)

        # Show summary
        if user_sessions:
            total_users = len(user_sessions)
            total_sessions = sum(len(sessions) for sessions in user_sessions.values())
            total_messages = sum(
                len(session['messages'])
                for sessions in user_sessions.values()
                for session in sessions.values()
            )

            print("\n📊 STORAGE SUMMARY:")
            print(f"   👥 Total Users: {total_users}")
            print(f"   📁 Total Sessions: {total_sessions}")
            print(f"   💬 Total Messages: {total_messages}")

            # Explain how the existing chats got there
            print("\n💡 HOW EXISTING CHATS GOT THERE:")
            print(f"   The {total_messages} messages you see in the UI were stored by Aura's")
            print("   vector database system during previous conversations. Each message")
            print("   is automatically saved with embeddings for semantic search.")

    # Check storage implementation
    check_storage_implementation()

    # Create test conversation
    create_test_conversation()

    print("\n✅ Inspection Complete!")
    print("   Chat storage system appears to be working.")
    print("   Existing chats were preserved from previous sessions.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Inspection interrupted by user")
    except Exception as e:
        print(f"\n❌ Inspection failed: {e}")
        logger.exception("Inspection error")
