#!/usr/bin/env python3
"""
ChromaDB Cleanup Script
======================

This script cleans up conflicting ChromaDB instances and UUID directories,
keeping only the main chroma.sqlite3 file.
"""

import shutil
from pathlib import Path


def cleanup_chromadb():
    """Clean up ChromaDB UUID directories and keep only the sqlite file"""

    # Define the ChromaDB directory
    chromadb_dir = Path("./aura_chroma_db")

    if not chromadb_dir.exists():
        print("✅ No ChromaDB directory found")
        return

    print(f"🔍 Checking ChromaDB directory: {chromadb_dir}")

    # List all items in the directory
    items = list(chromadb_dir.iterdir())
    print(f"📂 Found {len(items)} items in ChromaDB directory")

    # Keep track of what we're removing
    removed_count = 0
    kept_files = []

    for item in items:
        # Keep important files
        if item.name in ["chroma.sqlite3", "chroma.sqlite3-wal", "chroma.sqlite3-shm"]:
            kept_files.append(item.name)
            print(f"✅ Keeping: {item.name}")
        # Remove UUID directories and other files
        elif item.is_dir() and len(item.name) == 36 and item.name.count("-") == 4:
            print(f"🗑️  Removing UUID directory: {item.name}")
            shutil.rmtree(item)
            removed_count += 1
        else:
            print(f"⚠️  Unknown item: {item.name} (keeping for safety)")

    print("\n📊 Cleanup Summary:")
    print(f"   • Removed {removed_count} UUID directories")
    print(f"   • Kept {len(kept_files)} important files: {', '.join(kept_files)}")

    if removed_count > 0:
        print("\n✅ ChromaDB cleanup completed!")
        print("💡 You can now restart the backend safely")
    else:
        print("\n✅ No cleanup needed")


if __name__ == "__main__":
    try:
        cleanup_chromadb()
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        print("💡 You may need to manually remove the UUID directories")
