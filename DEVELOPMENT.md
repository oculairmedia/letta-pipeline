# Development Notes

Quick reference for developing and debugging the Letta Pipeline.

## 🔧 Configuration

### Environment Variables
```bash
LETTA_BASE_URL=https://letta2.oculair.ca
LETTA_AGENT_ID=your-agent-id
LETTA_PASSWORD=your-password
```

### Valves (Settings)
```python
# Global settings
LETTA_BASE_URL: str  # Base URL for Letta API
LETTA_AGENT_ID: str  # Agent ID for authentication
LETTA_PASSWORD: str  # Password for authentication
ENABLE_TOOLS: bool   # Enable Open WebUI tool integration
DEV_MODE: bool       # Enable development mode logging
TASK_MODEL: str      # Model for special tasks
SAVE_RESPONSES: bool # Save responses to file
RESPONSE_LOG_PATH: str # Path for response logs

# User-specific settings
DISPLAY_EVENTS: bool    # Show event emitters
SHOW_REASONING: bool    # Show reasoning steps
SHOW_USAGE_STATS: bool # Show usage statistics
```

## 🔍 Debugging

### Enable Dev Mode
1. In UI: Toggle "Developer Mode" in settings
2. In code: `pipe.valves.DEV_MODE = True`

### Check Logs
```bash
tail -f letta_responses.jsonl
```

### Common Issues
1. "No messages provided" - Check body["messages"]
2. "Error processing None" - Check task handling
3. "Invalid response format" - Check API response

## 🧪 Testing

### Run Integration Test
```bash
python3 test_letta_integration.py
```

### Test Output Format
```python
# Event format
{
    "type": "status|message|reasoning|usage|error",
    "data": {
        # Status event
        "status": "in_progress|complete",
        "level": "info|success|error",
        "description": "Message text",
        "done": bool,

        # Message event
        "content": "Response text",

        # Reasoning event
        "message": "Reasoning step",

        # Usage event
        "completion_tokens": int,
        "prompt_tokens": int,
        "total_tokens": int,
        "step_count": int,

        # Error event
        "error": "Error message",
        "type": "ErrorType"
    }
}
```

## 📤 Deployment

### Upload to Open WebUI
```bash
python3 upload_letta.py
```

### Update Function
1. Delete existing function
2. Upload new version
3. Check function ID: `custom_letta`

## 🔄 Event Flow

1. Start request:
   ```
   🔄 Processing request...
   ```

2. Reasoning steps:
   ```
   🤔 Understanding the request...
   🤔 Analyzing options...
   🤔 Formulating response...
   ```

3. Response:
   ```
   [Content streaming...]
   ✓ Response complete
   ```

4. Error handling:
   ```
   ⚠️ Error message
   ```

## 🛠️ Development Tips

1. Use `logger.debug()` for detailed logs
2. Check raw chunks in dev mode
3. Monitor event emitter output
4. Test with different message types
5. Validate response formats

## 🔗 Useful Links

- [Letta API Docs](https://letta2.oculair.ca/docs)
- [Open WebUI Integration Guide](https://github.com/open-webui/open-webui)
- [Event Emitter Spec](https://github.com/open-webui/open-webui/blob/main/docs/events.md)