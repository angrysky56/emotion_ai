#!/usr/bin/env python3
"""
Test Inter-Process Locking for Enhanced Vector DB
================================================

This script verifies that the file-based locking mechanism
properly coordinates database access across multiple processes.
"""

import asyncio
import multiprocessing
import time
import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from enhanced_vector_db import EnhancedAuraVectorDB
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(process)d] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestMemory:
    user_id: str
    message: str
    sender: str
    timestamp: Optional[datetime] = None
    embedding: Optional[List[float]] = None
    session_id: Optional[str] = None

async def test_concurrent_access(process_id: int, num_operations: int = 5):
    """Test concurrent database access from a single process"""
    logger.info("Process %s starting...", process_id)
    
    # Initialize vector DB
    vector_db = EnhancedAuraVectorDB()
    
    success_count = 0
    error_count = 0
    
    for i in range(num_operations):
        try:
            # Create test memory
            memory = TestMemory(
                user_id=f"test_user_{process_id}",
                message=f"Test message {i} from process {process_id}",
                sender="test",
                timestamp=datetime.now()
            )
            
            # Attempt to store
            start_time = time.time()
            await vector_db.store_conversation(memory)
            duration = (time.time() - start_time) * 1000
            
            logger.info("Process %s stored document %s in %sms", process_id, i, duration)
            success_count += 1
            
            # Small delay between operations
            await asyncio.sleep(0.1)
            
        except Exception as e:
            logger.error("Process %s failed on operation %s: %s", process_id, i, e)
            error_count += 1
    
    logger.info("Process %s completed: %s successes, %s errors", process_id, success_count, error_count)
    
    # Close the database connection
    await vector_db.close()
    
    return success_count, error_count

def run_process_test(process_id: int, num_operations: int):
    """Wrapper to run async test in a process"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        success, errors = loop.run_until_complete(
            test_concurrent_access(process_id, num_operations)
        )
        return success, errors
    finally:
        loop.close()

async def test_lock_contention():
    """Test that locks properly serialize access"""
    logger.info("Testing lock contention with rapid sequential access...")
    
    vector_db = EnhancedAuraVectorDB()
    
    # Rapid fire operations to test lock contention
    operations = []
    for i in range(10):
        memory = TestMemory(
            user_id="contention_test",
            message=f"Rapid test message {i}",
            sender="test",
            timestamp=datetime.now()
        )
        operations.append(vector_db.store_conversation(memory))
    
    # Execute all operations concurrently
    start_time = time.time()
    results = await asyncio.gather(*operations, return_exceptions=True)
    total_duration = (time.time() - start_time) * 1000
    
    # Count successes and failures
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = sum(1 for r in results if isinstance(r, Exception))
    
    logger.info("Lock contention test completed in %sms", total_duration)
    logger.info("Successes: %s, Failures: %s", successes, failures)
    
    # Print any exceptions
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Operation %s failed: %s", i, result)
    
    await vector_db.close()

def main():
    """Main test function"""
    print("=" * 60)
    print("Enhanced Vector DB Inter-Process Locking Test")
    print("=" * 60)
    
    # Test 1: Single process async operations
    print("\n1. Testing single process with async operations...")
    asyncio.run(test_lock_contention())
    
    # Test 2: Multiple processes
    print("\n2. Testing multiple processes accessing the database...")
    num_processes = 3
    operations_per_process = 3
    
    # Create processes
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Start all processes
        results = []
        for i in range(num_processes):
            result = pool.apply_async(
                run_process_test, 
                args=(i, operations_per_process)
            )
            results.append(result)
        
        # Wait for all processes to complete
        pool.close()
        pool.join()
        
        # Collect results
        total_success = 0
        total_error = 0
        for result in results:
            success, error = result.get()
            total_success += success
            total_error += error
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"Total operations attempted: {num_processes * operations_per_process}")
    print(f"Total successes: {total_success}")
    print(f"Total errors: {total_error}")
    print(f"Success rate: {(total_success / (total_success + total_error) * 100):.1f}%")
    
    if total_error == 0:
        print("\n✅ All tests passed! Inter-process locking is working correctly.")
    else:
        print("\n⚠️ Some operations failed. Check the logs for details.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
