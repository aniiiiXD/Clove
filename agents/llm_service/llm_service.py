#!/usr/bin/env python3
"""LLM Service - google-genai SDK wrapper for AgentOS kernel

This subprocess receives JSON requests on stdin and outputs JSON responses on stdout.
It uses the official google-genai SDK for accessing Gemini models.
"""

import sys
import json
import base64
import os
from pathlib import Path

# Load .env file before anything else
def load_dotenv():
    """Load environment variables from .env file"""
    # Search for .env in multiple locations
    search_paths = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent.parent / ".env",  # AGENTOS/.env
        Path.home() / ".env",
    ]

    for env_path in search_paths:
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, value = line.partition('=')
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and value and key not in os.environ:
                            os.environ[key] = value
            break

# Load .env at module import time
load_dotenv()

from google import genai
from google.genai import types

# Initialize client (uses GOOGLE_API_KEY or GEMINI_API_KEY from environment)
def get_client():
    """Get configured genai client"""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("No API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY in environment or .env file.")
    return genai.Client(api_key=api_key)


def handle_request(client, request: dict) -> dict:
    """Process a single LLM request"""
    try:
        model = request.get("model", "gemini-2.0-flash")
        prompt = request.get("prompt", "")

        # Build contents (multimodal support)
        contents = []
        if prompt:
            contents.append(prompt)

        # Handle image if present (base64 encoded)
        if "image" in request:
            image_data = base64.b64decode(request["image"]["data"])
            mime_type = request["image"].get("mime_type", "image/jpeg")
            contents.append(types.Part.from_bytes(data=image_data, mime_type=mime_type))

        # Build generation config
        gen_config_args = {}

        if "temperature" in request:
            gen_config_args["temperature"] = request["temperature"]

        if "max_tokens" in request:
            gen_config_args["max_output_tokens"] = request["max_tokens"]

        # Build thinking config if specified
        thinking_config = None
        if "thinking_level" in request:
            level = request["thinking_level"].upper()
            thinking_config = types.ThinkingConfig(
                thinking_budget={"LOW": 1024, "MEDIUM": 4096, "HIGH": 8192}.get(level, 4096)
            )

        # Build final config
        config_args = {}
        if gen_config_args:
            config_args.update(gen_config_args)

        if "system_instruction" in request:
            config_args["system_instruction"] = request["system_instruction"]

        if thinking_config:
            config_args["thinking_config"] = thinking_config

        # Create config object if we have any config
        config = types.GenerateContentConfig(**config_args) if config_args else None

        # Call Gemini
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )

        # Extract token count
        tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            tokens = getattr(response.usage_metadata, 'total_token_count', 0)

        return {
            "success": True,
            "content": response.text,
            "tokens": tokens
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content": ""
        }


def main():
    """Main loop - read JSON requests from stdin, write responses to stdout"""
    # Initialize client once at startup
    try:
        client = get_client()
    except Exception as e:
        # If we can't initialize, report error for each request
        client = None
        init_error = str(e)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            response = {"success": False, "error": f"Invalid JSON: {e}", "content": ""}
            print(json.dumps(response), flush=True)
            continue

        if client is None:
            response = {"success": False, "error": init_error, "content": ""}
        else:
            response = handle_request(client, request)

        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
