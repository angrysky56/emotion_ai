#!/usr/bin/env python3
"""Database health check script"""
import chromadb
import json

def check_database_health(db_path="./aura_chroma_db"):
    try:
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()

        health_report = {
            "status": "healthy",
            "collections_count": len(collections),
            "collections": []
        }

        for collection in collections:
            try:
                count = collection.count()
                health_report["collections"].append({
                    "name": collection.name,
                    "count": count,
                    "status": "healthy"
                })
            except Exception as e:
                health_report["collections"].append({
                    "name": collection.name,
                    "status": "error",
                    "error": str(e)
                })
                health_report["status"] = "unhealthy"

        return health_report

    except Exception as e:
        return {
            "status": "critical",
            "error": str(e)
        }

if __name__ == "__main__":
    report = check_database_health()
    print(json.dumps(report, indent=2))
