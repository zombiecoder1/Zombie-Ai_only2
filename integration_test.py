"""
Integration Test for Hello Zombie Main Server
Tests all endpoints and functionality
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:12346"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing Health Endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["ollama_status"] == "healthy"
    assert data["memory_status"] == "healthy"
    print("✅ Health endpoint: PASS")

def test_models():
    """Test models endpoint"""
    print("🔍 Testing Models Endpoint...")
    response = requests.get(f"{BASE_URL}/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) > 0
    print("✅ Models endpoint: PASS")

def test_chat():
    """Test chat endpoint"""
    print("🔍 Testing Chat Endpoint...")
    payload = {
        "agent": "hello_zombie",
        "input": "What is 2+2?",
        "context": {"test": True}
    }
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "author" in data
    assert "text" in data
    assert "timestamp" in data
    assert "model" in data
    assert "success" in data
    assert data["success"] == True
    print("✅ Chat endpoint: PASS")
    return data["id"]

def test_agent_config():
    """Test agent configuration endpoint"""
    print("🔍 Testing Agent Config Endpoint...")
    response = requests.post(f"{BASE_URL}/agents/configure")
    assert response.status_code == 200
    data = response.json()
    assert "agent" in data
    assert "infrastructure" in data
    assert data["agent"]["name"] == "Hello Zombie"
    print("✅ Agent config endpoint: PASS")

def test_conversation_history(conversation_id):
    """Test conversation history endpoint"""
    print("🔍 Testing Conversation History Endpoint...")
    response = requests.get(f"{BASE_URL}/conversations/hello_zombie")
    assert response.status_code == 200
    data = response.json()
    assert "conversations" in data
    assert len(data["conversations"]) > 0
    # Check if our test conversation is in history
    found = False
    for conv in data["conversations"]:
        if conv["id"] == conversation_id:
            found = True
            break
    assert found == True
    print("✅ Conversation history endpoint: PASS")

def test_error_handling():
    """Test error handling"""
    print("🔍 Testing Error Handling...")
    # Test invalid chat payload
    response = requests.post(f"{BASE_URL}/chat", json={"invalid": "payload"})
    assert response.status_code == 422  # Validation error
    print("✅ Error handling: PASS")

def run_integration_tests():
    """Run all integration tests"""
    print("🚀 Starting Hello Zombie Integration Tests...")
    print("=" * 50)
    
    try:
        # Test all endpoints
        test_health()
        test_models()
        conversation_id = test_chat()
        test_agent_config()
        test_conversation_history(conversation_id)
        test_error_handling()
        
        print("=" * 50)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Ollama integration: Working")
        print("✅ Main server: Healthy")
        print("✅ Memory system: Functional")
        print("✅ API endpoints: All responding")
        print("✅ Error handling: Proper")
        
        return True
        
    except Exception as e:
        print("=" * 50)
        print(f"❌ INTEGRATION TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)
