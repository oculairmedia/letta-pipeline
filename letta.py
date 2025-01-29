"""
title: Letta Manifold Pipe
description: Interactive Letta AI integration with event emitters and configurable settings
author: [Your Name]
author_url: [Your GitHub URL]
funding_url: https://github.com/open-webui
version: 0.2.1
license: MIT
"""

import os
import json
import time
import urllib3
from datetime import datetime
from pathlib import Path
from typing import List, Union, Iterator, Generator, Callable, Awaitable, Any
from pydantic import BaseModel, Field
from fastapi import Request
from open_webui.utils.chat import generate_chat_completion
from open_webui.models.users import Users
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Disable SSL warnings temporarily
urllib3.disable_warnings()


class Pipe:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            (urllib3.exceptions.TimeoutError, urllib3.exceptions.HTTPError)
        ),
    )
    def _send_request(self, method: str, url: str, **kwargs):
        if self.valves.DEV_MODE:
            self._dev_print(f"Sending request to URL: {url}", "DEBUG")
            self._dev_print(f"Method: {method}", "DEBUG")
            self._dev_print(f"Kwargs: {json.dumps(kwargs, indent=2)}", "DEBUG")
            self._dev_print(f"URL components: {urllib3.util.parse_url(url)}", "DEBUG")
        return self.http.request(method, url, **kwargs)

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
        DISPLAY_EVENTS: bool = Field(
            default=True,
            description="Display event emitters during processing",
        )
        SHOW_REASONING: bool = Field(
            default=True,
            description="Show reasoning steps in events",
        )
        SHOW_USAGE_STATS: bool = Field(
            default=True,
            description="Show usage statistics in events",
        )
        DEV_MODE: bool = Field(
            default=False,
            description="Enable development mode with detailed logging"
        )
        LOG_RAW_CHUNKS: bool = Field(
            default=True,
            description="Log raw response chunks in dev mode"
        )
        LOG_PARSED_CHUNKS: bool = Field(
            default=True,
            description="Log parsed response chunks in dev mode"
        )
        LOG_EVENTS: bool = Field(
            default=True,
            description="Log event emitter calls in dev mode"
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
        self.http = urllib3.PoolManager(
            cert_reqs="CERT_NONE",
            headers={
                "X-BARE-PASSWORD": f"password {self.valves.LETTA_PASSWORD}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
        )
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

    def _dev_print(self, message: str, level: str = "INFO"):
        """Print development messages if dev mode is enabled"""
        if not self.valves.DEV_MODE:
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {message}")

    async def _dev_event(self, event_type: str, data: Any, event_emitter: Callable = None):
        """Handle development events and logging"""
        if not self.valves.DEV_MODE:
            return

        if self.valves.LOG_EVENTS:
            self._dev_print(
                f"Event: {event_type}\nData: {json.dumps(data, indent=2)}", 
                "EVENT"
            )
            
        if event_emitter:
            await event_emitter({
                "type": event_type,
                "data": data
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
                    }
                },
            }
        ]

    async def pipe(
        self, 
        body: dict, 
        __user__: dict, 
        __request__: Request,
        __event_emitter__: Callable[[dict], Awaitable[None]] = None
    ) -> Union[str, Iterator[str]]:
        """Main processing pipeline with tool support and event emitters"""
        try:
            # Get user valves
            user_valves = __user__.get("valves", self.UserValves())
            
            # Determine whether to display events
            display_events = (
                self.valves.DISPLAY_EVENTS and 
                user_valves.DISPLAY_EVENTS and 
                __event_emitter__ is not None
            )

            # Handle tool execution via Open WebUI
            if body.get("tools") and self.valves.ENABLE_TOOLS:
                user = Users.get_user_by_id(__user__["id"])
                return await generate_chat_completion(__request__, body, user)

            # Process messages
            messages = self._format_messages(body["messages"])
            last_message = messages[-1] if messages else {}

            # Send initial status event
            if display_events:
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "status": "processing",
                        "description": "Processing request...",
                        "done": False
                    }
                })

            # Prepare payload
            payload = {
                "messages": [last_message],
                "stream_steps": True,
                "stream_tokens": True,
            }

            # Construct URL
            url = f"{self.valves.LETTA_BASE_URL}/v1/agents/{self.valves.LETTA_AGENT_ID}/messages/stream"
            if self.valves.DEV_MODE:
                self._dev_print(f"Constructed URL: {url}", "DEBUG")
                parsed = urllib3.util.parse_url(url)
                self._dev_print(f"Parsed URL: {parsed}", "DEBUG")

            return self._handle_streaming(
                url=url,
                payload=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "X-BARE-PASSWORD": f"password {self.valves.LETTA_PASSWORD}",
                },
                display_events=display_events,
                event_emitter=__event_emitter__,
                user_valves=user_valves
            )

        except Exception as e:
            if display_events:
                await __event_emitter__({
                    "type": "error",
                    "data": {
                        "error": str(e),
                        "type": type(e).__name__
                    }
                })
            return f"Letta Error: {str(e)}"

    def _format_messages(self, messages: list) -> list:
        """Convert Open WebUI format to Letta format"""
        formatted = []
        for msg in messages:
            formatted_msg = {
                "role": "system" if msg["role"] == "system" else "user",
                "content": msg["content"],
            }
            formatted.append(formatted_msg)
        return formatted

    def _handle_streaming(
        self, 
        url: str, 
        payload: dict, 
        headers: dict,
        display_events: bool = False,
        event_emitter: Callable = None,
        user_valves: UserValves = None
    ) -> Generator:
        """Handle streaming responses with event emitters and development logging"""

        async def generator():
            response = None
            try:
                # Development logging: Request details
                if self.valves.DEV_MODE:
                    self._dev_print(f"Request URL: {url}", "DEBUG")
                    self._dev_print(f"Base URL: {self.valves.LETTA_BASE_URL}", "DEBUG")
                    self._dev_print(f"Agent ID: {self.valves.LETTA_AGENT_ID}", "DEBUG")
                    self._dev_print(f"Request Headers: {json.dumps(headers, indent=2)}", "DEBUG")
                    self._dev_print(f"Request Payload: {json.dumps(payload, indent=2)}", "DEBUG")

                # Send request
                response = self._send_request(
                    "POST",
                    url,
                    body=json.dumps(payload),
                    preload_content=False,
                    headers=headers,
                )

                # Development logging: Response status
                if self.valves.DEV_MODE:
                    self._dev_print(f"Response Status: {response.status}", "DEBUG")
                    self._dev_print(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}", "DEBUG")

                # Process streaming response
                for chunk in response.stream():
                    decoded_chunk = chunk.decode("utf-8")
                    
                    # Development logging: Raw chunk
                    if self.valves.DEV_MODE and self.valves.LOG_RAW_CHUNKS:
                        self._dev_print(f"Raw Chunk:\n{decoded_chunk}", "CHUNK")
                        self._log_response("raw_chunk", decoded_chunk)

                    chunks = decoded_chunk.split("\n\n")
                    for chunk in chunks:
                        if not chunk.startswith("data: "):
                            continue

                        # Handle [DONE] marker
                        if chunk == "data: [DONE]":
                            if self.valves.DEV_MODE:
                                self._dev_print("Received [DONE] marker", "DEBUG")
                                self._log_response("done_marker", "[DONE]")
                            continue

                        try:
                            chunk_data = json.loads(chunk[6:])
                            
                            # Development logging: Parsed chunk
                            if self.valves.DEV_MODE and self.valves.LOG_PARSED_CHUNKS:
                                self._dev_print(
                                    f"Parsed Chunk:\n{json.dumps(chunk_data, indent=2)}", 
                                    "PARSED"
                                )
                                self._log_response("parsed_chunk", chunk_data)

                            message_type = chunk_data.get("message_type")

                            if message_type == "assistant_message":
                                content = chunk_data.get("content", "")
                                if content:
                                    if self.valves.DEV_MODE:
                                        self._log_response("assistant_message", content)
                                    yield content + "\n"
                                    
                            elif message_type == "usage_statistics" and user_valves.SHOW_USAGE_STATS:
                                if display_events:
                                    if self.valves.DEV_MODE:
                                        self._log_response("usage_stats", chunk_data)
                                    await self._dev_event("usage", chunk_data, event_emitter)
                                    
                            elif message_type == "reasoning_message" and user_valves.SHOW_REASONING:
                                if display_events:
                                    reasoning_data = {
                                        "step": chunk_data.get("step", "unknown"),
                                        "content": chunk_data.get("content", "")
                                    }
                                    if self.valves.DEV_MODE:
                                        self._log_response("reasoning", reasoning_data)
                                    await self._dev_event("reasoning", reasoning_data, event_emitter)

                        except json.JSONDecodeError as e:
                            if self.valves.DEV_MODE:
                                self._dev_print(f"JSON Parse Error: {str(e)}", "ERROR")
                                self._log_response("parse_error", {
                                    "error": str(e),
                                    "chunk": chunk
                                })
                            if display_events:
                                await self._dev_event(
                                    "warning",
                                    {
                                        "message": "Failed to parse chunk",
                                        "chunk": chunk,
                                        "error": str(e)
                                    },
                                    event_emitter
                                )

                # Send final status event
                if display_events:
                    await self._dev_event(
                        "status",
                        None,  # This will clear the status
                        event_emitter
                    )

            except Exception as e:
                error_data = {
                    "error": str(e),
                    "type": type(e).__name__
                }
                if self.valves.DEV_MODE:
                    self._dev_print(f"Streaming Error: {str(e)}", "ERROR")
                    self._log_response("error", error_data)
                if display_events:
                    await self._dev_event("error", error_data, event_emitter)
                yield json.dumps({
                    "type": "chat:error",
                    "data": {"message": f"Error during streaming: {str(e)}"}
                })
            finally:
                if response is not None:
                    response.release_conn()

        return generator()

    def _parse_response(self, response) -> str:
        """Parse Letta API response"""
        if response.status != 200:
            return f"Error: {response.status} - {response.data.decode()}"

        try:
            data = json.loads(response.data.decode())
            return data["choices"][0]["message"]["content"]
        except KeyError:
            return "Error: Invalid response format from Letta"

    async def on_valves_updated(self):
        """Update HTTP client when valves change"""
        self.http = urllib3.PoolManager(
            cert_reqs="CERT_NONE",
            headers={
                "X-BARE-PASSWORD": f"password {self.valves.LETTA_PASSWORD}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
        )