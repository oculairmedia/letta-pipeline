"""
title: Letta Manifold Pipe
description: Interactive Letta AI integration with event emitters and configurable settings
author: OpenHands
version: 0.3.0
license: MIT
"""

import os
import json
import logging
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import List, Union, Dict, Callable, Awaitable, Any, Iterator
from pydantic import BaseModel, Field
from fastapi import Request
from open_webui.utils.chat import generate_chat_completion
from open_webui.models.users import Users
from dataclasses import dataclass

# Constants
class TASKS:
    DEFAULT = "default"

# Setup logging
name = "Letta AI"

def setup_logger():
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.set_name(name)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = setup_logger()

@dataclass
class User:
    id: str
    email: str
    name: str
    role: str

class Pipe:
    class Valves(BaseModel):
        LETTA_BASE_URL: str = Field(
            default=os.getenv("LETTA_BASE_URL", "https://letta2.oculair.ca"),
            description="Base URL for Letta API",
        )
        LETTA_AGENT_ID: str = Field(
            default=os.getenv("LETTA_AGENT_ID", ""),
            description="Agent ID for Letta authentication",
        )
        LETTA_PASSWORD: str = Field(
            default=os.getenv("LETTA_PASSWORD", ""),
            description="Password for Letta authentication",
        )
        ENABLE_TOOLS: bool = Field(
            default=True,
            description="Enable Open WebUI tool integration"
        )
        DEV_MODE: bool = Field(
            default=False,
            description="Enable development mode with detailed logging"
        )
        TASK_MODEL: str = Field(
            default="",
            description="Model to use for special tasks. If empty, uses the default model."
        )
        SAVE_RESPONSES: bool = Field(
            default=True,
            description="Save responses to file in dev mode"
        )
        RESPONSE_LOG_PATH: str = Field(
            default="letta_responses.jsonl",
            description="Path to save response logs"
        )

    class UserValves(BaseModel):
        DISPLAY_EVENTS: bool = Field(
            default=True,
            description="Display event emitters during processing (user-specific)",
        )
        SHOW_REASONING: bool = Field(
            default=True,
            description="Show reasoning steps in events (user-specific)",
        )
        SHOW_USAGE_STATS: bool = Field(
            default=True,
            description="Show usage statistics in events (user-specific)",
        )

    def __init__(self):
        self.id = "letta_ai"
        self.type = "manifold"
        self.name = "Letta: "
        self.valves = self.Valves()
        # Initialize response log file in dev mode
        if self.valves.DEV_MODE and self.valves.SAVE_RESPONSES:
            self._init_response_log()

    def _init_response_log(self):
        """Initialize the response log file with a header"""
        log_path = Path(self.valves.RESPONSE_LOG_PATH)
        if not log_path.exists():
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('# Letta Response Log\n')
                f.write(f'# Created: {datetime.now().isoformat()}\n')
                f.write('# Format: {"timestamp": "", "type": "", "content": ""}\n\n')

    def _log_response(self, response_type: str, content: Any):
        """Log a response to the response log file"""
        if not (self.valves.DEV_MODE and self.valves.SAVE_RESPONSES):
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": response_type,
            "content": content
        }
        
        with open(self.valves.RESPONSE_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')

    async def emit_message(self, event_emitter: Callable, message: str):
        """Emit a message event"""
        if event_emitter is not None:
            await event_emitter({
                "type": "message",
                "data": {"content": message}
            })

    async def emit_status(self, event_emitter: Callable, level: str, message: str, done: bool):
        """Emit a status event"""
        if event_emitter is not None:
            await event_emitter({
                "type": "status",
                "data": {
                    "status": "complete" if done else "in_progress",
                    "level": level,
                    "description": message,
                    "done": done,
                },
            })

    def pipes(self) -> List[dict]:
        """Fetch available Letta configurations"""
        return [
            {
                "id": f"letta.{self.valves.LETTA_AGENT_ID}",
                "name": f"Letta",
                "meta": {
                    "provider": "letta",
                    "agent_id": self.valves.LETTA_AGENT_ID,
                    "profile": {
                        "name": "Letta",
                        "description": "A helpful AI assistant that can engage in natural conversations and help with various tasks.",
                        "avatar": "https://letta2.oculair.ca/static/letta-avatar.png"
                    },
                    "settings": {
                        "dev_mode": {
                            "type": "boolean",
                            "label": "Developer Mode",
                            "description": "Enable detailed logging and debug information",
                            "value": self.valves.DEV_MODE
                        }
                    }
                },
            }
        ]

    def update_settings(self, settings: dict) -> None:
        """Update function settings"""
        if "dev_mode" in settings:
            self.valves.DEV_MODE = settings["dev_mode"]
            if self.valves.DEV_MODE and self.valves.SAVE_RESPONSES:
                self._init_response_log()

    async def format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages according to the Letta API specification"""
        formatted_messages = []
        for msg in messages:
            # Only include supported roles
            if msg.get("role") not in ["user", "system", "assistant"]:
                continue

            formatted_msg = {
                "role": "system" if msg["role"] == "system" else "user",
                "content": msg.get("content", ""),
            }
            formatted_messages.append(formatted_msg)

        # Ensure we have at least one message
        if not formatted_messages:
            formatted_messages.append({"role": "user", "content": "Hello"})

        if self.valves.DEV_MODE:
            logger.debug(f"Formatted messages: {json.dumps(formatted_messages, indent=2)}")
        return formatted_messages

    async def get_letta_response(
        self,
        messages: List[Dict[str, str]],
        event_emitter: Callable = None,
        user_valves: UserValves = None
    ) -> str:
        """Send messages to the Letta agent and get its response"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "X-BARE-PASSWORD": f"password {self.valves.LETTA_PASSWORD}"
        }

        formatted_messages = await self.format_messages(messages)
        payload = {
            "messages": [formatted_messages[-1]],  # Send only the last message
            "stream_steps": True,
            "stream_tokens": True,
        }

        url = f"{self.valves.LETTA_BASE_URL}/v1/agents/{self.valves.LETTA_AGENT_ID}/messages/stream"

        if self.valves.DEV_MODE:
            logger.debug(f"Sending request to {url}")
            logger.debug(f"Request data: {json.dumps(payload, indent=2)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 422:
                        error_text = await response.text()
                        logger.error(f"API Validation Error: {error_text}")
                        raise ValueError(f"API Validation Error: {error_text}")

                    response.raise_for_status()
                    
                    # Process the streaming response
                    response_content = []
                    async for line in response.content:
                        decoded_line = line.decode('utf-8')
                        if not decoded_line.strip():
                            continue

                        if self.valves.DEV_MODE:
                            logger.debug(f"Raw chunk: {decoded_line}")

                        if not decoded_line.startswith('data: '):
                            continue

                        if decoded_line == 'data: [DONE]':
                            if self.valves.DEV_MODE:
                                logger.debug("Received [DONE] marker")
                            break

                        try:
                            chunk_data = json.loads(decoded_line[6:])
                            message_type = chunk_data.get("message_type")

                            if message_type == "assistant_message":
                                content = chunk_data.get("content", "")
                                if content:
                                    response_content.append(content)
                                    # Clear processing status
                                    await self.emit_status(event_emitter, "info", "", True)
                                    # Stream the content
                                    await self.emit_message(event_emitter, content)

                            elif message_type == "usage_statistics" and getattr(user_valves, "SHOW_USAGE_STATS", True):
                                if self.valves.DEV_MODE:
                                    logger.debug(f"Usage statistics: {chunk_data}")
                                await event_emitter({
                                    "type": "usage",
                                    "data": chunk_data
                                })

                            elif message_type == "reasoning_message" and getattr(user_valves, "SHOW_REASONING", True):
                                reasoning_data = {
                                    "step": chunk_data.get("step", "unknown"),
                                    "content": chunk_data.get("content", "")
                                }
                                if self.valves.DEV_MODE:
                                    logger.debug(f"Reasoning: {reasoning_data}")
                                await event_emitter({
                                    "type": "reasoning",
                                    "data": reasoning_data
                                })

                        except json.JSONDecodeError as e:
                            if self.valves.DEV_MODE:
                                logger.error(f"JSON Parse Error: {str(e)}")
                                logger.error(f"Problem chunk: {decoded_line}")

            return "\n".join(response_content)

        except aiohttp.ClientError as e:
            logger.error(f"Error communicating with Letta agent: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def pipe(
        self,
        body: dict,
        __user__: dict,
        __request__: Request,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None,
        __task__: str = TASKS.DEFAULT,
        __model__: str = None,
    ) -> Union[str, Iterator[str]]:
        """Main processing pipeline with tool support and event emitters"""
        try:
            # Get user valves with defaults
            user_valves = self.UserValves()
            
            # Handle task-specific processing
            if __task__ and __task__ != TASKS.DEFAULT:
                try:
                    task_model = self.valves.TASK_MODEL or __model__
                    if not task_model:
                        logger.error("No task model specified")
                        return f"{name}: Error - No task model specified"
                        
                    response = await generate_chat_completion(
                        __request__,
                        {
                            "model": task_model,
                            "messages": body.get("messages", []),
                            "stream": False,
                        },
                        user=User(**__user__)
                    )
                    if not response or "choices" not in response:
                        logger.error("Invalid response format")
                        return f"{name}: Error - Invalid response format"
                        
                    return f"{name}: {response['choices'][0]['message']['content']}"
                except Exception as e:
                    logger.error(f"Error processing task {__task__}: {e}")
                    return f"{name}: Error processing {__task__}"

            # Handle tool execution via Open WebUI
            if body.get("tools") and self.valves.ENABLE_TOOLS:
                user = Users.get_user_by_id(__user__["id"])
                return await generate_chat_completion(__request__, body, user)

            # Process messages
            messages = body.get("messages", [])
            if not messages:
                await self.emit_status(__event_emitter__, "error", "No messages provided", True)
                return ""

            await self.emit_status(__event_emitter__, "info", "Sending request to Letta agent...", False)

            try:
                response = await self.get_letta_response(
                    messages,
                    event_emitter=__event_emitter__,
                    user_valves=user_valves
                )
                
                if self.valves.DEV_MODE:
                    logger.debug(f"Letta agent response: {response}")
                
                if response:
                    await self.emit_status(__event_emitter__, "success", "Response received", True)
                    return response
                else:
                    await self.emit_status(__event_emitter__, "error", "Empty response from Letta agent", True)
                    return ""

            except Exception as e:
                error_msg = f"Error processing request: {str(e)}"
                logger.error(error_msg)
                await self.emit_status(__event_emitter__, "error", error_msg, True)
                return ""

        except Exception as e:
            if __event_emitter__:
                await __event_emitter__({
                    "type": "error",
                    "data": {
                        "error": str(e),
                        "type": type(e).__name__
                    }
                })
            return f"Letta Error: {str(e)}"