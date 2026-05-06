"""
Thinking Processor for Aura - Advanced AI Companion
==================================================

Implements proper thinking extraction using Google Gemini's thinking capabilities.
This module handles the streaming response processing to separate AI thoughts
from the final answer, enabling transparent reasoning visibility.
"""

import logging
from typing import List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from google import genai
from google.genai import types
import os

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ThinkingResult:
    """Container for thinking extraction results"""
    thoughts: str
    answer: str
    thinking_summary: str
    total_chunks: int
    thinking_chunks: int
    answer_chunks: int
    processing_time_ms: float
    has_thinking: bool
    error: Optional[str] = None

class ThinkingProcessor:
    """
    Advanced thinking processor for Gemini's reasoning capabilities.

    This processor handles streaming responses from Gemini models to extract
    and separate the AI's internal reasoning (thoughts) from the final answer,
    providing transparency into the AI's decision-making process.
    """

    def __init__(self, client: genai.Client):
        """
        Initialize the thinking processor.

        Args:
            client: Initialized Google Gemini client
        """
        self.client = client
        budget = int(os.getenv('THINKING_BUDGET', '-1'))  # Default to adaptive thinking
        # Use adaptive thinking (-1) as intended by Google, don't impose artificial limits
        self.thinking_budget = budget

    async def process_message_with_thinking(
        self,
        chat: Any,
        message: str,
        user_id: str,
        include_thinking_in_response: bool = False,
        thinking_summary_length: int = 200
    ) -> ThinkingResult:
        """
        Process a message with thinking extraction using non-streaming approach.

        UPDATED: Now uses chat.send_message() for non-streaming operation that
        works better with Aura's architecture while still extracting thinking.

        Args:
            chat: Google Gemini chat session with thinking enabled
            message: User's input message
            user_id: User identifier for logging
            include_thinking_in_response: Whether to include thoughts in final answer
            thinking_summary_length: Maximum length for thinking summary

        Returns:
            ThinkingResult containing separated thoughts and answer
        """
        start_time = datetime.now()
        thoughts = ""
        answer = ""
        total_chunks = 1  # Non-streaming, so just one "chunk"
        thinking_chunks = 0
        answer_chunks = 1
        has_thinking = False

        try:
            logger.info("🧠 Starting non-streaming thinking processing for user %s", user_id)

            # Use the chat session directly (it should have thinking enabled)
            result = chat.send_message(message)

            # Debug logging for raw response (only in debug mode)
            debug_mode = os.getenv('THINKING_DEBUG', 'false').lower() == 'true'
            if debug_mode:
                logger.debug("🔍 Raw response structure for %s: %s", user_id, type(result))
                logger.debug("🔍 Response candidates: %s", len(result.candidates) if result.candidates else 0)

            # Check for valid response
            if not result or not result.candidates:
                raise ValueError("Empty response from Gemini")

            candidate = result.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise ValueError("Malformed response structure from Gemini")

            # Debug candidate structure
            if debug_mode:
                logger.debug("🔍 Candidate parts count: %s", len(candidate.content.parts))

            # Extract the answer text and check for thinking attributes
            for i, part in enumerate(candidate.content.parts):
                if debug_mode:
                    has_text = hasattr(part, 'text')
                    has_thought = hasattr(part, 'thought')
                    logger.debug("🔍 Part %s: type=%s, has_text=%s, has_thought=%s", i, type(part), has_text, has_thought)

                # Skip parts without text
                if not hasattr(part, 'text') or not part.text:
                    continue

                text_content = str(part.text) if part.text else ""
                if not text_content:
                    continue

                # Check if this part is thinking content (based on Google's documentation)
                if hasattr(part, 'thought') and part.thought is True:
                    # This is thinking content - add to thoughts
                    thoughts += text_content
                    has_thinking = True
                    thinking_chunks += 1
                    logger.info("🎯 Found thinking content in response part %s: %s chars", i, len(text_content))
                    if debug_mode:
                        logger.debug("🔍 Thinking content preview: %s...", text_content[:100])
                else:
                    # This is regular answer content (including when part.thought is None or False)
                    answer += text_content
                    if debug_mode:
                        logger.debug("🔍 Added answer part: %s chars", len(text_content))

            if debug_mode:
                logger.debug("🔍 Total answer length: %s chars", len(answer))
                logger.debug("🔍 Total thoughts length: %s chars", len(thoughts))
                logger.debug("🔍 Has thinking: %s", has_thinking)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            # Log results
            logger.info("✅ Non-streaming thinking processing complete for user %s", user_id)
            logger.info("   � Total chunks: %s", total_chunks)
            logger.info("   🧠 Thinking chunks: %s", thinking_chunks)
            logger.info("   💬 Answer chunks: %s", answer_chunks)
            logger.info("   ⏱️ Processing time: %sms", processing_time)
            logger.info("   🎯 Has thinking: %s", has_thinking)
            if has_thinking:
              logger.info("   🧠 Thinking content length: %s chars", len(thoughts))
              logger.info("   💬 Answer content length: %s chars", len(answer))
            logger.info("   🧠 Thinking chunks: %s", thinking_chunks)
            logger.info("   💬 Answer chunks: %s", answer_chunks)
            logger.info("   ⏱️ Processing time: %sms", processing_time)
            logger.info("   🎯 Has thinking: %s", has_thinking)

            # Optionally include thinking in response
            final_answer = answer
            if include_thinking_in_response and has_thinking and thoughts.strip():
                final_answer = f"**My Reasoning:**\n{thoughts}\n\n**My Response:**\n{answer}"

            return ThinkingResult(
                thoughts=thoughts,
                answer=final_answer,
                thinking_summary=thoughts,  # Just use thoughts directly
                total_chunks=total_chunks,
                thinking_chunks=thinking_chunks,
                answer_chunks=answer_chunks,
                processing_time_ms=processing_time,
                has_thinking=has_thinking
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error("❌ Non-streaming thinking processing failed for user %s: %s", user_id, e)

            return ThinkingResult(
                thoughts="",
                answer="I apologize, but I encountered an issue processing your request. Please try again.",
                thinking_summary="",
                total_chunks=total_chunks,
                thinking_chunks=thinking_chunks,
                answer_chunks=answer_chunks,
                processing_time_ms=processing_time,
                has_thinking=False,
                error=str(e)
            )

    def _create_thinking_summary(self, thoughts: str, max_length: int = 200) -> str:
        """
        Create a concise summary of the AI's thinking process.

        Args:
            thoughts: Raw thinking text
            max_length: Maximum length for summary

        Returns:
            Summarized thinking process
        """
        # Ensure thoughts is actually a string
        if not isinstance(thoughts, str):
            thoughts = str(thoughts) if thoughts else ""

        if not thoughts.strip():
            return "No internal reasoning captured."

        # Simple summarization - take key sentences
        sentences = thoughts.replace('\n', ' ').split('. ')

        if len(thoughts) <= max_length:
            return thoughts.strip()

        # Extract key phrases and reasoning steps
        key_phrases = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            # Look for reasoning indicators
            reasoning_indicators = [
                'because', 'therefore', 'since', 'given that',
                'considering', 'based on', 'due to', 'as a result'
            ]

            if any(indicator in sentence.lower() for indicator in reasoning_indicators):
                key_phrases.append(sentence)
            elif len(key_phrases) < 2:  # Ensure we have some content
                key_phrases.append(sentence)

        summary = '. '.join(key_phrases[:3])  # Max 3 key sentences

        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."

        return summary.strip() if summary.strip() else "Complex reasoning process completed."

    async def process_with_function_calls_and_thinking(
        self,
        chat: Any,
        message: str,
        user_id: str,
        mcp_bridge: Any = None,
        include_thinking_in_response: bool = False
    ) -> ThinkingResult:
        """
        Process message with both function calls and thinking extraction.

        SIMPLIFIED: Since Aura doesn't use streaming and function calls are handled
        by the autonomic system, this now just delegates to the standard thinking processor.

        Args:
            chat: Google Gemini chat session
            message: User's input message
            user_id: User identifier for logging
            mcp_bridge: MCP bridge for function calls (unused - kept for compatibility)
            include_thinking_in_response: Whether to include thoughts in response

        Returns:
            ThinkingResult with thinking extraction
        """
        logger.info("🔧 Processing message with thinking for user %s", user_id)

        # Simply delegate to the standard thinking processor
        # Function calls are handled by aura_autonomic_system.py
        return await self.process_message_with_thinking(
            chat=chat,
            message=message,
            user_id=user_id,
            include_thinking_in_response=include_thinking_in_response
        )

def create_thinking_enabled_chat(
    client: genai.Client,
    model: str,
    system_instruction: str,
    tools: Optional[List[Any]] = None,
    thinking_budget: Optional[int] = None
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
        budget = int(os.getenv('THINKING_BUDGET', '-1'))  # Default to adaptive thinking
        # Use adaptive thinking (-1) as intended by Google, don't impose artificial limits
        thinking_budget = budget

    chat = client.chats.create(
        model=model,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=int(os.getenv('AURA_MAX_OUTPUT_TOKENS', '1000000')),
            tools=tools if tools else None,
            system_instruction=system_instruction,
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=thinking_budget
            )
        )
    )

    logger.info("🧠 Created thinking-enabled chat session (budget: %s)", thinking_budget)
    return chat
