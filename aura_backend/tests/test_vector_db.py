#!/usr/bin/env python3
"""
Test Aura's Vector Database Integration with ChromaDB
====================================================

This script tests the core vector database functionality that Aura will use
for advanced memory, emotional pattern analysis, and semantic search.
"""

import asyncio
import logging
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_chroma_installation():
    """Test if ChromaDB is properly installed and accessible"""
    print("🧪 Testing ChromaDB Installation...")

    try:
        import chromadb
        from chromadb.config import Settings
        print("✅ ChromaDB imported successfully")

        # Test basic client creation
        chromadb.Client(Settings(allow_reset=True, is_persistent=False))
        print("✅ ChromaDB client created successfully")
        return True
    except ImportError as e:
        print(f"❌ ChromaDB not available: {e}")
        return False
    except Exception as e:
        print(f"❌ ChromaDB error: {e}")
        return False

def test_embedding_model():
    """Test sentence transformer model for embeddings"""
    print("\n🔤 Testing Embedding Model...")

    try:
        from sentence_transformers import SentenceTransformer

        # Load the same model that Aura uses
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Embedding model loaded successfully")

        # Test encoding
        test_texts = [
            "I'm feeling happy today!",
            "This conversation is about emotional intelligence",
            "Aura is learning from our interactions"
        ]

        embeddings = model.encode(test_texts)
        print(f"✅ Generated {len(embeddings)} embeddings of dimension {embeddings[0].shape[0]}")

        return True, model
    except ImportError as e:
        print(f"❌ SentenceTransformers not available: {e}")
        return False, None
    except Exception as e:
        print(f"❌ Embedding model error: {e}")
        return False, None

def test_aura_emotional_memory():
    """Test Aura's emotional memory system"""
    print("\n🎭 Testing Aura's Emotional Memory System...")

    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer

        # Create client and embedding model
        client = chromadb.Client(Settings(allow_reset=True, is_persistent=False))
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Create Aura's emotional patterns collection
        emotional_collection = client.create_collection(
            name="aura_emotional_patterns",
            metadata={"description": "Aura's emotional intelligence memory"}
        )

        # Sample emotional data that Aura would store
        emotional_memories = [
            {
                "content": "User expressed happiness about their promotion at work",
                "emotion": "Joy",
                "intensity": "High",
                "brainwave": "Gamma",
                "neurotransmitter": "Dopamine",
                "context": "career_success"
            },
            {
                "content": "User felt overwhelmed with daily tasks and responsibilities",
                "emotion": "Stressed",
                "intensity": "Medium",
                "brainwave": "Beta",
                "neurotransmitter": "Cortisol",
                "context": "work_pressure"
            },
            {
                "content": "User shared a peaceful moment during meditation",
                "emotion": "Peace",
                "intensity": "High",
                "brainwave": "Alpha",
                "neurotransmitter": "GABA",
                "context": "mindfulness"
            }
        ]

        # Store emotional memories with embeddings
        documents = []
        metadatas = []
        ids = []
        embeddings = []

        for memory in emotional_memories:
            content = memory["content"]
            documents.append(content)

            # Create metadata
            metadata = {
                "emotion": memory["emotion"],
                "intensity": memory["intensity"],
                "brainwave": memory["brainwave"],
                "neurotransmitter": memory["neurotransmitter"],
                "context": memory["context"],
                "timestamp": datetime.now().isoformat()
            }
            metadatas.append(metadata)

            # Generate unique ID
            ids.append(f"emotion_{uuid.uuid4().hex[:8]}")

            # Generate embedding
            embedding = embedding_model.encode(content).tolist()
            embeddings.append(embedding)

        # Add to collection
        emotional_collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ Stored {len(documents)} emotional memories")

        # Test semantic search for emotional patterns
        search_queries = [
            "feeling happy and successful",
            "stress and overwhelming feelings",
            "calm and peaceful moments"
        ]

        for query in search_queries:
            query_embedding = embedding_model.encode(query).tolist()
            results = emotional_collection.query(
                query_embeddings=[query_embedding],
                n_results=2,
                include=["documents", "metadatas", "distances"]
            )

            print(f"\n🔍 Query: '{query}'")
            if (results and results['documents'] and results['documents'][0] and
                    results['metadatas'] and results['metadatas'][0]):
                for i, doc in enumerate(results['documents'][0]):
                    emotion = results['metadatas'][0][i]['emotion']
                    similarity = 1 - results['distances'][0][i] if results['distances'] and results['distances'][0] else 0
                    print(f"   📄 Found: {emotion} emotion (Similarity: {similarity:.3f})")
            else:
                print("   📄 No results found for this query.")

        return True

    except Exception as e:
        print(f"❌ Emotional memory test failed: {e}")
        return False

