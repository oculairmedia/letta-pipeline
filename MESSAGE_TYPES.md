# Letta Message Types

## Core Message Types

### 1. System Messages
- **Role:** `"role": "system"`
- **Purpose:** Provide system-level instructions or context
- **Format:**
```json
{
    "role": "system",
    "content": "System instruction or context"
}
```

### 2. User Messages
- **Role:** `"role": "user"`
- **Purpose:** User queries or commands
- **Format:**
```json
{
    "role": "user",
    "content": "User query or command"
}
```

### 3. Assistant Messages
- **Type:** `"message_type": "assistant_message"`
- **Purpose:** Main response content from the assistant
- **Format:**
```json
{
    "message_type": "assistant_message",
    "content": "Assistant's response"
}
```

### 4. Tool Messages

#### Tool Call
- **Purpose:** Invoke specific tools or functions
- **Format:**
```json
{
    "role": "assistant",
    "content": null,
    "tool_calls": [{
        "id": "call_xyz",
        "type": "function",
        "function": {
            "name": "tool_name",
            "arguments": {
                "param1": "value1",
                "param2": "value2"
            }
        }
    }]
}
```

#### Tool Return
- **Purpose:** Results from tool execution
- **Format:**
```json
{
    "role": "tool",
    "content": "Tool execution result",
    "tool_call_id": "call_xyz"
}
```

### 5. Reasoning Messages
- **Type:** `"message_type": "reasoning_message"`
- **Purpose:** Internal thought processes and reasoning steps
- **Format:**
```json
{
    "message_type": "reasoning_message",
    "message": "Reasoning step description"
}
```

### 6. Usage Statistics
- **Type:** `"message_type": "usage_statistics"`
- **Purpose:** Token usage and performance metrics
- **Format:**
```json
{
    "message_type": "usage_statistics",
    "completion_tokens": 123,
    "prompt_tokens": 456,
    "total_tokens": 579,
    "step_count": 1
}
```

## Message Flow

1. **Input Flow:**
   ```
   System Message (optional)
   → User Message
   → Tool Call (if needed)
   → Tool Return (if tool used)
   ```

2. **Output Flow:**
   ```
   Reasoning Messages (internal)
   → Assistant Message
   → Usage Statistics
   ```

## Important Notes

1. **Tool Call Requirements:**
   - Tool calls must be followed by tool return messages
   - The `use_assistant_message` parameter affects tool argument parsing

2. **Message Processing:**
   - System messages set context for the entire conversation
   - User messages trigger the main processing pipeline
   - Reasoning messages are internal and can be shown/hidden
   - Usage statistics are sent after completion

3. **Event Handling:**
   - Messages emit corresponding events for UI updates
   - Events can be controlled via user valves:
     - `SHOW_REASONING`: Toggle reasoning messages
     - `SHOW_USAGE_STATS`: Toggle usage statistics

4. **Development Mode:**
   - Raw chunks are logged in dev mode
   - Parsed messages are logged separately
   - Response logs include all message types

## Example Conversation Flow

```json
// System context
{
    "role": "system",
    "content": "You are a helpful assistant."
}

// User query
{
    "role": "user",
    "content": "What's the weather?"
}

// Internal reasoning (not visible to user)
{
    "message_type": "reasoning_message",
    "message": "I should check the weather API"
}

// Tool call
{
    "role": "assistant",
    "content": null,
    "tool_calls": [{
        "id": "weather_1",
        "type": "function",
        "function": {
            "name": "get_weather",
            "arguments": {"location": "current"}
        }
    }]
}

// Tool return
{
    "role": "tool",
    "content": "Sunny, 22°C",
    "tool_call_id": "weather_1"
}

// Assistant response
{
    "message_type": "assistant_message",
    "content": "It's currently sunny and 22°C."
}

// Usage stats
{
    "message_type": "usage_statistics",
    "completion_tokens": 10,
    "prompt_tokens": 20,
    "total_tokens": 30,
    "step_count": 1
}
```