"""
Aura Autonomic Nervous System
============================

Advanced task offloading system for Aura AI companion that intelligently delegates
computational tasks to a secondary model (gemini-2.0-flash-lite) to optimize
resource usage and improve response quality.

This system acts as Aura's "autonomic nervous system" - handling background
processing while the main consciousness focuses on user interaction.
"""

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from google.genai import types

from aura_backend.aura_internal_tools import AuraInternalTools
from aura_backend.mcp_to_gemini_bridge import MCPGeminiBridge

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Sophisticated rate limiting implementation for API request management

    Tracks both requests per minute (RPM) and requests per day (RPD) with
    sliding window algorithms for accurate rate limit enforcement.
    """

    def __init__(self, rpm_limit: int, rpd_limit: int):
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit

        # Sliding window for RPM tracking (60-second windows)
        self.minute_requests: deque = deque()

        # Daily request tracking
        self.daily_requests = 0
        self.daily_reset_time = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        # Statistics tracking
        self.total_requests = 0
        self.total_rejected = 0
        self.last_request_time: Optional[datetime] = None

        logger.info("🚦 Rate limiter initialized: %s RPM, %s RPD", rpm_limit, rpd_limit)

    async def can_make_request(self) -> bool:
        """Check if a request can be made without exceeding rate limits"""
        current_time = datetime.now()

        # Clean up old minute requests (sliding window)
        cutoff_time = current_time - timedelta(minutes=1)
        while self.minute_requests and self.minute_requests[0] < cutoff_time:
            self.minute_requests.popleft()

        # Reset daily counter if needed
        if current_time >= self.daily_reset_time:
            self.daily_requests = 0
            self.daily_reset_time = current_time.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
            logger.info("🔄 Daily rate limit counter reset")

        # Check both RPM and RPD limits
        rpm_available = len(self.minute_requests) < self.rpm_limit
        rpd_available = self.daily_requests < self.rpd_limit

        return rpm_available and rpd_available

    async def acquire(self) -> bool:
        """
        Attempt to acquire a request slot

        Returns:
            True if request can proceed, False if rate limited
        """
        if not await self.can_make_request():
            self.total_rejected += 1
            return False

        current_time = datetime.now()

        # Record the request
        self.minute_requests.append(current_time)
        self.daily_requests += 1
        self.total_requests += 1
        self.last_request_time = current_time

        return True

    async def wait_for_availability(self, max_wait_seconds: float = 60.0) -> bool:
        """
        Wait until a request slot becomes available

        Args:
            max_wait_seconds: Maximum time to wait in seconds

        Returns:
            True if slot became available, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            if await self.can_make_request():
                return await self.acquire()

            # Calculate optimal wait time
            if self.minute_requests:
                # Wait until the oldest request in the current minute expires
                oldest_request = self.minute_requests[0]
                wait_time = (
                    oldest_request + timedelta(minutes=1) - datetime.now()
                ).total_seconds()
                wait_time = max(0.1, min(wait_time, 5.0))  # Wait 0.1-5 seconds
            else:
                wait_time = 0.1  # Brief wait if no current requests

            await asyncio.sleep(wait_time)

        logger.warning("⏰ Rate limiter timeout after %ss", max_wait_seconds)
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status and statistics"""
        current_time = datetime.now()

        # Clean up old requests for accurate counting
        cutoff_time = current_time - timedelta(minutes=1)
        current_minute_requests = sum(
            1 for req_time in self.minute_requests if req_time >= cutoff_time
        )

        return {
            "rpm_limit": self.rpm_limit,
            "rpm_current": current_minute_requests,
            "rpm_available": self.rpm_limit - current_minute_requests,
            "rpd_limit": self.rpd_limit,
            "rpd_current": self.daily_requests,
            "rpd_available": self.rpd_limit - self.daily_requests,
            "total_requests": self.total_requests,
            "total_rejected": self.total_rejected,
            "rejection_rate": (
                self.total_rejected / max(1, self.total_requests + self.total_rejected)
            )
            * 100,
            "last_request": (
                self.last_request_time.isoformat() if self.last_request_time else None
            ),
            "daily_reset_time": self.daily_reset_time.isoformat(),
        }


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, Enum):
    MCP_TOOL_CALL = "mcp_tool_call"
    DATA_ANALYSIS = "data_analysis"
    CODE_GENERATION = "code_generation"
    MEMORY_SEARCH = "memory_search"
    PATTERN_ANALYSIS = "pattern_analysis"
    COMPLEX_REASONING = "complex_reasoning"
    BACKGROUND_PROCESSING = "background_processing"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AutonomicTask:
    """Represents a task that can be offloaded to the autonomic system"""

    task_id: str
    task_type: TaskType
    priority: TaskPriority
    description: str
    payload: Dict[str, Any]
    user_id: str
    session_id: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class TaskClassifier:
    """Intelligent task classification system to determine offload candidates"""

    def __init__(self, threshold: str = "medium"):
        self.threshold = threshold
        self._complexity_weights = {
            "tool_calls": 0.8,
            "data_processing": 0.9,
            "analysis": 0.7,
            "memory_operations": 0.6,
            "code_generation": 0.8,
            "pattern_recognition": 0.9,
        }

    async def should_offload_task(
        self,
        task_description: str,
        task_payload: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, TaskType, TaskPriority]:
        """
        Analyze whether a task should be offloaded to autonomic system

        Returns:
            Tuple of (should_offload, task_type, priority)
        """
        # Analyze task complexity and type
        task_analysis = await self._analyze_task_complexity(
            task_description, task_payload
        )

        task_type = self._classify_task_type(task_description, task_payload)
        priority = self._determine_priority(task_analysis, user_context)

        # Decision logic based on threshold
        should_offload = self._make_offload_decision(task_analysis, priority)

        return should_offload, task_type, priority

    async def _analyze_task_complexity(
        self, description: str, payload: Dict[str, Any]
    ) -> Dict[str, float]:
        """Analyze task complexity across multiple dimensions"""

        complexity_indicators = {
            "computational_load": 0.0,
            "data_volume": 0.0,
            "tool_complexity": 0.0,
            "reasoning_depth": 0.0,
            "time_sensitivity": 0.0,
        }

        # Analyze computational load
        if any(
            keyword in description.lower()
            for keyword in [
                "analyze",
                "process",
                "compute",
                "calculate",
                "generate",
                "search",
            ]
        ):
            complexity_indicators["computational_load"] += 0.3

        # Analyze data volume
        if payload.get("data_size", 0) > 1000:
            complexity_indicators["data_volume"] += 0.4

        # Analyze tool complexity
        if "tool_name" in payload:
            tool_complexity_map = {
                "search_all_memories": 0.7,
                "analyze_emotional_patterns": 0.8,
                "create_knowledge_summary": 0.6,
                "archive_old_conversations": 0.9,
                "complex_analysis": 0.9,
            }
            tool_name = payload.get("tool_name", "")
            complexity_indicators["tool_complexity"] = tool_complexity_map.get(
                tool_name, 0.3
            )

        # Analyze reasoning depth
        reasoning_keywords = [
            "deep",
            "complex",
            "comprehensive",
            "detailed",
            "thorough",
        ]
        if any(keyword in description.lower() for keyword in reasoning_keywords):
            complexity_indicators["reasoning_depth"] += 0.5

        return complexity_indicators

    def _classify_task_type(
        self, description: str, payload: Dict[str, Any]
    ) -> TaskType:
        """Classify the type of task based on description and payload"""

        description_lower = description.lower()

        if "tool_name" in payload or "function_call" in payload:
            return TaskType.MCP_TOOL_CALL
        elif any(
            keyword in description_lower
            for keyword in ["analyze", "analysis", "pattern"]
        ):
            return TaskType.DATA_ANALYSIS
        elif any(
            keyword in description_lower for keyword in ["code", "generate", "script"]
        ):
            return TaskType.CODE_GENERATION
        elif any(
            keyword in description_lower for keyword in ["search", "memory", "recall"]
        ):
            return TaskType.MEMORY_SEARCH
        elif any(
            keyword in description_lower for keyword in ["reason", "think", "complex"]
        ):
            return TaskType.COMPLEX_REASONING
        else:
            return TaskType.BACKGROUND_PROCESSING

    def _determine_priority(
        self,
        complexity_analysis: Dict[str, float],
        user_context: Optional[Dict[str, Any]],
    ) -> TaskPriority:
        """Determine task priority based on complexity and context"""

        # Calculate overall complexity score
        complexity_score = sum(complexity_analysis.values()) / len(complexity_analysis)

        # Adjust based on user context
        if user_context:
            if user_context.get("is_urgent", False):
                complexity_score += 0.3
            if user_context.get("user_waiting", True):
                complexity_score += 0.2

        # Map complexity to priority
        if complexity_score >= 0.8:
            return TaskPriority.CRITICAL
        elif complexity_score >= 0.6:
            return TaskPriority.HIGH
        elif complexity_score >= 0.4:
            return TaskPriority.MEDIUM
        else:
            return TaskPriority.LOW

    def _make_offload_decision(
        self, complexity_analysis: Dict[str, float], priority: TaskPriority
    ) -> bool:
        """Make the final decision on whether to offload"""

        # Threshold mapping
        threshold_map = {"low": 0.3, "medium": 0.5, "high": 0.7}

        threshold_value = threshold_map.get(self.threshold, 0.5)
        complexity_score = sum(complexity_analysis.values()) / len(complexity_analysis)

        # Decision logic
        if priority == TaskPriority.CRITICAL:
            return (
                complexity_score > threshold_value * 0.8
            )  # Lower threshold for critical
        elif priority == TaskPriority.HIGH:
            return complexity_score > threshold_value
        else:
            return (
                complexity_score > threshold_value * 1.2
            )  # Higher threshold for low priority


class AutonomicProcessor:
    """Core processor for autonomic task execution with rate limiting"""

    def __init__(
        self,
        autonomic_model: str = "gemini-2.0-flash-lite",
        max_output_tokens: int = 100000,
        timeout_seconds: int = 30,
        rpm_limit: int = 25,
        rpd_limit: int = 1200,
    ):
        self.autonomic_model = autonomic_model
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(rpm_limit, rpd_limit)

        self.execution_stats = {
            "tasks_processed": 0,
            "tasks_successful": 0,
            "tasks_failed": 0,
            "tasks_rate_limited": 0,
            "average_execution_time": 0.0,
            "total_execution_time": 0.0,
        }

    async def execute_task(
        self,
        task: AutonomicTask,
        mcp_bridge: Optional[MCPGeminiBridge] = None,
        internal_tools: Optional[AuraInternalTools] = None,
    ) -> AutonomicTask:
        """Execute a task using the autonomic processor"""

        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now()
        start_time = time.time()

        try:
            logger.info(
                "🤖 Autonomic processor executing task: %s (%s)",
                task.task_id,
                task.task_type.value,
            )

            # Route task to appropriate handler
            if task.task_type == TaskType.MCP_TOOL_CALL:
                result = await self._execute_mcp_tool_task(
                    task, mcp_bridge, internal_tools
                )
            elif task.task_type == TaskType.DATA_ANALYSIS:
                result = await self._execute_analysis_task(task)
            elif task.task_type == TaskType.CODE_GENERATION:
                result = await self._execute_code_generation_task(task)
            elif task.task_type == TaskType.MEMORY_SEARCH:
                result = await self._execute_memory_search_task(task, internal_tools)
            else:
                result = await self._execute_general_task(task)

            # Update task with results
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()

            # Update stats
            execution_time = (time.time() - start_time) * 1000
            task.execution_time_ms = execution_time
            self._update_execution_stats(execution_time, True)

            logger.info(
                "✅ Autonomic task completed: %s (%s.1fms)",
                task.task_id,
                execution_time,
            )
            return task

        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = f"Task exceeded timeout of {self.timeout_seconds} seconds"
            task.completed_at = datetime.now()
            self._update_execution_stats((time.time() - start_time) * 1000, False)
            logger.warning("⏰ Autonomic task timeout: %s", task.task_id)
            return task

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            self._update_execution_stats((time.time() - start_time) * 1000, False)
            logger.error("❌ Autonomic task failed: %s - %s", task.task_id, e)
            return task

    async def _execute_mcp_tool_task(
        self,
        task: AutonomicTask,
        mcp_bridge: Optional[MCPGeminiBridge],
        internal_tools: Optional[AuraInternalTools],
    ) -> Dict[str, Any]:
        """Execute MCP tool calls through autonomic processor"""

        tool_name = task.payload.get("tool_name")
        arguments = task.payload.get("arguments", {})

        # Try internal tools first
        if internal_tools and tool_name and tool_name.startswith("aura."):
            result = await internal_tools.execute_tool(tool_name, arguments)
            return {"tool_result": result, "execution_method": "internal_tools"}

        # Use MCP bridge for external tools
        elif mcp_bridge and tool_name:
            # Create a mock function call for the MCP bridge
            from google.genai.types import FunctionCall

            function_call = FunctionCall(name=tool_name, args=arguments)

            execution_result = await mcp_bridge.execute_function_call(
                function_call, task.user_id
            )

            return {
                "tool_result": execution_result.result,
                "success": execution_result.success,
                "error": execution_result.error,
                "execution_method": "mcp_bridge",
            }

        else:
            raise ValueError(f"No suitable tool executor found for: {tool_name}")

    async def _execute_analysis_task(self, task: AutonomicTask) -> Dict[str, Any]:
        """Execute data analysis tasks using autonomic model"""

        analysis_prompt = f"""
        Analyze the following data/information and provide insights:

        Task: {task.description}
        Data: {json.dumps(task.payload, indent=2)}

        Provide a comprehensive analysis including:
        1. Key patterns and trends
        2. Notable insights
        3. Recommendations
        4. Summary of findings

        Format your response as JSON with clear sections.
        """

        result = await self._call_autonomic_model(analysis_prompt)
        return {"analysis_result": result, "task_type": "data_analysis"}

    async def _execute_code_generation_task(
        self, task: AutonomicTask
    ) -> Dict[str, Any]:
        """Execute code generation tasks using autonomic model"""

        code_prompt = f"""
        Generate code based on the following requirements:

        Task: {task.description}
        Requirements: {json.dumps(task.payload, indent=2)}

        Provide:
        1. Complete, working code
        2. Documentation and comments
        3. Usage examples
        4. Error handling

        Use best practices and include proper structure.
        """

        result = await self._call_autonomic_model(code_prompt)
        return {"code_result": result, "task_type": "code_generation"}

    async def _execute_memory_search_task(
        self, task: AutonomicTask, internal_tools: Optional[AuraInternalTools]
    ) -> Dict[str, Any]:
        """Execute memory search tasks using internal tools"""

        if not internal_tools:
            raise ValueError("Internal tools not available for memory search")

        search_query = task.payload.get("query", task.description)
        user_id = task.user_id
        max_results = task.payload.get("max_results", 10)

        # Use comprehensive memory search
        result = await internal_tools.execute_tool(
            "aura.search_all_memories",
            {"query": search_query, "user_id": user_id, "max_results": max_results},
        )

        return {"memory_search_result": result, "task_type": "memory_search"}

    async def _execute_general_task(self, task: AutonomicTask) -> Dict[str, Any]:
        """Execute general processing tasks using autonomic model"""

        general_prompt = f"""
        Process the following task:

        Description: {task.description}
        Details: {json.dumps(task.payload, indent=2)}
        Priority: {task.priority.value}

        Provide a thorough response that addresses the task requirements.
        Include reasoning, methodology, and actionable results.
        """

        result = await self._call_autonomic_model(general_prompt)
        return {"general_result": result, "task_type": "general_processing"}

    async def _call_autonomic_model(self, prompt: str) -> str:
        """Call the autonomic model with rate limiting and timeout handling"""

        # Import client from main module
        import os

        from google import genai

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Google API key not available")

        client = genai.Client(api_key=api_key)

        # Rate limiting: Wait for availability with timeout
        rate_limit_acquired = await self.rate_limiter.wait_for_availability(
            max_wait_seconds=60.0
        )

        if not rate_limit_acquired:
            self.execution_stats["tasks_rate_limited"] += 1
            raise RuntimeError(
                "Rate limit exceeded - unable to acquire request slot within timeout"
            )

        # Create timeout wrapper
        async def model_call():
            # Get maximum remote calls for autonomic model from environment
            autonomic_max_remote_calls = int(
                os.getenv("AFC_AUTONOMIC_MAX_REMOTE_CALLS", "30")
            )
            logger.debug(
                "🤖 Autonomic model configured with %s maximum function calls",
                autonomic_max_remote_calls,
            )

            result = client.models.generate_content(
                model=self.autonomic_model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Lower temperature for more focused processing
                    max_output_tokens=self.max_output_tokens,
                    # Configure automatic function calling for autonomic model (future-proofing)
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        maximum_remote_calls=autonomic_max_remote_calls
                    ),
                ),
            )
            return result.text if result.text else ""

        # Execute with timeout
        try:
            result = await asyncio.wait_for(model_call(), timeout=self.timeout_seconds)
            return result
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(
                f"Model call exceeded {self.timeout_seconds}s timeout"
            ) from None

    def _update_execution_stats(self, execution_time: float, success: bool):
        """Update execution statistics"""
        self.execution_stats["tasks_processed"] += 1

        if success:
            self.execution_stats["tasks_successful"] += 1
        else:
            self.execution_stats["tasks_failed"] += 1

        # Update timing stats
        total_time = self.execution_stats["total_execution_time"] + execution_time
        self.execution_stats["total_execution_time"] = total_time
        self.execution_stats["average_execution_time"] = (
            total_time / self.execution_stats["tasks_processed"]
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics including rate limiting metrics"""
        stats = self.execution_stats.copy()
        stats["rate_limiter"] = self.rate_limiter.get_status()
        return stats


