"""
Thinking Processor for Aura - Advanced AI Companion (FIXED VERSION)
===================================================================

Implements proper thinking extraction using Google Gemini's thinking capabilities
WITH proper function call handling. This restores the functionality that was
removed while maintaining thinking transparency.

This version properly handles:
- Thinking extraction from Gemini responses
- Function call execution through MCP bridge
- Integration between thinking and tool usage
- Non-streaming mode that works with Aura's architecture
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from google import genai
from google.genai import types

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ThinkingResult:
    """Container for thinking extraction results"""

    thoughts: str
    answer: str
    total_chunks: int
    thinking_chunks: int
    answer_chunks: int
    processing_time_ms: float
    has_thinking: bool
    error: Optional[str] = None


class ThinkingProcessor:
    """
    Advanced thinking processor for Gemini's reasoning capabilities.

    This processor handles responses from Gemini models to extract
    and separate the AI's internal reasoning (thoughts) from the final answer,
    while also properly executing function calls.
    """

    def __init__(self, client: genai.Client):
        """
        Initialize the thinking processor.

        Args:
            client: Initialized Google Gemini client
        """
        self.client = client
        budget = int(os.getenv("THINKING_BUDGET", "-1"))  # Default to adaptive thinking
        self.thinking_budget = budget

    async def process_message_with_thinking(
        self,
        chat: Any,
        message: str,
        user_id: str,
        include_thinking_in_response: bool = False,
    ) -> ThinkingResult:
        """
        Process a message with thinking extraction - SIMPLE AND CORRECT VERSION.

        Args:
            chat: Google Gemini chat session with thinking enabled
            message: User's input message
            user_id: User identifier for logging
            include_thinking_in_response: Whether to include thoughts in final answer

        Returns:
            ThinkingResult containing separated thoughts and answer
        """
        start_time = datetime.now()
        thoughts = ""
        answer = ""
        total_chunks = 1
        thinking_chunks = 0
        answer_chunks = 0
        has_thinking = False

        try:
            logger.info("🧠 Starting thinking processing for user %s", user_id)

            # Use the chat session directly (it should have thinking enabled)
            result = chat.send_message(message)

            # Enable debug mode for thinking processing

            debug_mode = os.getenv("THINKING_DEBUG", "true").lower() == "true"

            # Debug logging
            if debug_mode:
                logger.debug("🔍 Raw response structure for %s: %s", user_id, type(result))
                logger.debug(
                    f"🔍 Response candidates: {len(result.candidates) if result.candidates else 0}"
                )

            # Check for valid response
            if not result or not result.candidates:
                raise ValueError("Empty response from Gemini")

            candidate = result.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise ValueError("Malformed response structure from Gemini")

            # Simple, correct processing - trust Gemini's thinking detection
            for i, part in enumerate(candidate.content.parts):
                if debug_mode:
                    has_text = hasattr(part, "text")
                    has_thought = hasattr(part, "thought")
                    thought_value = (
                        getattr(part, "thought", None) if has_thought else None
                    )
                    logger.debug(
                        f"🔍 Part {i}: type={type(part)}, has_text={has_text}, has_thought={has_thought}, thought_value={thought_value}"
                    )

                # Skip parts without text
                if not hasattr(part, "text") or not part.text:
                    continue

                text_content = str(part.text) if part.text else ""
                if not text_content:
                    continue

                # SIMPLE: Trust Gemini's thinking detection completely
                if hasattr(part, "thought") and part.thought is True:
                    # This is thinking content as marked by Gemini
                    thoughts += text_content
                    has_thinking = True
                    thinking_chunks += 1
                    logger.info(
                        f"🎯 Gemini thinking - Part {i}: {len(text_content)} chars"
                    )
                    if debug_mode:
                        logger.debug("🧠 Thinking: %s...", text_content[:200])
                else:
                    # This is regular answer content
                    answer += text_content
                    answer_chunks += 1
                    logger.info(
                        f"💬 Gemini answer - Part {i}: {len(text_content)} chars"
                    )
                    if debug_mode:
                        logger.debug("💬 Answer: %s...", text_content[:200])

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Log results
            logger.info("✅ Thinking processing complete for user %s", user_id)
            logger.info("   🧠 Thinking chunks: %s", thinking_chunks)
            logger.info("   💬 Answer chunks: %s", answer_chunks)
            logger.info("   🎯 Has thinking: %s", has_thinking)
            if has_thinking:
                logger.info("   🧠 Thinking length: %s chars", len(thoughts))
            logger.info("   💬 Answer length: %s chars", len(answer))

            # Don't include thinking in response unless explicitly requested
            final_answer = answer
            if include_thinking_in_response and has_thinking and thoughts.strip():
                final_answer = (
                    f"**My Reasoning:**\n{thoughts}\n\n**My Response:**\n{answer}"
                )

            return ThinkingResult(
                thoughts=thoughts,
                answer=final_answer,
                total_chunks=total_chunks,
                thinking_chunks=thinking_chunks,
                answer_chunks=answer_chunks,
                processing_time_ms=processing_time,
                has_thinking=has_thinking,
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error("❌ Thinking processing failed for user %s: %s", user_id, e)

            return ThinkingResult(
                thoughts="",
                answer="I apologize, but I encountered an issue processing your request. Please try again.",
                total_chunks=0,
                thinking_chunks=0,
                answer_chunks=1,
                processing_time_ms=processing_time,
                has_thinking=False,
                error=str(e),
            )

    async def process_with_function_calls_and_thinking(
        self,
        chat: Any,
        message: str,
        user_id: str,
        mcp_bridge: Any = None,
        include_thinking_in_response: bool = False,
    ) -> ThinkingResult:
        """
        Process message with both function calls and enhanced thinking extraction.

        This version preserves the complete reasoning process including tool calls and results
        in the thinking block, as requested by the user.

        Args:
            chat: Google Gemini chat session
            message: User's input message
            user_id: User identifier for logging
            mcp_bridge: MCP bridge for function calls
            include_thinking_in_response: Whether to include thoughts in response

        Returns:
            ThinkingResult with complete thinking process including tool usage
        """
        start_time = datetime.now()

        try:
            logger.info(
                f"🔧 Starting enhanced thinking+function call processing for user {user_id}"
            )

            # Complete thinking content including tool calls and results
            complete_thinking_process = ""
            final_answer = ""
            total_chunks = 0
            thinking_chunks = 0
            answer_chunks = 0
            has_thinking = False
            function_calls_processed = 0

            # Enable debug mode for thinking processing

            # Send message to get initial response
            result = chat.send_message(message)

            # Check for empty or malformed response
            if not result or not result.candidates:
                raise ValueError(
                    "Empty response from Gemini (possible tool call cutoff)"
                )

            candidate = result.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise ValueError("Malformed response structure from Gemini")

            # Track function calls for complete thinking process
            pending_function_calls = []

            # Process initial response parts
            for i, part in enumerate(candidate.content.parts):
                total_chunks += 1

                if part.text:
                    part_text = part.text

                    # Check if this is thinking content (trust Gemini's marking)
                    if hasattr(part, "thought") and part.thought is True:
                        complete_thinking_process += part_text + "\n\n"
                        thinking_chunks += 1
                        has_thinking = True
                        logger.info(
                            f"🎯 Initial thinking detected by Gemini attribute - Part {i}"
                        )
                        logger.info(
                            f"🧠 Added initial text to thinking (gemini_attribute) - Part {i}: {len(part_text)} chars"
                        )
                    else:
                        # This is the final answer content
                        final_answer += part_text
                        answer_chunks += 1
                        logger.info(
                            f"💬 Added initial text to answer - Part {i}: {len(part_text)} chars"
                        )

                elif (
                    hasattr(part, "function_call") and part.function_call and mcp_bridge
                ):
                    # Function call detected - add to thinking process
                    pending_function_calls.append(part.function_call)
                    function_calls_processed += 1

                    # Add function call to thinking process
                    complete_thinking_process += (
                        f"🔧 **Function Call:** {part.function_call.name}\n"
                    )
                    if hasattr(part.function_call, "args") and part.function_call.args:
                        try:
                            args_str = json.dumps(part.function_call.args, indent=2)
                            complete_thinking_process += (
                                f"📋 **Arguments:**\n```json\n{args_str}\n```\n\n"
                            )
                        except Exception:
                            complete_thinking_process += (
                                f"📋 **Arguments:** {part.function_call.args}\n\n"
                            )
                    else:
                        complete_thinking_process += "\n"

                    logger.info("🔧 Function call detected: %s", part.function_call.name)
                    has_thinking = True

            # Process function calls and add results to thinking
            if pending_function_calls:
                logger.info(
                    f"🔧 Processing {len(pending_function_calls)} function calls"
                )

                # Execute all function calls and collect results
                function_responses = []

                for func_call in pending_function_calls:
                    try:
                        # Execute function call through MCP bridge
                        execution_result = await mcp_bridge.execute_function_call(
                            func_call, user_id
                        )

                        if execution_result.success:
                            logger.info(
                                f"✅ Function call {func_call.name} executed successfully"
                            )

                            # Add function result to thinking process
                            complete_thinking_process += (
                                f"✅ **Function Result for {func_call.name}:**\n"
                            )
                            complete_thinking_process += (
                                f"```\n{execution_result.result}\n```\n\n"
                            )

                            # Collect function response for batch processing
                            function_response = types.Part(
                                function_response=types.FunctionResponse(
                                    name=func_call.name,
                                    response={"result": execution_result.result},
                                )
                            )
                            function_responses.append(function_response)

                        else:
                            # Function call failed - add to thinking process
                            error_info = f"❌ **Function Call Failed:** {func_call.name}\n**Error:** {execution_result.error}\n\n"
                            complete_thinking_process += error_info
                            logger.error(
                                f"❌ Function call {func_call.name} failed: {execution_result.error}"
                            )
                            has_thinking = True

                    except Exception as func_error:
                        # Function call error - add to thinking process
                        error_info = f"💥 **Function Call Error:** {func_call.name}\n**Exception:** {str(func_error)}\n\n"
                        complete_thinking_process += error_info
                        logger.error(
                            f"❌ Function call {func_call.name} error: {func_error}"
                        )
                        has_thinking = True

                # Send all function responses to get follow-up response (simplified approach)
                if function_responses:
                    logger.info(
                        f"📤 Sending {len(function_responses)} function results to model for final response"
                    )

                    try:
                        # Get follow-up response for function results
                        follow_up_result = chat.send_message(function_responses)

                        if (
                            follow_up_result.candidates
                            and follow_up_result.candidates[0].content
                            and follow_up_result.candidates[0].content.parts
                        ):

                            # Process follow-up response parts
                            for j, result_part in enumerate(
                                follow_up_result.candidates[0].content.parts
                            ):
                                if result_part.text:
                                    total_chunks += 1
                                    follow_text = result_part.text

                                    # Use verified patterns for follow-up classification
                                    is_marked_as_thought = (
                                        hasattr(result_part, "thought")
                                        and result_part.thought is True
                                    )
                                    looks_like_thinking = (
                                        self._looks_like_thinking_content(follow_text)
                                    )

                                    # Decision logic: Only treat as thinking if both marked AND looks like thinking
                                    if is_marked_as_thought and looks_like_thinking:
                                        # This is legitimate follow-up thinking
                                        complete_thinking_process += f"🧠 **Follow-up Thinking:**\n{follow_text}\n\n"
                                        thinking_chunks += 1
                                        has_thinking = True
                                        logger.info(
                                            f"🎯 Follow-up thinking detected (verified with patterns) - Part {j}"
                                        )
                                        logger.info(
                                            f"🧠 Added cleaned follow-up to thinking (gemini_attribute_with_reasoning_patterns) - Part {j}: {len(follow_text)} chars"
                                        )
                                    else:
                                        # This is the final answer after processing tool results
                                        cleaned_follow_text = (
                                            self._clean_follow_up_content(follow_text)
                                        )
                                        if cleaned_follow_text.strip():
                                            final_answer += cleaned_follow_text
                                            answer_chunks += 1
                                            logger.info(
                                                f"📝 Follow-up treated as answer - Part {j}"
                                            )
                                            logger.info(
                                                f"💬 Added cleaned follow-up to answer - Part {j}: {len(cleaned_follow_text)} chars"
                                            )

                                elif (
                                    hasattr(result_part, "function_call")
                                    and result_part.function_call
                                    and mcp_bridge
                                ):
                                    # EXECUTE additional function calls as intended - no "efficiency" sabotage!
                                    logger.info(
                                        f"🔧 Executing additional function call in response: {result_part.function_call.name}"
                                    )

                                    try:
                                        # ACTUALLY EXECUTE the function call instead of deferring it
                                        execution_result = (
                                            await mcp_bridge.execute_function_call(
                                                result_part.function_call, user_id
                                            )
                                        )

                                        if execution_result.success:
                                            complete_thinking_process += f"🔧 **Additional Function Call:** {result_part.function_call.name}\n"
                                            complete_thinking_process += f"✅ **Result:** {execution_result.result}\n\n"

                                            # Add result to final answer
                                            if execution_result.result:
                                                final_answer += (
                                                    f"\n\n{execution_result.result}"
                                                )
                                        else:
                                            complete_thinking_process += f"🔧 **Additional Function Call:** {result_part.function_call.name}\n"
                                            complete_thinking_process += f"❌ **Error:** {execution_result.error}\n\n"

                                        function_calls_processed += 1
                                        has_thinking = True

                                    except Exception as func_error:
                                        logger.error(
                                            f"❌ Additional function call failed: {func_error}"
                                        )
                                        complete_thinking_process += f"🔧 **Additional Function Call:** {result_part.function_call.name}\n"
                                        complete_thinking_process += (
                                            f"💥 **Exception:** {str(func_error)}\n\n"
                                        )
                                        has_thinking = True

                    except Exception as follow_up_error:
                        logger.error(
                            f"❌ Failed to process follow-up response: {follow_up_error}"
                        )
                        complete_thinking_process += (
                            f"💥 **Follow-up Error:** {str(follow_up_error)}\n\n"
                        )
                        has_thinking = True

            # Ensure we have a response
            if not final_answer.strip():
                if has_thinking and complete_thinking_process.strip():
                    # If we only have thinking content, provide a summary
                    final_answer = "I've completed the analysis and function calls as shown in my reasoning above."
                else:
                    final_answer = "I apologize, but I wasn't able to generate a proper response. Please try again."

            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Only include thinking in response if explicitly requested (usually false for UI display)
            response_with_thinking = final_answer
            if (
                include_thinking_in_response
                and has_thinking
                and complete_thinking_process.strip()
            ):
                response_with_thinking = f"**My Reasoning:**\n{complete_thinking_process}\n\n**My Response:**\n{final_answer}"

            logger.info(
                f"✅ Enhanced thinking+function processing complete for user {user_id}"
            )
            logger.info("   📊 Total chunks: %s", total_chunks)
            logger.info("   🧠 Thinking chunks: %s", thinking_chunks)
            logger.info("   💬 Answer chunks: %s", answer_chunks)
            logger.info("   🔧 Function calls: %s", function_calls_processed)
            logger.info("   ⏱️ Processing time: %sms", processing_time)
            logger.info("   🎯 Has thinking: %s", has_thinking)
            if has_thinking:
                logger.info(
                    f"   🧠 Final thinking length: {len(complete_thinking_process)} chars"
                )
            logger.info("   💬 Final answer length: %s chars", len(final_answer))

            return ThinkingResult(
                thoughts=complete_thinking_process,  # Complete process including tool calls and results
                answer=response_with_thinking,  # Clean final answer (without thinking unless requested)
                total_chunks=total_chunks,
                thinking_chunks=thinking_chunks,
                answer_chunks=answer_chunks,
                processing_time_ms=processing_time,
                has_thinking=has_thinking,
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(
                f"❌ Enhanced thinking+function processing failed for user {user_id}: {e}"
            )

            return ThinkingResult(
                thoughts="",
                answer="I apologize, but I encountered an issue processing your request. Please try again.",
                total_chunks=0,
                thinking_chunks=0,
                answer_chunks=1,
                processing_time_ms=processing_time,
                has_thinking=False,
                error=str(e),
            )

    def _looks_like_thinking_content(self, content: str) -> bool:
        """
        Use heuristics to determine if content looks like internal thinking vs. user-facing response.

        This helps override Gemini's thought=True marking when it's clearly wrong.

        Args:
            content: Text content to analyze

        Returns:
            True if content appears to be internal reasoning, False if it looks like a user response
        """
        if not content or not content.strip():
            return False

        content_lower = content.lower().strip()

        # Strong indicators of thinking content
        thinking_indicators = [
            "let me think",
            "i need to",
            "i should",
            "let me analyze",
            "let me consider",
            "i'll need to",
            "first, i",
            "next, i",
            "then i",
            "so i need to",
            "i can see that",
            "looking at this",
            "from the search results",
            "the search shows",
            "based on the results",
        ]

        # Strong indicators of user-facing response
        response_indicators = [
            "you're absolutely right",
            "thank you for",
            "i apologize",
            "you certainly can",
            "that's fascinating",
            "i've completed",
            "i found",
            "here's what",
            "according to",
            "the configuration shows",
            "i can confirm",
            "excellent news",
            "perfect!",
        ]

        # Check for thinking indicators
        thinking_score = sum(
            1 for indicator in thinking_indicators if indicator in content_lower
        )

        # Check for response indicators
        response_score = sum(
            1 for indicator in response_indicators if indicator in content_lower
        )

        # If content is very short and conversational, likely a response
        if len(content) < 200 and any(
            indicator in content_lower
            for indicator in ["thank you", "you're", "i've", "that's"]
        ):
            return False

        # If we have clear response indicators and no thinking indicators, it's a response
        if response_score > 0 and thinking_score == 0:
            return False

        # If we have more response indicators than thinking indicators, likely a response
        if response_score > thinking_score:
            return False

        # If we have thinking indicators but no response indicators, likely thinking
        if thinking_score > 0 and response_score == 0:
            return True

        # Default: if unclear and marked as thought by Gemini, trust Gemini but with lower confidence
        # This should rarely be reached due to the logic in the calling function
        return True

    def _clean_follow_up_content(self, content: str) -> str:
        """
        Clean follow-up content to remove conversational headers and unwanted elements.

        This prevents "My Response:", "My Reasoning:", etc. from appearing in the
        AI Reasoning dropdown or main response.

        Args:
            content: Raw follow-up content from Gemini

        Returns:
            Cleaned content with headers and unwanted elements removed
        """
        if not content:
            return ""

        # Remove common conversational headers
        headers_to_remove = [
            "**My Response:**",
            "**My Reasoning:**",
            "**My Analysis:**",
            "**My Thoughts:**",
            "My Response:",
            "My Reasoning:",
            "My Analysis:",
            "My Thoughts:",
            "**Response:**",
            "**Reasoning:**",
            "Response:",
            "Reasoning:",
        ]

        cleaned = content
        for header in headers_to_remove:
            # Remove the header and any following whitespace/newlines
            if header in cleaned:
                parts = cleaned.split(header, 1)
                if len(parts) > 1:
                    # Keep everything before the header, and content after (without the header)
                    cleaned = parts[0] + parts[1]

        # Remove excessive whitespace at start/end
        cleaned = cleaned.strip()

        # Remove leading/trailing newlines that might create formatting issues
        while cleaned.startswith("\n"):
            cleaned = cleaned[1:]
        while cleaned.endswith("\n\n\n"):
            cleaned = cleaned[:-1]

        return cleaned


def create_thinking_enabled_chat(
    client: genai.Client,
    model: str,
    system_instruction: str,
    tools: Optional[List[Any]] = None,
    thinking_budget: Optional[int] = None,
) -> Any:
    """
    Create a chat session with thinking capabilities enabled.

    Args:
        client: Google Gemini client
        model: Model name to use
        system_instruction: System prompt
        tools: List of available tools
        thinking_budget: Thinking token budget (default from env)

    Returns:
        Chat session with thinking enabled
    """
    if thinking_budget is None:
        budget = int(os.getenv("THINKING_BUDGET", "-1"))  # Default to adaptive thinking
        thinking_budget = budget

    chat = client.chats.create(
        model=model,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=int(os.getenv("AURA_MAX_OUTPUT_TOKENS", "1000000")),
            tools=tools if tools else None,
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(
                include_thoughts=True, thinking_budget=thinking_budget
            ),
        ),
    )

    logger.info("🧠 Created thinking-enabled chat session (budget: %s)", thinking_budget)
    return chat
