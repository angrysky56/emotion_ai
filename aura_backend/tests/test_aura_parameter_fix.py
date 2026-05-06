#!/usr/bin/env python3
"""
Test Script for Aura Parameter Formatting Fix
==============================================

This script tests the parameter formatting for Aura MCP tools to ensure
the validation errors are resolved.
"""

import sys
from pathlib import Path

# Add the aura_backend directory to the path
aura_backend_path = Path(__file__).parent / "aura_backend"
sys.path.insert(0, str(aura_backend_path))

try:
    from smart_mcp_parameter_handler import SmartMCPParameterHandler
    print("✅ Successfully imported SmartMCPParameterHandler")
except ImportError as e:
    print(f"❌ Failed to import SmartMCPParameterHandler: {e}")
    sys.exit(1)

def test_aura_parameter_formatting():
    """Test parameter formatting for Aura tools"""
    
    handler = SmartMCPParameterHandler()
    
    # Test case 1: store_aura_conversation with FastMCP format
    print("\n" + "="*60)
    print("🧪 Testing store_aura_conversation parameter formatting")
    print("="*60)
    
    # Sample arguments that would come from Gemini
    test_arguments = {
        "user_id": "Ty",
        "message": "This is a test message for storage",
        "sender": "user",
        "emotional_state": "Happy:Medium",
        "cognitive_focus": "KS"
    }
    
    # Mock schema for store_aura_conversation (FastMCP with Pydantic)
    mock_schema = {
        "inputSchema": {
            "type": "object",
            "properties": {
                "params": {
                    "$ref": "#/$defs/AuraConversationStore"
                }
            },
            "required": ["params"],
            "$defs": {
                "AuraConversationStore": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "message": {"type": "string"},
                        "sender": {"type": "string"},
                        "emotional_state": {"type": "string", "default": None},
                        "cognitive_focus": {"type": "string", "default": None},
                        "session_id": {"type": "string", "default": None}
                    },
                    "required": ["user_id", "message", "sender"]
                }
            }
        }
    }
    
    # Test format detection from schema
    input_schema = mock_schema["inputSchema"]
    print(f"📋 Mock schema inputSchema: {input_schema}")
    print(f"📋 Has $defs: {'$defs' in input_schema}")
    print(f"📋 $ref in str: {'$ref' in str(input_schema)}")
    print(f"📋 Properties: {input_schema.get('properties', {})}")
    print(f"📋 Required: {input_schema.get('required', [])}")
    
    detected_format = handler._detect_format_from_schema(
        input_schema,
        "store_aura_conversation"
    )
    print(f"🔍 Detected format from schema: {detected_format}")
    
    # Test format detection from heuristics
    heuristic_format = handler._detect_format_from_heuristics(
        "store_aura_conversation",
        "aura-companion",
        test_arguments
    )
    print(f"🎯 Detected format from heuristics: {heuristic_format}")
    
    # Test parameter formatting with new logic
    formatted_params = handler.format_parameters(
        tool_name="store_aura_conversation",
        server_name="aura-companion", 
        arguments=test_arguments,
        tool_schema=mock_schema
    )
    
    print(f"📤 Original arguments: {test_arguments}")
    print(f"📥 Formatted parameters: {formatted_params}")
    
    # Test the search_aura_memories case specifically
    print("\n🔧 Testing search_aura_memories case:")
    search_params = handler.format_parameters(
        tool_name="search_aura_memories",
        server_name="aura-companion",
        arguments={'params': '{"user_id": "Ty", "query": "memvid"}'},
        tool_schema={
            "inputSchema": {
                "type": "object", 
                "properties": {
                    "params": {"$ref": "#/$defs/AuraMemorySearch"}
                },
                "required": ["params"],
                "$defs": {"AuraMemorySearch": {"type": "object"}}
            }
        }
    )
    print(f"📥 Search formatted parameters: {search_params}")
    
    # Verify the formatting is correct
    if "params" in formatted_params and isinstance(formatted_params["params"], dict):
        params_obj = formatted_params["params"]
        required_fields = ["user_id", "message", "sender"]
        
        all_required_present = all(field in params_obj for field in required_fields)
        print(f"✅ All required fields present: {all_required_present}")
        
        if all_required_present:
            print("🎉 Parameter formatting test PASSED!")
            return True
        else:
            print("❌ Missing required fields in formatted parameters")
            return False
    else:
        print("❌ Parameters not properly wrapped for FastMCP")
        return False

