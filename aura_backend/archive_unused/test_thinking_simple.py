#!/usr/bin/env python3
"""
Simple Thinking Test Script
===========================

This script tests the thinking functionality to verify it's working properly.
"""

import os
import asyncio
import logging
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_thinking():
    """Test basic thinking functionality"""

    # Get API key
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment variables")
        return

    # Create client
    client = genai.Client(api_key=api_key)

    # Get thinking budget from environment
    budget = int(os.getenv('THINKING_BUDGET', '-1'))  # Default to adaptive thinking
    thinking_budget = budget  # No conversion - pass through -1 for adaptive thinking

    print(f"🧠 Testing thinking with budget: {thinking_budget} tokens ({'adaptive' if budget == -1 else 'fixed'})")

    # Create thinking-enabled chat
    chat = client.chats.create(
        model=os.getenv('AURA_MODEL', 'gemini-2.5-flash'),
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=int(os.getenv('AURA_MAX_OUTPUT_TOKENS', '1000000')),
            system_instruction="You are a helpful AI assistant. Show your reasoning process.",
            thinking_config=types.ThinkingConfig(
                thinking_budget=thinking_budget,
                include_thoughts=True
            )
        )
    )

    # Test message that should trigger thinking
    test_message = "Explain step by step how to solve: What's 15 * 23 + 47 - 8?"

    print(f"📤 Sending test message: {test_message}")

    try:
        # Send message
        result = chat.send_message(test_message)

        print("📥 Response received!")
        print(f"🔍 Response type: {type(result)}")
        print(f"🔍 Candidates: {len(result.candidates) if result.candidates else 0}")

        if result.candidates:
            candidate = result.candidates[0]
            print(f"🔍 Content parts: {len(candidate.content.parts) if candidate.content else 0}")

            full_response = ""
            thinking_found = False

            for i, part in enumerate(candidate.content.parts):
                print(f"🔍 Part {i}: type={type(part)}")
                print(f"    - has_text: {hasattr(part, 'text')}")
                print(f"    - has_thought: {hasattr(part, 'thought')}")

                if hasattr(part, 'text') and part.text:
                    print(f"    - text length: {len(part.text)}")
                    full_response += part.text

                if hasattr(part, 'thought') and part.thought:
                    print(f"    - thought length: {len(part.thought)}")
                    print(f"    - thought preview: {part.thought[:100]}...")
                    thinking_found = True

            print("\n📄 Full Response:")
            print(f"{full_response}")

            print(f"\n🧠 Thinking Status: {'✅ Found' if thinking_found else '❌ Not Found'}")

            if hasattr(result, 'usage_metadata'):
                print(f"📊 Usage metadata: {result.usage_metadata}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_thinking())
