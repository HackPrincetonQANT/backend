# database/api/do_llm.py

import os
from typing import Optional

try:
    import requests  # type: ignore
except ImportError:
    requests = None  # we'll handle this gracefully


DO_API_KEY = os.getenv("DO_API_KEY")
# You can change this to the exact model slug you enable on DigitalOcean
DO_LLM_MODEL = os.getenv("DO_LLM_MODEL", "gpt-4o-mini")


def call_do_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Call DigitalOcean's hosted LLM via their OpenAI-compatible API.

    If DO_API_KEY or requests is missing, we return a placeholder message
    so the API still works without crashing.
    """
    # If no key or no requests, return a safe stub response
    if not DO_API_KEY or requests is None:
        return (
            "Hi! Your AI coach is not fully configured yet on the server. "
            "Ask your teammate to set DO_API_KEY and install 'requests' in the backend "
            "so I can generate smarter, personalized coaching messages."
        )

    url = "https://api.digitalocean.com/v2/ai/openai/chat/completions"

    headers = {
        "Authorization": f"Bearer {DO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DO_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 300,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # OpenAI-style response structure
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        # Don't crash the app; just return a fallback message
        return (
            "Your AI coach ran into a problem talking to the DigitalOcean LLM "
            f"(error: {e!r}). Please try again later or check the server logs."
        )
