# utils/ai_client.py

import os
import asyncio
import concurrent.futures
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4o-mini"

# Sync client — for planner, extractor (called from sync context)
_sync_client  = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Async client — for parallel AI calls inside FastAPI
_async_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def ask_ai_async(prompt: str, system: str = "") -> str:
    """
    Async version — use inside FastAPI or asyncio.gather().
    Non-blocking — lets other code run while waiting for AI.
    """
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        else:
            messages.append({"role": "system", "content": "You are a helpful research assistant."})
        messages.append({"role": "user", "content": prompt})

        response = await _async_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"[AI Error async] {e}")
        return "Error: Could not get AI response."


def ask_ai(prompt: str, system: str = "") -> str:
    """
    Sync version — kept for backward compatibility.
    Used by planner.py and extractor.py.
    Safely handles both sync and async contexts.
    """
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        else:
            messages.append({"role": "system", "content": "You are a helpful research assistant."})
        messages.append({"role": "user", "content": prompt})

        response = _sync_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=2000,
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"[AI Error] {e}")
        return "Error: Could not get AI response."