class AutonomicNervousSystem:
    """
    Complete autonomic nervous system for Aura

    Manages task offloading, queuing, and execution to optimize
    main conversation flow and resource utilization.
    """

    def __init__(
        self,
        autonomic_model: str = "gemini-2.0-flash-lite",
        max_concurrent_tasks: int = 29,
        task_threshold: str = "medium",
        max_output_tokens: int = 100000,
        timeout_seconds: int = 60,
        rpm_limit: int = 30,
        rpd_limit: int = 1400,
        queue_max_size: int = 100,
    ):
        self.classifier = TaskClassifier(threshold=task_threshold)
        self.processor = AutonomicProcessor(
            autonomic_model=autonomic_model,
            max_output_tokens=max_output_tokens,
            timeout_seconds=timeout_seconds,
            rpm_limit=rpm_limit,
            rpd_limit=rpd_limit,
        )

        self.max_concurrent_tasks = max_concurrent_tasks
        self.queue_max_size = queue_max_size
        self.task_queue: asyncio.Queue = asyncio.Queue(maxsize=queue_max_size)
        self.active_tasks: Dict[str, AutonomicTask] = {}
        self.completed_tasks: Dict[str, AutonomicTask] = {}
        self.task_semaphore = asyncio.Semaphore(max_concurrent_tasks)

        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

        # External system references
        self.mcp_bridge: Optional[MCPGeminiBridge] = None
        self.internal_tools: Optional[AuraInternalTools] = None

        logger.info("🧠 Autonomic Nervous System initialized")
        logger.info("   Model: %s", autonomic_model)
        logger.info("   Max concurrent tasks: %s", max_concurrent_tasks)
        logger.info("   Task threshold: %s", task_threshold)
        logger.info("   Rate limits: %s RPM, %s RPD", rpm_limit, rpd_limit)
        logger.info("   Queue capacity: %s", queue_max_size)

    def set_external_systems(
        self,
        mcp_bridge: Optional[MCPGeminiBridge] = None,
        internal_tools: Optional[AuraInternalTools] = None,
    ):
        """Set references to external systems"""
        self.mcp_bridge = mcp_bridge
        self.internal_tools = internal_tools
        logger.info("🔗 Autonomic system connected to external systems")

    async def start(self):
        """Start the autonomic system worker"""
        if self._running:
            logger.warning("Autonomic system is already running")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._task_worker())
        logger.info("🚀 Autonomic nervous system started")

    async def stop(self):
        """Stop the autonomic system gracefully"""
        if not self._running:
            return

        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        # Wait for active tasks to complete (with timeout)
        if self.active_tasks:
            logger.info(
                "⏳ Waiting for %s active tasks to complete...", len(self.active_tasks)
            )
            await asyncio.sleep(2)  # Brief grace period

        logger.info("🛑 Autonomic nervous system stopped")

    async def submit_task(
        self,
        description: str,
        payload: Dict[str, Any],
        user_id: str,
        session_id: Optional[str] = None,
        force_offload: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        Submit a task for potential autonomic processing

        Returns:
            Tuple of (was_offloaded, task_id)
        """

        # Analyze whether task should be offloaded
        if not force_offload:
            should_offload, task_type, priority = (
                await self.classifier.should_offload_task(
                    description, payload, {"user_id": user_id}
                )
            )
        else:
            should_offload = True
            task_type = TaskType.BACKGROUND_PROCESSING
            priority = TaskPriority.MEDIUM

        if not should_offload:
            return False, None

        # Create autonomic task
        task_id = f"task_{int(time.time() * 1000)}_{user_id[:8]}"
        task = AutonomicTask(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            description=description,
            payload=payload,
            user_id=user_id,
            session_id=session_id,
        )

        # Queue task with size limit handling
        try:
            self.task_queue.put_nowait(task)
            logger.info(
                f"📋 Queued autonomic task: {task_id} ({task_type.value}, {priority.value})"
            )
            return True, task_id
        except asyncio.QueueFull:
            logger.warning(
                f"⚠️ Task queue full ({self.queue_max_size}), rejecting task: {task_id}"
            )
            return False, None

    async def get_task_result(
        self, task_id: str, timeout: Optional[float] = None
    ) -> Optional[AutonomicTask]:
        """Get the result of a completed task"""

        # Check if already completed
        if task_id in self.completed_tasks:
            return self.completed_tasks[task_id]

        # Wait for completion if specified
        if timeout:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if task_id in self.completed_tasks:
                    return self.completed_tasks[task_id]
                await asyncio.sleep(0.1)

        # Check active tasks
        return self.active_tasks.get(task_id)

    async def _task_worker(self):
        """Background worker to process queued tasks"""
        logger.info("🔄 Autonomic task worker started")

        while self._running:
            try:
                # Get task from queue with timeout
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)

                # Process task with semaphore
                async with self.task_semaphore:
                    asyncio.create_task(self._process_task(task))

            except asyncio.TimeoutError:
                # No tasks in queue, continue
                continue
            except Exception as e:
                logger.error("❌ Task worker error: %s", e)
                await asyncio.sleep(1.0)

    async def _process_task(self, task: AutonomicTask):
        """Process an individual task"""
        try:
            # Add to active tasks
            self.active_tasks[task.task_id] = task

            # Execute task
            completed_task = await self.processor.execute_task(
                task, self.mcp_bridge, self.internal_tools
            )

            # Move to completed tasks
            self.completed_tasks[task.task_id] = completed_task

            # Clean up active tasks
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]

            # Limit completed task history
            if len(self.completed_tasks) > 1000:
                # Remove oldest tasks
                oldest_tasks = sorted(
                    self.completed_tasks.keys(),
                    key=lambda k: self.completed_tasks[k].completed_at or datetime.min,
                )[:100]
                for old_task_id in oldest_tasks:
                    del self.completed_tasks[old_task_id]

        except Exception as e:
            logger.error("❌ Error processing task %s: %s", task.task_id, e)
            # Ensure task is moved to completed even on error
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status including rate limiting metrics"""
        processor_stats = self.processor.get_stats()

        return {
            "running": self._running,
            "queued_tasks": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "queue_max_size": self.queue_max_size,
            "queue_utilization": (self.task_queue.qsize() / self.queue_max_size) * 100,
            "processor_stats": processor_stats,
            "rate_limiting": processor_stats.get("rate_limiter", {}),
            "task_threshold": self.classifier.threshold,
            "autonomic_model": self.processor.autonomic_model,
        }


# Global autonomic system instance
_autonomic_system: Optional[AutonomicNervousSystem] = None


async def initialize_autonomic_system(
    mcp_bridge: Optional[MCPGeminiBridge] = None,
    internal_tools: Optional[AuraInternalTools] = None,
) -> AutonomicNervousSystem:
    """Initialize the global autonomic nervous system with proper rate limiting"""
    global _autonomic_system

    import os

    # Get configuration from environment with optimized defaults
    autonomic_model = os.getenv("AURA_AUTONOMIC_MODEL", "gemini-2.0-flash-lite")
    max_concurrent = int(os.getenv("AUTONOMIC_MAX_CONCURRENT_TASKS", "30"))
    task_threshold = os.getenv("AUTONOMIC_TASK_THRESHOLD", "medium")
    max_tokens = int(os.getenv("AURA_AUTONOMIC_MAX_OUTPUT_TOKENS", "100000"))
    timeout = int(os.getenv("AUTONOMIC_TIMEOUT_SECONDS", "60"))

    # Rate limiting configuration
    rpm_limit = int(os.getenv("AUTONOMIC_RATE_LIMIT_RPM", "30"))
    rpd_limit = int(os.getenv("AUTONOMIC_RATE_LIMIT_RPD", "1400"))
    queue_max_size = int(os.getenv("AUTONOMIC_QUEUE_MAX_SIZE", "40"))

    _autonomic_system = AutonomicNervousSystem(
        autonomic_model=autonomic_model,
        max_concurrent_tasks=max_concurrent,
        task_threshold=task_threshold,
        max_output_tokens=max_tokens,
        timeout_seconds=timeout,
        rpm_limit=rpm_limit,
        rpd_limit=rpd_limit,
        queue_max_size=queue_max_size,
    )

    # Set external system references
    _autonomic_system.set_external_systems(mcp_bridge, internal_tools)

    # Start the system
    await _autonomic_system.start()

    logger.info("🧠 Global autonomic nervous system initialized and started")
    logger.info(
        f"📊 Configuration: {max_concurrent} concurrent, {rpm_limit} RPM, {rpd_limit} RPD"
    )
    return _autonomic_system


def get_autonomic_system() -> Optional[AutonomicNervousSystem]:
    """Get the global autonomic system instance"""
    return _autonomic_system


async def shutdown_autonomic_system():
    """Shutdown the global autonomic system"""
    global _autonomic_system

    if _autonomic_system:
        await _autonomic_system.stop()
        _autonomic_system = None
        logger.info("🛑 Global autonomic nervous system shutdown complete")
