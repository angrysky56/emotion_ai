#!/usr/bin/env python3
"""
Test Thinking Functionality for Aura Backend
============================================

This script tests the thinking extraction capabilities to ensure proper
integration with the Aura emotion AI system.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_thinking_functionality():
    """Test the thinking processor and integration"""
    
    try:
        # Import required modules
        from thinking_processor import ThinkingProcessor, create_thinking_enabled_chat
        from google import genai
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("❌ GOOGLE_API_KEY not found in environment variables")
            return False
        
        # Initialize client
        client = genai.Client(api_key=api_key)
        logger.info("✅ Google Gemini client initialized")
        
        # Initialize thinking processor
        thinking_processor = ThinkingProcessor(client)
        logger.info("✅ Thinking processor initialized")
        
        # Create thinking-enabled chat
        system_instruction = """You are Aura, a helpful AI assistant. Please think through problems step by step and show your reasoning process."""
        
        chat = create_thinking_enabled_chat(
            client=client,
            model=os.getenv('AURA_MODEL', 'gemini-2.5-flash-preview-05-20'),
            system_instruction=system_instruction,
            thinking_budget=4096
        )
        logger.info("✅ Thinking-enabled chat session created")
        
        # Test messages
        test_messages = [
            "What is 127 * 83? Please think through this step by step.",
            "Explain why the sky appears blue during the day.",
            "What are the pros and cons of renewable energy?"
        ]
        
        for i, message in enumerate(test_messages, 1):
            logger.info("\n🧪 Test %s: %s", i, message)
            
            try:
                # Process message with thinking
                result = await thinking_processor.process_message_with_thinking(
                    chat=chat,
                    message=message,
                    user_id="test_user",
                    include_thinking_in_response=False,
                    thinking_summary_length=150
                )
                
                # Display results
                logger.info("✅ Test %s completed successfully", i)
                logger.info("   🧠 Has thinking: %s", result.has_thinking)
                logger.info("   📊 Thinking chunks: %s", result.thinking_chunks)
                logger.info("   💬 Answer chunks: %s", result.answer_chunks)
                logger.info("   ⏱️ Processing time: %sms", result.processing_time_ms)
                
                if result.has_thinking:
                    logger.info("   💭 Thinking summary: %s", result.thinking_summary)
                    logger.info("   🧠 Full thoughts (first 200 chars): %s...", result.thoughts[:200])
                
                logger.info("   💬 Answer: %s", result.answer)
                
                # Brief pause between tests
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error("❌ Test %s failed: %s", i, e)
                return False
        
        logger.info("\n🎉 All thinking tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error("❌ Thinking test setup failed: %s", e)
        return False

async def test_thinking_status_endpoint():
    """Test the thinking status endpoint"""
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/thinking-status') as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("✅ Thinking status endpoint working:")
                    logger.info("   Status: %s", data.get('status'))
                    logger.info("   Thinking enabled: %s", data.get('thinking_configuration', {}).get('thinking_enabled')
                    logger.info("   Budget: %s", data.get('thinking_configuration', {}).get('thinking_enabled')
                    return True
                else:
                    logger.error("❌ Status endpoint returned %s", response.status)
                    return False
                    
    except Exception as e:
        logger.warning("⚠️ Could not test status endpoint (server may not be running): %s", e)
        return False

if __name__ == "__main__":
    async def main():
        logger.info("🚀 Starting Aura Thinking Functionality Tests")
        
        # Test 1: Basic thinking functionality
        logger.info("\n📝 Testing thinking processor...")
        thinking_success = await test_thinking_functionality()
        
        # Test 2: Status endpoint (optional - requires running server)
        logger.info("\n📡 Testing thinking status endpoint...")
        endpoint_success = await test_thinking_status_endpoint()
        
        # Summary
        logger.info("\n📊 Test Summary:")
        logger.info("   Thinking Processor: %s", '✅ PASS' if thinking_success else '❌ FAIL')
        logger.info("   Status Endpoint: %s", '✅ PASS' if endpoint_success else '⚠️ SKIP')
        
        if thinking_success:
            logger.info("\n🎉 Thinking functionality is working correctly!")
            logger.info("💡 Tips:")
            logger.info("   - Set INCLUDE_THINKING_IN_RESPONSE=true to show reasoning in responses")
            logger.info("   - Adjust THINKING_BUDGET to control reasoning depth")
            logger.info("   - Check /thinking-status endpoint for system status")
        else:
            logger.error("\n❌ Thinking functionality has issues. Check the logs above.")
            sys.exit(1)
    
    asyncio.run(main())