def test_aura_conversation_memory():
    """Test Aura's conversation memory with ASEKE framework"""
    print("\n💬 Testing Aura's Conversation Memory (ASEKE Framework)...")

    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer

        client = chromadb.Client(Settings(allow_reset=True, is_persistent=False))
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Create conversation collection
        conversation_collection = client.create_collection(
            name="aura_conversations",
            metadata={"description": "Aura's conversation memory with ASEKE framework"}
        )

        # Sample conversation data with ASEKE components
        conversations = [
            {
                "content": "Tell me about the importance of emotional intelligence in relationships",
                "sender": "user",
                "aseke_focus": "ESA",  # Emotional State Algorithms
                "context": "learning_about_emotions"
            },
            {
                "content": "Emotional intelligence helps us understand and manage our emotions, leading to better relationships and communication",
                "sender": "aura",
                "aseke_focus": "KI",  # Knowledge Integration
                "context": "teaching_emotional_concepts"
            },
            {
                "content": "How can I improve my ability to recognize emotions in others?",
                "sender": "user",
                "aseke_focus": "IS",  # Information Structures
                "context": "skill_development"
            },
            {
                "content": "Practice active listening, observe body language, and pay attention to vocal cues. Empathy grows with conscious effort.",
                "sender": "aura",
                "aseke_focus": "KP",  # Knowledge Propagation
                "context": "practical_guidance"
            }
        ]

        # Store conversations
        documents = []
        metadatas = []
        ids = []
        embeddings = []

        for conv in conversations:
            documents.append(conv["content"])

            metadata = {
                "sender": conv["sender"],
                "aseke_focus": conv["aseke_focus"],
                "context": conv["context"],
                "timestamp": datetime.now().isoformat()
            }
            metadatas.append(metadata)

            ids.append(f"conv_{uuid.uuid4().hex[:8]}")

            embedding = embedding_model.encode(conv["content"]).tolist()
            embeddings.append(embedding)

        conversation_collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ Stored {len(documents)} conversation memories")

        # Test semantic search for conversation context
        search_queries = [
            "emotional intelligence and relationships",
            "recognizing emotions in other people",
            "improving social skills"
        ]

        for query in search_queries:
            query_embedding = embedding_model.encode(query).tolist()
            results = conversation_collection.query(
                query_embeddings=[query_embedding],
                n_results=2,
                include=["documents", "metadatas", "distances"]
            )

            print(f"\n🔍 Query: '{query}'")
            if results and results['documents'] and results['documents'][0] and results['documents'][0] is not None:
                for i, doc in enumerate(results['documents'][0]):
                    if results['metadatas'] and results['metadatas'][0] and results['metadatas'][0][i]:
                        sender = results['metadatas'][0][i]['sender']
                        aseke = results['metadatas'][0][i]['aseke_focus']
                        similarity = 1 - results['distances'][0][i] if results['distances'] and results['distances'][0] else 0
                        content_preview = doc[:60] + "..." if len(doc) > 60 else doc
                        print(f"   💭 {sender} ({aseke}): {content_preview} (Similarity: {similarity:.3f})")
                    else:
                        print("   💭 Metadata is missing for this result.")

        return True

    except Exception as e:
        print(f"❌ Conversation memory test failed: {e}")
        return False

