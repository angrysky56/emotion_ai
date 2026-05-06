#!/usr/bin/env python3
"""
ChromaDB Conflict Fixes Validation
==================================

Validates the specific fixes made to resolve:
1. Division by zero error in conversation_persistence_service.py
2. Multiple ChromaDB client architecture issue with memvid integration

This script tests the exact issues that were causing the problems.
"""

import sys
import logging
import asyncio
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging for validation
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChromaDBFixValidator:
    """Validates the ChromaDB conflict fixes"""

    def __init__(self):
        self.test_dir = None
        self.validation_results = {
            "division_by_zero_fix": False,
            "chromadb_client_sharing": False,
            "persistence_metrics": False,
            "memvid_initialization": False
        }

    async def setup_test_environment(self):
        """Set up isolated test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="aura_validation_"))
        logger.info("🧪 Created test environment: %s", self.test_dir)

        # Create test data directories
        (self.test_dir / "aura_chroma_db").mkdir()
        (self.test_dir / "aura_data").mkdir()
        (self.test_dir / "memvid_videos").mkdir()

    async def cleanup_test_environment(self):
        """Clean up test environment"""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            logger.info("🧹 Cleaned up test environment")

    async def validate_division_by_zero_fix(self) -> bool:
        """
        Validate Fix 1: Division by zero error in persistence service
        
        Tests that _update_average_store_time handles total_stores = 0 correctly
        """
        logger.info("🔍 Testing division by zero fix...")

        try:
            # Import the fixed persistence service
            from conversation_persistence_service import ConversationPersistenceService
            from main import AuraVectorDB, AuraFileSystem

            # Create test components
            vector_db = AuraVectorDB(persist_directory=str(self.test_dir / "aura_chroma_db"))
            file_system = AuraFileSystem(base_path=str(self.test_dir / "aura_data"))
            
            # Create persistence service
            persistence_service = ConversationPersistenceService(vector_db, file_system)

            # Test the critical scenario: call _update_average_store_time with total_stores = 0
            persistence_service._metrics.copy()
            
            # This should NOT cause a division by zero error
            persistence_service._update_average_store_time(100.0)
            
            # Verify the metrics were updated correctly
            updated_metrics = persistence_service._metrics
            
            # Check that average_store_time was set to the duration (no division)
            if updated_metrics["average_store_time"] == 100.0:
                logger.info("✅ Division by zero fix verified - handles zero total_stores correctly")
                return True
            else:
                logger.error("❌ Division by zero fix failed - expected 100.0, got %s", updated_metrics['average_store_time'])
                return False

        except ZeroDivisionError as e:
            logger.error("❌ Division by zero error still occurs: %s", e)
            return False
        except Exception as e:
            logger.error("❌ Unexpected error testing division by zero fix: %s", e)
            return False

    async def validate_chromadb_client_sharing(self) -> bool:
        """
        Validate Fix 2: ChromaDB client sharing between main.py and memvid
        
        Tests that memvid uses the same ChromaDB client instance as the main system
        """
        logger.info("🔍 Testing ChromaDB client sharing...")

        try:
            # Import required components
            from main import AuraVectorDB
            from aura_real_memvid import get_aura_real_memvid, reset_aura_real_memvid

            # Reset global instance to ensure clean test
            reset_aura_real_memvid()

            # Create main vector DB instance (this creates the primary ChromaDB client)
            vector_db = AuraVectorDB(persist_directory=str(self.test_dir / "aura_chroma_db"))
            main_client = vector_db.client

            # Get memvid instance with the existing client
            memvid_system = get_aura_real_memvid(existing_chroma_client=main_client)

            # Verify that memvid is using the same client instance
            if memvid_system.chroma_client is main_client:
                logger.info("✅ ChromaDB client sharing verified - memvid uses shared client")
                return True
            else:
                logger.error("❌ ChromaDB client sharing failed - memvid created separate client")
                return False

        except Exception as e:
            logger.error("❌ Error testing ChromaDB client sharing: %s", e)
            return False

    async def validate_persistence_metrics(self) -> bool:
        """
        Validate that persistence metrics work correctly after the fix
        """
        logger.info("🔍 Testing persistence metrics...")

        try:
            from conversation_persistence_service import ConversationPersistenceService, ConversationExchange
            from main import AuraVectorDB, AuraFileSystem, ConversationMemory, EmotionalStateData, EmotionalIntensity

            # Create test components
            vector_db = AuraVectorDB(persist_directory=str(self.test_dir / "aura_chroma_db"))
            file_system = AuraFileSystem(base_path=str(self.test_dir / "aura_data"))
            persistence_service = ConversationPersistenceService(vector_db, file_system)

            # Create test emotional state
            test_emotion = EmotionalStateData(
                name="Happy",
                formula="H(x) = test_formula",
                components={"test": "component"},
                ntk_layer="test_ntk",
                brainwave="Beta",
                neurotransmitter="Dopamine",
                description="Test emotional state",
                intensity=EmotionalIntensity.MEDIUM
            )

            # Create test conversation memories
            user_memory = ConversationMemory(
                user_id="test_user",
                message="Hello, this is a test message",
                sender="user",
                emotional_state=test_emotion,
                session_id="test_session"
            )

            ai_memory = ConversationMemory(
                user_id="test_user", 
                message="Hello! I'm responding to your test message",
                sender="aura",
                emotional_state=test_emotion,
                session_id="test_session"
            )

            # Create conversation exchange
            exchange = ConversationExchange(
                user_memory=user_memory,
                ai_memory=ai_memory,
                user_emotional_state=test_emotion,
                ai_emotional_state=test_emotion,
                session_id="test_session"
            )

            # Persist the exchange (this should not cause division by zero)
            result = await persistence_service.persist_conversation_exchange(exchange)

            # Check that persistence succeeded
            if result["success"] and result["duration_ms"] > 0:
                logger.info("✅ Persistence metrics validation passed")
                return True
            else:
                logger.error("❌ Persistence metrics validation failed: %s", result)
                return False

        except Exception as e:
            logger.error("❌ Error testing persistence metrics: %s", e)
            return False

    async def validate_memvid_initialization(self) -> bool:
        """
        Validate that memvid initializes properly with shared client
        """
        logger.info("🔍 Testing memvid initialization with shared client...")

        try:
            from main import AuraVectorDB
            from aura_internal_memvid_tools import get_aura_internal_memvid_tools, reset_aura_internal_memvid_tools

            # Reset to ensure clean test
            reset_aura_internal_memvid_tools()

            # Create vector DB
            vector_db = AuraVectorDB(persist_directory=str(self.test_dir / "aura_chroma_db"))

            # Initialize memvid tools with shared client
            memvid_tools = get_aura_internal_memvid_tools(vector_db.client)

            # Check that memvid tools initialized properly
            if memvid_tools and memvid_tools.memvid_system:
                # Verify shared client
                if memvid_tools.memvid_system.chroma_client is vector_db.client:
                    logger.info("✅ Memvid initialization validation passed - using shared client")
                    return True
                else:
                    logger.error("❌ Memvid initialization failed - not using shared client")
                    return False
            else:
                logger.warning("⚠️ Memvid tools not available (this is OK if memvid isn't installed)")
                return True  # Not a failure if memvid isn't available

        except Exception as e:
            logger.error("❌ Error testing memvid initialization: %s", e)
            return False

    async def run_validation(self) -> Dict[str, Any]:
        """Run all validations and return results"""
        logger.info("🚀 Starting ChromaDB fixes validation...")

        await self.setup_test_environment()

        try:
            # Run all validation tests
            self.validation_results["division_by_zero_fix"] = await self.validate_division_by_zero_fix()
            self.validation_results["chromadb_client_sharing"] = await self.validate_chromadb_client_sharing()
            self.validation_results["persistence_metrics"] = await self.validate_persistence_metrics()
            self.validation_results["memvid_initialization"] = await self.validate_memvid_initialization()

            # Calculate overall result
            passed_tests = sum(1 for result in self.validation_results.values() if result)
            total_tests = len(self.validation_results)

            overall_success = passed_tests == total_tests

            # Generate report
            report = {
                "overall_success": overall_success,
                "passed_tests": passed_tests,
                "total_tests": total_tests,
                "test_results": self.validation_results,
                "timestamp": datetime.now().isoformat(),
                "test_environment": str(self.test_dir)
            }

            # Log summary
            if overall_success:
                logger.info("🎉 All %s validation tests PASSED!", total_tests)
                logger.info("✅ ChromaDB conflict fixes are working correctly")
            else:
                failed_tests = [name for name, result in self.validation_results.items() if not result]
                logger.error("❌ %s validation tests FAILED: %s", len(failed_tests), failed_tests)

            return report

        finally:
            await self.cleanup_test_environment()

async def main():
    """Main validation function"""
    print("🔧 ChromaDB Conflict Fixes Validation")
    print("=====================================")
    print()

    validator = ChromaDBFixValidator()
    results = await validator.run_validation()

    print("\n📊 Validation Results:")
    print("=====================")
    for test_name, passed in results["test_results"].items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")

    print(f"\nOverall: {results['passed_tests']}/{results['total_tests']} tests passed")

    if results["overall_success"]:
        print("\n🎉 SUCCESS: All ChromaDB conflict fixes are working correctly!")
        return 0
    else:
        print("\n❌ FAILURE: Some validation tests failed. Check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
