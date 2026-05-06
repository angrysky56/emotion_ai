#!/usr/bin/env python3
"""
Simple Thinking Fix Test
========================

Test the fixed thinking system to ensure it works properly
with the non-streaming approach.
"""

import asyncio
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_thinking_fix():
    """Test the fixed thinking system"""
    
    try:
        # Import required modules
        from thinking_processor import ThinkingProcessor, create_thinking_enabled_chat
        from google import genai
        from dotenv import load_dotenv
        
        # Load environment
        load_dotenv()
        
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            print("❌ Error: GOOGLE_API_KEY not found")
            return False
        
        print("🧠 Testing Fixed Thinking System")
        print("="*50)
        
        # Initialize client and processor
        client = genai.Client(api_key=api_key)
        thinking_processor = ThinkingProcessor(client)
        
        # Create thinking-enabled chat
        system_instruction = """You are Aura, an AI with transparent reasoning. Think through problems step-by-step and show your reasoning process."""
        
        chat = create_thinking_enabled_chat(
            client=client,
            model=os.getenv('AURA_MODEL', 'gemini-2.5-flash-preview-05-20'),
            system_instruction=system_instruction,
            thinking_budget=8192
        )
        
        # Test question
        test_question = "How do you approach solving complex problems?"
        
        print(f"\n❓ Test Question: {test_question}")
        print("⏳ Processing with thinking extraction...")
        
        # Process with thinking
        result = await thinking_processor.process_message_with_thinking(
            chat=chat,
            message=test_question,
            user_id="test_fix",
            include_thinking_in_response=False
        )
        
        # Display results
        print("\n" + "="*60)
        print("🧠 THINKING SYSTEM TEST RESULTS")
        print("="*60)
        
        print(f"✅ Processing successful: {not result.error}")
        print(f"🧠 Has thinking: {result.has_thinking}")
        print(f"📊 Thinking chunks: {result.thinking_chunks}")
        print(f"💬 Answer chunks: {result.answer_chunks}")
        print(f"⏱️ Processing time: {result.processing_time_ms:.1f}ms")
        
        if result.has_thinking and result.thoughts:
            print("\n💭 THINKING CONTENT:")
            print(f"{result.thoughts[:300]}{'...' if len(result.thoughts) > 300 else ''}")
        else:
            print("\n💭 No thinking content captured")
        
        print("\n💬 FINAL ANSWER:")
        print(f"{result.answer}")
        
        # Test for thinking leakage in the answer
        thinking_indicators = [
            'reflecting on', 'alright, so', 'operational state',
            'let me think', 'considering', 'analyzing'
        ]
        
        answer_lower = result.answer.lower()
        thinking_leaked = any(indicator in answer_lower for indicator in thinking_indicators)
        
        print("\n🔍 LEAK CHECK:")
        print(f"Thinking leaked into answer: {thinking_leaked}")
        
        if thinking_leaked:
            print("⚠️ Warning: Thinking content may have leaked into the final answer")
            print("This suggests the fix may need further refinement")
        else:
            print("✅ Clean separation between thinking and answer")
        
        print("\n📈 SYSTEM STATUS:")
        print(f"Error: {result.error if result.error else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    async def main():
        print("🧠 Aura Thinking Fix Test")
        print("="*50)
        
        success = await test_thinking_fix()
        
        print("\n" + "="*50)
        if success:
            print("✅ Thinking fix test completed!")
            print("💡 Try the conversation endpoint to see if the issue is resolved.")
        else:
            print("⚠️ Fix may need additional work. Check the output above.")
        
        print("\n📝 Next steps:")
        print("1. Test with the main Aura conversation endpoint")
        print("2. Check the /thinking-status endpoint")
        print("3. Verify thinking data in conversation responses")
    
    asyncio.run(main())