def test_aura_knowledge_integration():
    """Test Aura's knowledge substrate and pattern recognition"""
    print("\n🧠 Testing Aura's Knowledge Integration...")

    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer

        client = chromadb.Client(Settings(allow_reset=True, is_persistent=False))
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Create knowledge substrate collection
        knowledge_collection = client.create_collection(
            name="aura_knowledge_substrate",
            metadata={"description": "Aura's shared knowledge and insights"}
        )

        # Sample knowledge entries
        knowledge_entries = [
            {
                "content": "The ASEKE framework consists of 7 components: KS, CE, IS, KI, KP, ESA, and SDA",
                "type": "framework_definition",
                "category": "cognitive_architecture"
            },
            {
                "content": "Emotional states can be mathematically modeled using formulas that combine multiple components",
                "type": "concept_explanation",
                "category": "emotional_intelligence"
            },
            {
                "content": "Vector databases enable semantic search by storing high-dimensional representations of text",
                "type": "technical_knowledge",
                "category": "ai_technology"
            },
            {
                "content": "Adaptive self-reflection allows AI systems to learn from mistakes and improve over time",
                "type": "principle",
                "category": "ai_learning"
            }
        ]

        # Store knowledge
        documents = []
        metadatas = []
        ids = []
        embeddings = []

        for entry in knowledge_entries:
            documents.append(entry["content"])

            metadata = {
                "type": entry["type"],
                "category": entry["category"],
                "timestamp": datetime.now().isoformat()
            }
            metadatas.append(metadata)

            ids.append(f"knowledge_{uuid.uuid4().hex[:8]}")

            embedding = embedding_model.encode(entry["content"]).tolist()
            embeddings.append(embedding)

        knowledge_collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        print(f"✅ Stored {len(documents)} knowledge entries")

        # Test cross-domain knowledge retrieval
        search_queries = [
            "cognitive frameworks for AI",
            "mathematical modeling of emotions",
            "machine learning and adaptation"
        ]

        for query in search_queries:
            query_embedding = embedding_model.encode(query).tolist()
            results = knowledge_collection.query(
                query_embeddings=[query_embedding],
                n_results=2,
                include=["documents", "metadatas", "distances"]
            )

            print(f"\n🔍 Query: '{query}'")
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    if results['metadatas'] and results['metadatas'][0] and results['metadatas'][0][i]:
                        results['metadatas'][0][i]['category']
                        results['metadatas'][0][i]['type']
                        1 - results['distances'][0][i] if results['distances'] and results['distances'][0] else 0
                        doc[:60] + "..." if len(doc) > 60 else doc
                    else:
                        print("   Metadata is missing for this result.")
            else:
                print("   No documents found for this query.")

        return True

    except Exception as e:
        print(f"❌ Knowledge integration test failed: {e}")
        return False

async def run_comprehensive_test():
    """Run all tests for Aura's vector database system"""
    print("🚀 Aura Vector Database Comprehensive Test")
    print("=" * 50)

    tests = [
        ("ChromaDB Installation", test_chroma_installation),
        ("Embedding Model", lambda: test_embedding_model()[0]),
        ("Emotional Memory System", test_aura_emotional_memory),
        ("Conversation Memory (ASEKE)", test_aura_conversation_memory),
        ("Knowledge Integration", test_aura_knowledge_integration)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("📊 Aura Vector Database Test Results:")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 Outstanding! Aura's vector database system is fully operational!")
        print("\n🧠 Aura is now capable of:")
        print("   • Semantic memory storage and retrieval")
        print("   • Emotional pattern analysis and tracking")
        print("   • ASEKE framework implementation")
        print("   • Cross-domain knowledge integration")
        print("   • Advanced conversational context understanding")

        print("\n🚀 Next Steps:")
        print("   1. Start the main Aura backend: ./start_all.sh")
        print("   2. Configure your frontend to use the API")
        print("   3. Begin building advanced AI conversations!")

        return True
    else:
        print(f"\n⚠️ {total-passed} tests failed. Please resolve these issues:")

        for test_name, result in results:
            if not result:
                print(f"   • {test_name}")

        return False

if __name__ == "__main__":
    import sys
    success = asyncio.run(run_comprehensive_test())
    sys.exit(0 if success else 1)
