"""
Test script for Letta pipeline with development features
"""

import os
import sys
import json
import asyncio
import pytest

# Add OpenWebUI backend to Python path
OPENWEBUI_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), '../open-webui/backend'))
sys.path.append(OPENWEBUI_BACKEND)
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from letta import Pipe

# Test messages to cover different scenarios
TEST_MESSAGES = [
    {
        "name": "basic_greeting",
        "message": "Hello! How are you?",
        "description": "Basic greeting to test simple responses"
    },
    {
        "name": "complex_query",
        "message": "Explain how quantum computers work and their potential impact on cryptography.",
        "description": "Complex query to test reasoning steps"
    },
    {
        "name": "long_conversation",
        "message": "Write a detailed story about a space explorer discovering a new planet.",
        "description": "Long response to test streaming and usage statistics"
    }
]

class MockRequest:
    """Mock FastAPI request object"""
    def __init__(self):
        self.app = type('MockApp', (), {'state': type('MockState', (), {'config': {}})()})

class MockEventEmitter:
    """Mock event emitter that logs events"""
    def __init__(self, log_file="test_events.jsonl"):
        self.log_file = log_file
        self.events = []
        # Create or clear the log file
        with open(log_file, 'w') as f:
            f.write(f"# Test Events Log - {datetime.now().isoformat()}\n")

    async def __call__(self, event):
        self.events.append(event)
        # Log the event
        with open(self.log_file, 'a') as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "event": event
            }) + '\n')
        # Print event for debugging
        print(f"\nEvent Emitted: {json.dumps(event, indent=2)}")

def setup_test_environment():
    """Setup test environment and validate configuration"""
    # Load environment variables
    load_dotenv()
    
    # Validate required environment variables
    required_vars = ['LETTA_BASE_URL', 'LETTA_AGENT_ID', 'LETTA_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Print test configuration
    print("\nTest Configuration:")
    print(f"LETTA_BASE_URL: {os.getenv('LETTA_BASE_URL')}")
    print(f"LETTA_AGENT_ID: {os.getenv('LETTA_AGENT_ID')}")
    print(f"LETTA_PASSWORD: {'*' * len(os.getenv('LETTA_PASSWORD'))}")

def configure_pipe_for_testing():
    """Configure Letta pipeline for testing"""
    pipe = Pipe()
    
    # Enable development features
    pipe.valves.DEV_MODE = True
    pipe.valves.LOG_RAW_CHUNKS = True
    pipe.valves.LOG_PARSED_CHUNKS = True
    pipe.valves.LOG_EVENTS = True
    pipe.valves.SAVE_RESPONSES = True
    pipe.valves.RESPONSE_LOG_PATH = "test_responses.jsonl"
    
    return pipe

async def process_message(pipe, message, event_emitter):
    """Process a test message and handle the response"""
    try:
        # Prepare test data
        test_body = {
            "chat_id": os.getenv('TEST_CHAT_ID', 'test-chat-123'),
            "message_id": os.getenv('TEST_MESSAGE_ID', 'test-message-456'),
            "messages": [{"role": "user", "content": message}],
            "stream": True
        }
        
        test_user = {
            "id": "test-user-001",
            "name": "Test User",
            "email": "test@example.com",
            "role": "user"
        }
        
        # Process message
        result = await pipe.pipe(
            body=test_body,
            __user__=test_user,
            __request__=MockRequest(),
            __event_emitter__=event_emitter
        )
        
        # Handle streaming response
        if hasattr(result, '__aiter__'):
            async for chunk in result:
                print(f"\nResponse chunk: {chunk}")
        else:
            print(f"\nFull response: {result}")
            
        return True
    
    except Exception as e:
        print(f"\n❌ Error processing message: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_letta_pipeline():
    """Main test function"""
    print("\n=== Starting Letta Pipeline Tests ===\n")
    
    try:
        # Setup
        setup_test_environment()
        pipe = configure_pipe_for_testing()
        event_emitter = MockEventEmitter()
        
        # Test results
        results = []
        
        # Process each test message
        for test_case in TEST_MESSAGES:
            print(f"\n--- Testing: {test_case['name']} ---")
            print(f"Description: {test_case['description']}")
            print(f"Message: {test_case['message']}\n")
            
            success = await process_message(
                pipe=pipe,
                message=test_case['message'],
                event_emitter=event_emitter
            )
            
            results.append({
                "test_case": test_case['name'],
                "success": success
            })
            
            # Add delay between tests
            await asyncio.sleep(2)
        
        # Print test summary
        print("\n=== Test Summary ===")
        for result in results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test_case']}")
        
        # Check log files
        response_log = Path("test_responses.jsonl")
        event_log = Path("test_events.jsonl")
        
        if response_log.exists():
            print(f"\nResponse log created: {response_log}")
            print(f"Size: {response_log.stat().st_size} bytes")
        
        if event_log.exists():
            print(f"\nEvent log created: {event_log}")
            print(f"Size: {event_log.stat().st_size} bytes")
        
        # Final status
        success_count = sum(1 for r in results if r['success'])
        print(f"\nTests completed: {success_count}/{len(results)} successful")
        
        assert success_count == len(results), "Not all tests passed"
        
    except Exception as e:
        print(f"\n❌ Test suite error: {str(e)}")
        raise

def analyze_logs():
    """Analyze test logs for patterns and issues"""
    try:
        # Analyze response log
        with open("test_responses.jsonl", 'r') as f:
            responses = [json.loads(line) for line in f if line.strip() and not line.startswith('#')]
        
        # Analyze event log
        with open("test_events.jsonl", 'r') as f:
            events = [json.loads(line) for line in f if line.strip() and not line.startswith('#')]
        
        # Print analysis
        print("\n=== Log Analysis ===")
        print(f"Total responses: {len(responses)}")
        print(f"Total events: {len(events)}")
        
        # Response types
        response_types = {}
        for r in responses:
            r_type = r.get('type', 'unknown')
            response_types[r_type] = response_types.get(r_type, 0) + 1
        
        print("\nResponse Types:")
        for r_type, count in response_types.items():
            print(f"- {r_type}: {count}")
        
        # Event types
        event_types = {}
        for e in events:
            e_type = e.get('event', {}).get('type', 'unknown')
            event_types[e_type] = event_types.get(e_type, 0) + 1
        
        print("\nEvent Types:")
        for e_type, count in event_types.items():
            print(f"- {e_type}: {count}")
        
    except Exception as e:
        print(f"\n❌ Log analysis error: {str(e)}")

if __name__ == "__main__":
    # Run tests
    asyncio.run(test_letta_pipeline())
    
    # Analyze logs
    analyze_logs()