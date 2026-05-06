#!/usr/bin/env python3
"""
Simple test to verify the search endpoint routing through Aura's MCP tools
Uses curl for HTTP requests to avoid dependency issues
"""

import subprocess
import json
import time

def run_curl_request(endpoint, data=None):
    """Run a curl request and return the response"""
    cmd = [
        "curl", "-s", "-X", "POST",
        f"http://localhost:8000{endpoint}",
        "-H", "Content-Type: application/json"
    ]
    
    if data:
        cmd.extend(["-d", json.dumps(data)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print(f"❌ Curl error: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def test_search_endpoint():
    """Test the search endpoint to verify MCP tool integration"""
    
    print("🧪 Testing search endpoint MCP tool integration...")
    
    # Test 1: Basic search
    print("\n📝 Test 1: Basic memory search")
    response = run_curl_request("/search", {
        "user_id": "test_user",
        "query": "memory system test",
        "n_results": 3
    })
    
    if response:
        print("✅ Response received:")
        print(f"   📊 Total found: {response.get('total_found', 0)}")
        print(f"   🔍 Search type: {response.get('search_type', 'unknown')}")
        print(f"   🎥 Video archives: {response.get('includes_video_archives', False)}")
        
        if response.get('results'):
            print(f"   📄 Has results: {len(response['results'])} items")
        else:
            print("   📄 No results returned")
    else:
        print("❌ No response received")
    
    # Test 2: Health check to ensure server is running
    print("\n🏥 Test 2: Health check")
    health_response = run_curl_request("/health")
    
    if health_response:
        print(f"✅ Server healthy: {health_response.get('status', 'unknown')}")
    else:
        print("❌ Server health check failed")
    
    print("\n🎉 Search integration test completed!")
    print("💡 Check VS Code terminal for detailed logs from the backend")

if __name__ == "__main__":
    # Small delay to ensure server is ready
    time.sleep(1)
    test_search_endpoint()
    
    print("\n🔗 If the search_type shows 'unified_memory_search' or 'active_memory_search',")
    print("   the fix is working and UI should now connect to Aura's MCP tools!")
