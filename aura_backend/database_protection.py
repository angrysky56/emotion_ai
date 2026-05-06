#!/usr/bin/env python3
"""
Database Protection Service - Proactive ChromaDB Protection
==========================================================

This service provides:
1. Automatic backup before risky operations
2. Health monitoring
3. Emergency recovery triggers
4. Transaction-like safety for database operations
"""

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class DatabaseProtectionService:
    def __init__(
        self, db_path: str = "./aura_chroma_db", backup_interval_hours: int = 6
    ):
        self.db_path = Path(db_path)
        self.backup_dir = self.db_path.parent / "auto_backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.backup_interval = timedelta(hours=backup_interval_hours)
        self.last_backup = None
        self.protection_active = True
        self.backup_thread = None

        # Operation tracking
        self.operation_log = []
        self.max_log_entries = 1000

    def start_protection(self):
        """Start the protection service"""
        logger.info("🛡️  Starting Database Protection Service")

        # Start automatic backup thread
        self.backup_thread = threading.Thread(target=self._backup_daemon, daemon=True)
        self.backup_thread.start()

        # Create initial backup
        self._create_safety_backup("initial_protection_backup")

        logger.info("✅ Database Protection Service started")

    def stop_protection(self):
        """Stop the protection service"""
        self.protection_active = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
        logger.info("🛡️  Database Protection Service stopped")

    def _backup_daemon(self):
        """Background backup daemon"""
        while self.protection_active:
            try:
                if self._should_create_backup():
                    self._create_safety_backup("auto_backup")
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error("Backup daemon error: %s", e)
                time.sleep(600)  # Wait longer on error

    def _should_create_backup(self) -> bool:
        """Check if we should create a backup"""
        if not self.last_backup:
            return True
        return datetime.now() - self.last_backup > self.backup_interval

    def _create_safety_backup(self, backup_type: str) -> Optional[Path]:
        """Create a safety backup without conflicting with existing ChromaDB instances"""
        try:
            if not self.db_path.exists():
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{backup_type}_{timestamp}"

            # Create a simple file system backup instead of using ChromaDB API
            # This avoids conflicts with running ChromaDB instances
            logger.info("🛡️ Creating file system backup: %s", backup_path)

            import shutil

            shutil.copytree(self.db_path, backup_path)

            self.last_backup = datetime.now()
            logger.info("🛡️  Safety backup created: %s", backup_path)

            # Clean old backups (keep last 10)
            self._cleanup_old_backups()

            return backup_path

        except Exception as e:
            logger.error("Failed to create safety backup: %s", e)
            return None

    def _cleanup_old_backups(self):
        """Clean up old backup files"""
        try:
            # Get all backup directories (not individual files within them)
            backup_candidates = []
            for item in self.backup_dir.iterdir():
                if item.is_dir() and "_backup_" in item.name:
                    try:
                        # Only add if we can successfully get creation time
                        ctime = os.path.getctime(item)
                        backup_candidates.append((item, ctime))
                    except (OSError, PermissionError) as e:
                        logger.warning("Skipping backup %s - cannot access: %s", item, e)
                        continue

            # Sort by creation time
            backups = sorted(backup_candidates, key=lambda x: x[1])
            backup_paths = [backup[0] for backup in backups]

            # Keep only the 10 most recent backups
            if len(backup_paths) > 10:
                for old_backup in backup_paths[:-10]:
                    try:
                        if old_backup.exists() and old_backup.is_dir():
                            import shutil

                            logger.info("🛡️ Removing old backup: %s", old_backup.name)
                            shutil.rmtree(old_backup, ignore_errors=True)
                    except (OSError, PermissionError) as e:
                        logger.warning("Could not remove backup %s: %s", old_backup, e)
                        continue

        except Exception as e:
            logger.error("Failed to cleanup old backups: %s", e)

    @contextmanager
    def protected_operation(self, operation_name: str, force_backup: bool = False):
        """Context manager for protected database operations"""
        operation_id = f"{operation_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = None

        try:
            # Log operation start
            self._log_operation(operation_id, "started", {"operation": operation_name})

            # Create backup if needed
            if force_backup or self._is_risky_operation(operation_name):
                backup_path = self._create_safety_backup(f"pre_{operation_name}")
                logger.info("🛡️  Pre-operation backup created for: %s", operation_name)

            # Yield control to the operation
            yield {
                "operation_id": operation_id,
                "backup_path": backup_path,
                "start_time": datetime.now(),
            }

            # Log successful completion
            self._log_operation(
                operation_id, "completed", {"operation": operation_name}
            )

        except Exception as e:
            # Log error and attempt recovery
            self._log_operation(
                operation_id,
                "failed",
                {
                    "operation": operation_name,
                    "error": str(e),
                    "backup_available": backup_path is not None,
                },
            )

            logger.error("🚨 Protected operation failed: %s - %s", operation_name, e)

            if backup_path:
                logger.info("🔄 Recovery backup available at: %s", backup_path)

            raise

    def _is_risky_operation(self, operation_name: str) -> bool:
        """Determine if an operation is risky and needs backup"""
        risky_operations = [
            "collection_delete",
            "database_reset",
            "bulk_update",
            "schema_migration",
            "collection_recreate",
        ]
        return any(risky in operation_name.lower() for risky in risky_operations)

    def _log_operation(self, operation_id: str, status: str, metadata: dict):
        """Log database operation"""
        log_entry = {
            "operation_id": operation_id,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "metadata": metadata,
        }

        self.operation_log.append(log_entry)

        # Keep log size manageable
        if len(self.operation_log) > self.max_log_entries:
            self.operation_log = self.operation_log[-self.max_log_entries // 2 :]

        # Save critical operations to file
        if status == "failed":
            self._save_critical_log(log_entry)

    def _save_critical_log(self, log_entry: dict):
        """Save critical operations to persistent log"""
        log_file = self.backup_dir / "critical_operations.log"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_health_status(self) -> dict:
        """Get protection service health status"""
        recent_operations = [
            op
            for op in self.operation_log
            if datetime.fromisoformat(op["timestamp"])
            > datetime.now() - timedelta(hours=24)
        ]

        failed_operations = [op for op in recent_operations if op["status"] == "failed"]

        return {
            "protection_active": self.protection_active,
            "last_backup": self.last_backup.isoformat() if self.last_backup else None,
            "backup_count": len(list(self.backup_dir.glob("*_backup_*"))),
            "recent_operations": len(recent_operations),
            "failed_operations": len(failed_operations),
            "status": "healthy" if len(failed_operations) == 0 else "warning",
        }

    def emergency_backup(self) -> Optional[Path]:
        """Create emergency backup immediately"""
        logger.warning("🚨 Emergency backup triggered!")
        return self._create_safety_backup("emergency_backup")


# Global protection service instance
_protection_service: Optional[DatabaseProtectionService] = None


def get_protection_service() -> DatabaseProtectionService:
    """Get the global protection service instance"""
    global _protection_service
    if _protection_service is None:
        _protection_service = DatabaseProtectionService()
        _protection_service.start_protection()
    return _protection_service


def protected_db_operation(operation_name: str, force_backup: bool = False):
    """Decorator for protecting database operations"""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            protection = get_protection_service()
            with protection.protected_operation(operation_name, force_backup):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Example usage:
# @protected_db_operation("collection_recreate", force_backup=True)
# def recreate_collection():
#     # Your risky database operation here
#     pass
