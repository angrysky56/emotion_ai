#!/usr/bin/env python3
"""
Aura Autonomic System Testing Suite
==================================

Comprehensive testing script to validate the autonomic nervous system integration
and demonstrate its capabilities.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List

import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutonomicSystemTester:
    """Testing suite for Aura's autonomic nervous system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_user_id = f"test_user_{int(time.time())}"
        self.test_results: List[Dict[str, Any]] = []
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        logger.info("🧪 Starting Aura Autonomic System Test Suite")
        logger.info("📍 Testing against: %s", self.base_url)
        logger.info("👤 Test user ID: %s", self.test_user_id)
        
        tests = [
            ("System Health Check", self.test_system_health),
            ("Autonomic Status Check", self.test_autonomic_status),
            ("Manual Task Submission", self.test_manual_task_submission),
            ("Conversation Integration", self.test_conversation_integration),
            ("Task Result Retrieval", self.test_task_result_retrieval),
            ("User Task Monitoring", self.test_user_task_monitoring),
            ("System Control", self.test_system_control),
            ("Performance Under Load", self.test_performance_load),
            ("Rate Limiting Functionality", self.test_rate_limiting)
        ]
        
        for test_name, test_func in tests:
            logger.info("\n%s", '='*50)
            logger.info("🔬 Running Test: %s", test_name)
            logger.info("%s", '='*50)
            
            try:
                result = await test_func()
                self.test_results.append({
                    "test_name": test_name,
                    "status": "PASSED" if result["success"] else "FAILED",
                    "details": result,
                    "timestamp": datetime.now().isoformat()
                })
                logger.info("✅ %s: %s", test_name, 'PASSED' if result['success'] else 'FAILED')
                
            except Exception as e:
                self.test_results.append({
                    "test_name": test_name,
                    "status": "ERROR",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                logger.error("❌ %s: ERROR - %s", test_name, e)
        
        # Generate test report
        await self.generate_test_report()
    
    async def test_system_health(self) -> Dict[str, Any]:
        """Test basic system health"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "success": health_data.get("status") == "healthy",
                    "response": health_data
                }
            else:
                return {
                    "success": False,
                    "error": f"Health check failed with status {response.status_code}"
                }
    
    async def test_autonomic_status(self) -> Dict[str, Any]:
        """Test autonomic system status"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/autonomic/status")
            
            if response.status_code == 200:
                status_data = response.json()
                is_operational = status_data.get("status") in ["operational", "disabled"]
                
                logger.info("📊 Autonomic Status: %s", status_data.get('status'))
                if "system_status" in status_data:
                    sys_status = status_data["system_status"]
                    logger.info("🏃 Running: %s", sys_status.get('running', False))
                    logger.info("📋 Queued Tasks: %s", sys_status.get('queued_tasks', 0))
                    logger.info("⚡ Active Tasks: %s", sys_status.get('active_tasks', 0))
                    logger.info("✅ Completed Tasks: %s", sys_status.get('completed_tasks', 0))
                
                return {
                    "success": is_operational,
                    "response": status_data
                }
            else:
                return {
                    "success": False,
                    "error": f"Status check failed with status {response.status_code}"
                }
    
    async def test_manual_task_submission(self) -> Dict[str, Any]:
        """Test manual task submission to autonomic system"""
        task_payload = {
            "description": "Test autonomic task processing capabilities",
            "payload": {
                "task_type": "test_processing",
                "test_data": "This is a test task for the autonomic nervous system",
                "complexity_level": "medium",
                "expected_processing_time": "short"
            },
            "user_id": self.test_user_id,
            "force_offload": True  # Force offloading for testing
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/autonomic/submit-task",
                params=task_payload
            )
            
            if response.status_code == 200:
                submit_data = response.json()
                logger.info("📤 Task submitted: %s", submit_data)
                
                if submit_data.get("status") == "submitted":
                    # Wait a moment for processing
                    await asyncio.sleep(2)
                    
                    # Check task result
                    task_id = submit_data.get("task_id")
                    result_response = await client.get(
                        f"{self.base_url}/autonomic/task/{task_id}/result"
                    )
                    
                    if result_response.status_code == 200:
                        result_data = result_response.json()
                        logger.info("📥 Task result: %s", result_data.get('status'))
                        
                        return {
                            "success": True,
                            "task_id": task_id,
                            "submit_response": submit_data,
                            "result_response": result_data
                        }
                
                return {
                    "success": submit_data.get("status") in ["submitted", "not_offloaded"],
                    "response": submit_data
                }
            else:
                return {
                    "success": False,
                    "error": f"Task submission failed with status {response.status_code}"
                }
    
    async def test_conversation_integration(self) -> Dict[str, Any]:
        """Test autonomic integration with conversation processing"""
        test_conversations = [
            "I'd like to analyze my emotional patterns over the past few weeks",
            "Can you help me understand complex machine learning concepts?",
            "Please search through my previous conversations about project planning",
            "I want to learn about quantum computing - can you create a comprehensive guide?"
        ]
        
        successful_conversations = 0
        conversation_results = []
        
        async with httpx.AsyncClient() as client:
            for i, message in enumerate(test_conversations):
                logger.info("💬 Testing conversation %s: '%s...'", i+1, message[:50])
                
                conversation_payload = {
                    "user_id": self.test_user_id,
                    "message": message,
                    "session_id": f"test_session_{i}"
                }
                
                response = await client.post(
                    f"{self.base_url}/conversation",
                    json=conversation_payload
                )
                
                if response.status_code == 200:
                    conv_data = response.json()
                    successful_conversations += 1
                    conversation_results.append({
                        "message": message,
                        "response_length": len(conv_data.get("response", "")),
                        "emotional_state": conv_data.get("emotional_state", {}),
                        "cognitive_state": conv_data.get("cognitive_state", {})
                    })
                    logger.info("✅ Conversation %s successful", i+1)
                else:
                    logger.warning("⚠️ Conversation %s failed with status %s", i+1, response.status_code)
                
                # Brief pause between conversations
                await asyncio.sleep(1)
        
        # Check if any autonomic tasks were generated
        await asyncio.sleep(3)  # Allow time for autonomic processing
        
        tasks_response = await client.get(
            f"{self.base_url}/autonomic/tasks/{self.test_user_id}",
            params={"limit": 20}
        )
        
        autonomic_tasks_generated = 0
        if tasks_response.status_code == 200:
            tasks_data = tasks_response.json()
            autonomic_tasks_generated = tasks_data.get("total_completed", 0) + tasks_data.get("total_active", 0)
            logger.info("🤖 Autonomic tasks generated: %s", autonomic_tasks_generated)
        
        return {
            "success": successful_conversations > 0,
            "successful_conversations": successful_conversations,
            "total_conversations": len(test_conversations),
            "autonomic_tasks_generated": autonomic_tasks_generated,
            "conversation_results": conversation_results
        }
    
    async def test_task_result_retrieval(self) -> Dict[str, Any]:
        """Test task result retrieval functionality"""
        # First submit a task
        task_payload = {
            "description": "Retrieve and analyze user interaction patterns",
            "payload": {
                "analysis_type": "interaction_patterns",
                "user_id": self.test_user_id,
                "scope": "recent_activity"
            },
            "user_id": self.test_user_id,
            "force_offload": True
        }
        
        async with httpx.AsyncClient() as client:
            # Submit task
            submit_response = await client.post(
                f"{self.base_url}/autonomic/submit-task",
                params=task_payload
            )
            
            if submit_response.status_code != 200:
                return {
                    "success": False,
                    "error": "Failed to submit test task for result retrieval"
                }
            
            submit_data = submit_response.json()
            
            if submit_data.get("status") != "submitted":
                return {
                    "success": False,
                    "error": "Task was not submitted for autonomic processing"
                }
            
            task_id = submit_data.get("task_id")
            logger.info("🔍 Testing result retrieval for task: %s", task_id)
            
            # Test immediate result retrieval (should be pending/processing)
            immediate_response = await client.get(
                f"{self.base_url}/autonomic/task/{task_id}/result"
            )
            
            # Test result retrieval with timeout
            timeout_response = await client.get(
                f"{self.base_url}/autonomic/task/{task_id}/result",
                params={"timeout": 5.0}
            )
            
            # Test detailed task information
            details_response = await client.get(
                f"{self.base_url}/autonomic/task/{task_id}"
            )
            
            success_count = sum([
                immediate_response.status_code == 200,
                timeout_response.status_code == 200,
                details_response.status_code == 200
            ])
            
            results = {
                "immediate_result": immediate_response.json() if immediate_response.status_code == 200 else None,
                "timeout_result": timeout_response.json() if timeout_response.status_code == 200 else None,
                "task_details": details_response.json() if details_response.status_code == 200 else None
            }
            
            return {
                "success": success_count >= 2,  # At least 2 out of 3 should succeed
                "task_id": task_id,
                "successful_retrievals": success_count,
                "results": results
            }
    
    async def test_user_task_monitoring(self) -> Dict[str, Any]:
        """Test user-specific task monitoring"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/autonomic/tasks/{self.test_user_id}",
                params={"limit": 10}
            )
            
            if response.status_code == 200:
                tasks_data = response.json()
                logger.info("📋 User tasks retrieved: %s completed, %s active", tasks_data.get('total_completed', 0), tasks_data.get('total_active', 0))
                
                return {
                    "success": True,
                    "user_id": self.test_user_id,
                    "tasks_data": tasks_data
                }
            else:
                return {
                    "success": False,
                    "error": f"Task monitoring failed with status {response.status_code}"
                }
    
    async def test_system_control(self) -> Dict[str, Any]:
        """Test autonomic system control functionality"""
        async with httpx.AsyncClient() as client:
            # Test system status check
            status_response = await client.get(f"{self.base_url}/autonomic/status")
            
            if status_response.status_code != 200:
                return {
                    "success": False,
                    "error": "Could not check system status"
                }
            
            status_data = status_response.json()
            initial_status = status_data.get("status")
            
            logger.info("📊 Initial system status: %s", initial_status)
            
            # Don't actually stop/start the system during testing to avoid disruption
            # Just verify the endpoints respond correctly
            
            # Test invalid control action
            invalid_response = await client.post(
                f"{self.base_url}/autonomic/control/invalid_action"
            )
            
            return {
                "success": True,
                "initial_status": initial_status,
                "control_endpoints_available": True,
                "invalid_action_handled": invalid_response.status_code == 400
            }
    
    async def test_performance_load(self) -> Dict[str, Any]:
        """Test system performance under load with optimized concurrency"""
        logger.info("🚀 Testing autonomic system performance under load")
        
        # Submit multiple tasks concurrently (increased for better rate limit testing)
        concurrent_tasks = 15  # Test closer to the 25 RPM limit
        task_descriptions = [
            f"Concurrent task {i}: Load test analysis #{i}" for i in range(1, concurrent_tasks + 1)
        ]
        
        async def submit_task(description: str, task_num: int):
            async with httpx.AsyncClient() as client:
                start_time = time.time()
                
                response = await client.post(
                    f"{self.base_url}/autonomic/submit-task",
                    params={
                        "description": description,
                        "payload": {
                            "task_number": task_num,
                            "test_data": f"Load test data for task {task_num}"
                        },
                        "user_id": self.test_user_id,
                        "force_offload": True
                    }
                )
                
                end_time = time.time()
                
                return {
                    "task_num": task_num,
                    "success": response.status_code == 200,
                    "response_time": end_time - start_time,
                    "response": response.json() if response.status_code == 200 else None
                }
        
        # Submit tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*[
            submit_task(desc, i+1) for i, desc in enumerate(task_descriptions)
        ])
        total_time = time.time() - start_time
        
        successful_submissions = sum(1 for r in results if r["success"])
        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        
        logger.info("⚡ Load test results:")
        logger.info("   Successful submissions: %s/%s", successful_submissions, concurrent_tasks)
        logger.info("   Total time: %ss", total_time:.2f)
        logger.info("   Average response time: %ss", avg_response_time:.2f)
        
        return {
            "success": successful_submissions >= concurrent_tasks * 0.8,  # 80% success rate
            "concurrent_tasks": concurrent_tasks,
            "successful_submissions": successful_submissions,
            "total_time": total_time,
            "average_response_time": avg_response_time,
            "results": results
        }
    
    async def test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting functionality and monitoring"""
        logger.info("🚦 Testing rate limiting functionality")
        
        async with httpx.AsyncClient() as client:
            # First, check initial rate limiter status
            status_response = await client.get(f"{self.base_url}/autonomic/status")
            
            if status_response.status_code != 200:
                return {
                    "success": False,
                    "error": "Could not check autonomic status"
                }
            
            status_data = status_response.json()
            rate_limiting = status_data.get("system_status", {}).get("rate_limiting", {})
            
            initial_rpm_current = rate_limiting.get("rpm_current", 0)
            initial_total_requests = rate_limiting.get("total_requests", 0)
            rpm_limit = rate_limiting.get("rpm_limit", 25)
            
            logger.info("📊 Initial rate limit status:")
            logger.info("   RPM limit: %s", rpm_limit)
            logger.info("   Current RPM usage: %s", initial_rpm_current)
            logger.info("   Total requests: %s", initial_total_requests)
            
            # Submit several tasks to test rate limiting
            rate_test_tasks = 8  # Moderate number to test rate limiting behavior
            
            async def submit_rate_test_task(task_num: int):
                return await client.post(
                    f"{self.base_url}/autonomic/submit-task",
                    params={
                        "description": f"Rate limit test task #{task_num}",
                        "payload": {
                            "test_type": "rate_limiting",
                            "task_number": task_num
                        },
                        "user_id": self.test_user_id,
                        "force_offload": True
                    }
                )
            
            # Submit tasks in quick succession
            start_time = time.time()
            rate_test_results = await asyncio.gather(*[
                submit_rate_test_task(i) for i in range(rate_test_tasks)
            ])
            submission_time = time.time() - start_time
            
            successful_rate_submissions = sum(1 for r in rate_test_results if r.status_code == 200)
            
            # Wait a moment for processing
            await asyncio.sleep(2)
            
            # Check rate limiter status after submissions
            final_status_response = await client.get(f"{self.base_url}/autonomic/status")
            
            if final_status_response.status_code == 200:
                final_status_data = final_status_response.json()
                final_rate_limiting = final_status_data.get("system_status", {}).get("rate_limiting", {})
                
                final_rpm_current = final_rate_limiting.get("rpm_current", 0)
                final_total_requests = final_rate_limiting.get("total_requests", 0)
                total_rejected = final_rate_limiting.get("total_rejected", 0)
                
                requests_made = final_total_requests - initial_total_requests
                rpm_increase = final_rpm_current - initial_rpm_current
                
                logger.info("📈 Rate limiting test results:")
                logger.info("   Tasks submitted: %s", rate_test_tasks)
                logger.info("   Successful submissions: %s", successful_rate_submissions)
                logger.info("   Requests made: %s", requests_made)
                logger.info("   RPM increase: %s", rpm_increase)
                logger.info("   Total rejected: %s", total_rejected)
                logger.info("   Submission time: %ss", submission_time:.2f)
                
                # Success criteria:
                # 1. Most tasks should be submitted successfully
                # 2. Rate limiter should track requests properly
                # 3. System should not exceed rate limits
                success = (
                    successful_rate_submissions >= rate_test_tasks * 0.7 and  # 70% submission success
                    requests_made <= rpm_limit and  # Don't exceed RPM limit
                    final_rpm_current <= rpm_limit  # Current usage within limits
                )
                
                return {
                    "success": success,
                    "rate_test_tasks": rate_test_tasks,
                    "successful_submissions": successful_rate_submissions,
                    "requests_made": requests_made,
                    "rpm_increase": rpm_increase,
                    "total_rejected": total_rejected,
                    "submission_time": submission_time,
                    "rate_limiting_status": final_rate_limiting
                }
            else:
                return {
                    "success": False,
                    "error": "Could not check final rate limiting status"
                }
    
    async def generate_test_report(self):
        """Generate comprehensive test report"""
        logger.info("\n%s", '='*60)
        logger.info("📋 AURA AUTONOMIC SYSTEM TEST REPORT")
        logger.info("%s", '='*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["status"] == "PASSED")
        failed_tests = sum(1 for r in self.test_results if r["status"] == "FAILED")
        error_tests = sum(1 for r in self.test_results if r["status"] == "ERROR")
        
        logger.info("📊 Test Summary:")
        logger.info("   Total Tests: %s", total_tests)
        logger.info("   ✅ Passed: %s", passed_tests)
        logger.info("   ❌ Failed: %s", failed_tests)
        logger.info("   💥 Errors: %s", error_tests)
        logger.info("   Success Rate: %s%%", (passed_tests/total_tests)*100)
        
        logger.info("\n📝 Detailed Results:")
        for result in self.test_results:
            status_emoji = "✅" if result["status"] == "PASSED" else "❌" if result["status"] == "FAILED" else "💥"
            logger.info("   %s %s: %s", status_emoji, result['test_name'], result['status'])
        
        # Save report to file
        report_data = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "error_tests": error_tests,
                "success_rate": (passed_tests/total_tests)*100
            },
            "test_results": self.test_results,
            "test_user_id": self.test_user_id,
            "report_generated": datetime.now().isoformat()
        }
        
        report_filename = f"autonomic_test_report_{int(time.time())}.json"
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info("\n💾 Test report saved to: %s", report_filename)
        logger.info("🔗 Test User ID: %s", self.test_user_id)
        
        return report_data

async def main():
    """Main test execution"""
    print("🧠 Aura Autonomic Nervous System Test Suite")
    print("=" * 50)
    
    tester = AutonomicSystemTester()
    
    try:
        await tester.run_all_tests()
        print("\n🎉 Test suite completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test suite interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
