# AgentOS LLM Service

Python subprocess that handles LLM API calls for the kernel.

## Overview

The kernel spawns this as a subprocess and communicates via stdin/stdout JSON.

```
Kernel (C++) ──JSON stdin──► llm_service.py ──HTTPS──► Gemini API
             ◄──JSON stdout──
```

## Why a Subprocess?

- **SDK support**: Use official `google-genai` Python SDK
- **Multimodal**: Easy handling of images + text
- **Isolation**: LLM failures don't crash the kernel
- **Flexibility**: Easy to swap LLM providers

## Installation

```bash
pip install google-genai
```

## Configuration

Set API key via environment variable or `.env` file:

```bash
export GEMINI_API_KEY="your-key"
# or
echo "GEMINI_API_KEY=your-key" >> .env
```

## Protocol

### Request (JSON on stdin)

```json
{
  "prompt": "What is 2+2?",
  "image": {
    "data": "<base64>",
    "mime_type": "image/jpeg"
  },
  "system_instruction": "You are helpful",
  "thinking_level": "medium",
  "temperature": 0.7,
  "model": "gemini-2.0-flash"
}
```

All fields except `prompt` are optional.

### Response (JSON on stdout)

```json
{
  "success": true,
  "content": "2+2 equals 4",
  "tokens": 15,
  "error": null
}
```

## Files

| File | Description |
|------|-------------|
| `llm_service.py` | Main service - reads JSON, calls Gemini, returns result |
| `requirements.txt` | Python dependencies |

## Supported Models

- `gemini-2.0-flash` (default)
- `gemini-2.0-flash-thinking` (with thinking_level)
- Other Gemini models

## Testing Standalone

```bash
echo '{"prompt": "Hello"}' | GEMINI_API_KEY="your-key" python3 llm_service.py
```
