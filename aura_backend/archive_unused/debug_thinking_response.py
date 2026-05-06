#!/usr/bin/env python3
"""
Debug script to examine the exact structure of Gemini thinking responses
"""

import asyncio
import logging
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def debug_gemini_thinking_response():
    """Debug the exact structure of Gemini thinking responses"""

    load_dotenv()

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("❌ GEMINI_API_KEY not found in environment")
        return

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)
    logger.info("✅ Gemini client initialized")

    # Create a chat session with thinking enabled
    chat = client.chats.create(
        model='gemini-2.5-flash',
        config=types.GenerateContentConfig(
            temperature=0.7,
            thinking_config=types.ThinkingConfig(
                thinking_budget=4096,
                include_thoughts=True
            )
        )
    )
    logger.info("✅ Chat session created with thinking enabled")

    # Test message
    test_message = "How is your memory doing?"

    logger.info("🤔 Testing with message: %s", test_message)

    try:
        # Send message and get response
        result = chat.send_message(test_message)

        # Debug the response structure
        logger.info("🔍 RAW RESPONSE ANALYSIS:")
        logger.info("   Response type: %s", type(result))
        logger.info("   Has candidates: %s", hasattr(result, 'candidates'))

        if result.candidates:
            logger.info("   Candidates count: %s", len(result.candidates))

            candidate = result.candidates[0]
            logger.info("   Candidate type: %s", type(candidate))
            logger.info("   Has content: %s", hasattr(candidate, 'content'))

            if candidate.content:
                logger.info("   Content type: %s", type(candidate.content))
                logger.info("   Has parts: %s", hasattr(candidate.content, 'parts'))

                if candidate.content.parts:
                    logger.info("   Parts count: %s", len(candidate.content.parts))

                    for i, part in enumerate(candidate.content.parts):
                        logger.info("\n   🔍 PART %s ANALYSIS:", i)
                        logger.info("      Part type: %s", type(part))
                        logger.info("      Has text: %s", hasattr(part, 'text'))
                        logger.info("      Has thought: %s", hasattr(part, 'thought'))

                        if hasattr(part, 'text'):
                            text_value = part.text
                            logger.info("      Text type: %s", type(text_value))
                            logger.info("      Text length: %s", len(str(text_value)) if text_value else 0)
                            if text_value:
                                text_str = str(text_value)
                                logger.info("      Text preview: %s", repr(text_str[:100]))

                        if hasattr(part, 'thought'):
                            thought_value = part.thought
                            logger.info("      Thought type: %s", type(thought_value))
                            logger.info("      Thought value: %s", thought_value)

                        # Check all attributes of the part
                        logger.info("      All attributes: %s", [attr for attr in dir(part) if not attr.startswith('_')])

        # Also check usage metadata
        if hasattr(result, 'usage_metadata'):
            logger.info("\n🔍 USAGE METADATA:")
            logger.info("   Usage metadata: %s", result.usage_metadata)
            if hasattr(result.usage_metadata, 'thoughts_token_count'):
                logger.info("   Thoughts token count: %s", result.usage_metadata.thoughts_token_count)

    except Exception as e:
        logger.error("❌ Debug failed: %s", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_gemini_thinking_response())