def test_json_string_handling():
    """Test handling of JSON string parameters"""
    print("\n" + "="*60)
    print("🧪 Testing JSON string parameter handling")
    print("="*60)
    
    handler = SmartMCPParameterHandler()
    
    # Simulate receiving a JSON string as params (the original error case)
    json_string_args = {
        "params": '{"user_id": "Ty", "message": "Test message", "sender": "user"}'
    }
    
    print(f"📤 Input with JSON string: {json_string_args}")
    
    formatted_result = handler._apply_format(json_string_args, 'fastmcp')
    
    print(f"📥 Formatted result: {formatted_result}")
    
    # Check if JSON string was properly parsed
    if ("params" in formatted_result and 
        isinstance(formatted_result["params"], dict) and
        "user_id" in formatted_result["params"]):
        print("✅ JSON string was properly parsed to object")
        
        # Test the actual error case from the logs
        print("\n🔧 Testing actual error case from logs:")
        actual_error_case = {
            "params": '{"user_id": "Ty", "query": "memvid"}'
        }
        print(f"📤 Actual error input: {actual_error_case}")
        
        actual_result = handler.format_parameters(
            tool_name="search_aura_memories",
            server_name="aura-companion",
            arguments=actual_error_case,
            tool_schema={
                "inputSchema": {
                    "type": "object", 
                    "properties": {
                        "params": {"$ref": "#/$defs/AuraMemorySearch"}
                    },
                    "required": ["params"],
                    "$defs": {"AuraMemorySearch": {"type": "object"}}
                }
            }
        )
        print(f"📥 Actual result: {actual_result}")
        
        if ("params" in actual_result and 
            isinstance(actual_result["params"], dict) and
            "user_id" in actual_result["params"] and
            "query" in actual_result["params"]):
            print("✅ Actual error case properly formatted")
            return True
        else:
            print("❌ Actual error case still not properly formatted")
            return False
            
    else:
        print("❌ JSON string was not properly parsed")
        return False

def test_other_formats():
    """Test other parameter formats for comparison"""
    print("\n" + "="*60)
    print("🧪 Testing other parameter formats")
    print("="*60)
    
    handler = SmartMCPParameterHandler()
    
    # Test direct format
    direct_args = {"path": "/test/file.txt", "encoding": "utf-8"}
    direct_result = handler._apply_format(direct_args, 'direct')
    print(f"Direct format: {direct_args} -> {direct_result}")
    
    # Test wrapped format  
    wrapped_result = handler._apply_format(direct_args, 'wrapped')
    print(f"Wrapped format: {direct_args} -> {wrapped_result}")
    
    # Test FastMCP format
    fastmcp_result = handler._apply_format(direct_args, 'fastmcp')
    print(f"FastMCP format: {direct_args} -> {fastmcp_result}")
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Aura Parameter Formatting Tests")
    print("="*80)
    
    all_tests_passed = True
    
    try:
        # Run tests
        test1_result = test_aura_parameter_formatting()
        test2_result = test_json_string_handling()
        test3_result = test_other_formats()
        
        all_tests_passed = test1_result and test2_result and test3_result
        
        print("\n" + "="*80)
        if all_tests_passed:
            print("🎉 ALL TESTS PASSED! Parameter formatting should work correctly now.")
        else:
            print("❌ Some tests failed. Please check the issues above.")
            
        print("="*80)
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    sys.exit(0 if all_tests_passed else 1)
