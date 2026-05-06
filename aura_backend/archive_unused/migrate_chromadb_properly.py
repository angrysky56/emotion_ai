#!/usr/bin/env python3
"""
Direct ChromaDB migration using the ChromaDB API
Properly handles the internal structure of ChromaDB databases
"""

import logging
import shutil
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_current_db(active_db_path):
    """Create a backup of the current active database before migration"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = active_db_path.parent / f"aura_chroma_db_backup_{timestamp}"
    
    if active_db_path.exists():
        shutil.copytree(active_db_path, backup_path)
        logger.info("📦 Created backup of current DB at: %s", backup_path)
        return backup_path
    return None

def migrate_chromadb_collections(backup_path, active_path):
    """Migrate collections from backup to active ChromaDB using the API"""
    logger.info("🚀 Starting ChromaDB migration using API...")
    
    # Initialize clients for both databases
    backup_client = chromadb.PersistentClient(
        path=str(backup_path),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=False  # Don't reset backup
        )
    )
    
    active_client = chromadb.PersistentClient(
        path=str(active_path),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=False  # Don't reset active
        )
    )
    
    # Get collections from backup
    try:
        backup_collections = backup_client.list_collections()
        logger.info("📂 Found %s collections in backup", len(backup_collections))
        
        for backup_collection in backup_collections:
            collection_name = backup_collection.name
            logger.info("\n🔄 Processing collection: %s", collection_name)
            
            # Get all data from backup collection
            backup_data = backup_collection.get(
                include=["embeddings", "metadatas", "documents"]
            )
            
            if not backup_data or not backup_data.get('ids'):
                logger.info("  ℹ️ No data in %s", collection_name)
                continue
                
            logger.info("  📊 Found %s documents in backup", len(backup_data['ids']))
            
            # Get or create the collection in active DB
            try:
                active_collection = active_client.get_or_create_collection(
                    name=collection_name,
                    metadata=backup_collection.metadata if hasattr(backup_collection, 'metadata') else None
                )
                
                # Get existing IDs to avoid duplicates
                existing_data = active_collection.get(include=["metadatas"])
                existing_ids = set(existing_data['ids']) if existing_data and 'ids' in existing_data else set()
                logger.info("  📈 Active collection has %s existing documents", len(existing_ids))
                
                # Filter out duplicates
                new_ids = []
                new_documents = []
                new_embeddings = []
                new_metadatas = []
                
                for i, doc_id in enumerate(backup_data['ids']):
                    if doc_id not in existing_ids:
                        new_ids.append(doc_id)
                        new_documents.append(backup_data['documents'][i])
                        new_embeddings.append(backup_data['embeddings'][i])
                        new_metadatas.append(backup_data['metadatas'][i] if backup_data['metadatas'] else {})
                
                if new_ids:
                    # Add in batches to avoid memory issues
                    batch_size = 100
                    total_added = 0
                    
                    for i in range(0, len(new_ids), batch_size):
                        end_idx = min(i + batch_size, len(new_ids))
                        
                        active_collection.add(
                            ids=new_ids[i:end_idx],
                            documents=new_documents[i:end_idx],
                            embeddings=new_embeddings[i:end_idx],
                            metadatas=new_metadatas[i:end_idx]
                        )
                        
                        total_added += (end_idx - i)
                        logger.info("    ✅ Added batch: %s/%s documents", total_added, len(new_ids))
                    
                    logger.info("  ✅ Successfully migrated %s new documents", total_added)
                else:
                    logger.info("  ℹ️ No new documents to migrate (all already exist)")
                    
            except Exception as e:
                logger.error("  ❌ Error migrating %s: %s", collection_name, e)
                continue
                
    except Exception as e:
        logger.error("❌ Failed to access backup collections: %s", e)
        raise

def verify_migration(active_path):
    """Verify the migration and show sample data"""
    logger.info("\n🔍 Verifying migration results...")
    
    client = chromadb.PersistentClient(
        path=str(active_path),
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=False
        )
    )
    
    collections = client.list_collections()
    logger.info("📊 Active database has %s collections:", len(collections))
    
    for collection in collections:
        count = collection.count()
        logger.info("\n  ✅ %s: %s documents", collection.name, count)
        
        # Show sample conversations
        if collection.name == "aura_conversations" and count > 0:
            sample = collection.get(
                limit=5,
                include=["documents", "metadatas"]
            )
            
            logger.info("    📝 Sample conversations:")
            for i, doc_id in enumerate(sample['ids'][:3]):
                doc = sample['documents'][i]
                meta = sample['metadatas'][i] if sample['metadatas'] else {}
                
                sender = meta.get('sender', 'unknown')
                emotion = meta.get('emotion_name', 'N/A')
                session = meta.get('session_id', 'N/A')[:8]
                
                logger.info("      [%s] (emotion: %s, session: %s...)", sender, emotion, session)
                logger.info("        \"%s...\"", doc[:80])

def main():
    """Main migration process"""
    backup_db_path = Path("/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend/chromadb_backups/chroma_backup_20250610_011745")
    active_db_path = Path("/home/ty/Repositories/ai_workspace/emotion_ai/aura_backend/aura_chroma_db")
    
    if not backup_db_path.exists():
        logger.error("❌ Backup path not found: %s", backup_db_path)
        return
    
    logger.info("=" * 60)
    logger.info("ChromaDB Migration Tool")
    logger.info("=" * 60)
    logger.info("📂 Backup source: %s", backup_db_path)
    logger.info("📂 Active target: %s", active_db_path)
    
    try:
        # Create backup of current active DB
        current_backup = backup_current_db(active_db_path)
        
        # Perform migration
        migrate_chromadb_collections(backup_db_path, active_db_path)
        
        # Verify results
        verify_migration(active_db_path)
        
        logger.info("\n✅ Migration completed successfully!")
        logger.info("ℹ️ Previous active DB backed up to: %s", current_backup)
        
    except Exception as e:
        logger.error("\n❌ Migration failed: %s", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
