#!/usr/bin/env python3
"""
Migrate ChromaDB backup to active database
Transfers conversation data from backup to current ChromaDB instance
"""

import sqlite3
import chromadb
from chromadb.config import Settings
import json
import logging
from pathlib import Path
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def copy_backup_to_temp(backup_path):
    """Copy backup to temporary location to avoid WAL issues"""
    temp_path = Path(backup_path).parent / "temp_backup.sqlite3"
    shutil.copy2(backup_path, temp_path)
    return temp_path

def extract_collections_from_backup(backup_db_path):
    """Extract collection data from backup SQLite database"""
    logger.info("📂 Extracting data from backup: %s", backup_db_path)
    
    conn = sqlite3.connect(backup_db_path)
    cursor = conn.cursor()
    
    # Get all collections
    cursor.execute("SELECT id, name FROM collections")
    collections = cursor.fetchall()
    logger.info("Found %s collections in backup", len(collections))
    
    data = {}
    
    for collection_id, collection_name in collections:
        logger.info("  Processing collection: %s", collection_name)
        
        # Get embeddings and metadata for this collection
        cursor.execute("""
            SELECT 
                e.id, 
                e.embedding_id,
                em.string_value as doc_id,
                em2.string_value as document,
                em3.string_value as metadata_json
            FROM embeddings e
            LEFT JOIN embedding_metadata em ON e.id = em.embedding_id AND em.key = 'id'
            LEFT JOIN embedding_metadata em2 ON e.id = em2.embedding_id AND em2.key = 'document'
            LEFT JOIN embedding_metadata em3 ON e.id = em3.embedding_id AND em3.key = 'metadata'
            WHERE e.collection_id = ?
        """, (collection_id,))
        
        embeddings_data = cursor.fetchall()
        
        # Get actual embeddings
        collection_data = []
        for row in embeddings_data:
            embedding_id = row[0]
            
            # Get the actual embedding vector
            cursor.execute("""
                SELECT vector_value 
                FROM embeddings 
                WHERE id = ?
            """, (embedding_id,))
            
            vector_result = cursor.fetchone()
            if vector_result:
                # Parse the embedding vector (stored as blob)
                import numpy as np
                embedding = np.frombuffer(vector_result[0], dtype=np.float32).tolist()
                
                collection_data.append({
                    'id': row[2] if row[2] else f"doc_{embedding_id}",
                    'document': row[3] if row[3] else "",
                    'metadata': json.loads(row[4]) if row[4] else {},
                    'embedding': embedding
                })
        
        data[collection_name] = collection_data
        logger.info("    Found %s documents", len(collection_data))
    
    conn.close()
    return data

def migrate_to_active_db(backup_data, active_db_path):
    """Migrate backup data to active ChromaDB"""
    logger.info("🔄 Migrating to active database: %s", active_db_path)
    
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(
        path=str(active_db_path),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # Process each collection
    for collection_name, documents in backup_data.items():
        if not documents:
            continue
            
        logger.info("  Migrating collection: %s", collection_name)
        
        # Get or create collection
        try:
            collection = client.get_or_create_collection(name=collection_name)
            
            # Get existing IDs to avoid duplicates
            existing = collection.get()
            existing_ids = set(existing['ids']) if existing and 'ids' in existing else set()
            logger.info("    Existing documents: %s", len(existing_ids))
            
            # Prepare data for batch insert
            new_docs = []
            new_embeddings = []
            new_metadatas = []
            new_ids = []
            
            for doc in documents:
                # Skip if already exists
                if doc['id'] in existing_ids:
                    continue
                
                # Validate document has required fields
                if doc.get('document') and doc.get('embedding'):
                    new_docs.append(doc['document'])
                    new_embeddings.append(doc['embedding'])
                    new_metadatas.append(doc.get('metadata', {}))
                    new_ids.append(doc['id'])
            
            # Add in batches
            if new_docs:
                batch_size = 100
                total_added = 0
                
                for i in range(0, len(new_docs), batch_size):
                    end_idx = min(i + batch_size, len(new_docs))
                    
                    collection.add(
                        documents=new_docs[i:end_idx],
                        embeddings=new_embeddings[i:end_idx],
                        metadatas=new_metadatas[i:end_idx],
                        ids=new_ids[i:end_idx]
                    )
                    total_added += (end_idx - i)
                    logger.info("    Added batch: %s/%s documents", total_added, len(new_docs))
                
                logger.info("    ✅ Migrated %s new documents", total_added)
            else:
                logger.info("    ℹ️  No new documents to migrate")
                
        except Exception as e:
            logger.error("    ❌ Error migrating %s: %s", collection_name, e)
            continue

def verify_migration(active_db_path):
    """Verify the migration was successful"""
    logger.info("🔍 Verifying migration...")
    
    client = chromadb.PersistentClient(
        path=str(active_db_path),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # Check each expected collection
    expected_collections = [
        "aura_conversations",
        "aura_emotional_patterns", 
        "aura_cognitive_patterns",
        "aura_knowledge_substrate"
    ]
    
    for collection_name in expected_collections:
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
            logger.info("  ✅ %s: %s documents", collection_name, count)
            
            # Show sample of conversations
            if collection_name == "aura_conversations" and count > 0:
                sample = collection.get(limit=3, include=["documents", "metadatas"])
                logger.info("    Sample conversations:")
                for i, doc in enumerate(sample['documents'][:3]):
                    meta = sample['metadatas'][i] if sample['metadatas'] else {}
                    logger.info("      - %s: %s...", meta.get('sender', 'unknown'), doc[:50])
                    
        except Exception as e:
            logger.error("  ❌ %s: Not found or error - %s", collection_name, e)

def main():
    """Main migration process"""
    backup_db_path = Path("/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend/chromadb_backups/chroma_backup_20250610_011745/chroma.sqlite3")
    active_db_path = Path("/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend/aura_chroma_db")
    
    if not backup_db_path.exists():
        logger.error("❌ Backup database not found: %s", backup_db_path)
        return
    
    logger.info("🚀 Starting ChromaDB migration...")
    
    try:
        # Create a clean copy of backup to avoid WAL issues
        temp_backup = copy_backup_to_temp(backup_db_path)
        
        # Extract data from backup
        backup_data = extract_collections_from_backup(temp_backup)
        
        # Migrate to active database
        migrate_to_active_db(backup_data, active_db_path)
        
        # Verify migration
        verify_migration(active_db_path)
        
        # Clean up temp file
        temp_backup.unlink()
        
        logger.info("✅ Migration completed successfully!")
        
    except Exception as e:
        logger.error("❌ Migration failed: %s", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
