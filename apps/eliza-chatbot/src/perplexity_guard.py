import os
import logging
import requests
from typing import Optional

from . import config

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(getattr(config, "USE_PERPLEXITY_GUARD", False) and getattr(config, "PERPLEXITY_API_KEY", None))


def try_answer(user_text: str) -> Optional[str]:
    """
    Query Perplexity API for a concise, factual answer to the user's question.
    Returns a short string, or None if disabled/unavailable/errors.
    """
    if not user_text or not is_enabled():
        return None

    api_key = config.PERPLEXITY_API_KEY  # type: ignore[attr-defined]
    model = (getattr(config, "PERPLEXITY_MODEL", None) or "sonar").strip()

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # Constrain the model to produce a short factual line only
    system_prompt = (
        "You are a strict factual answerer."
        " Answer concisely (<= 1 short sentence, ~15 words)."
        " Output only the answer text with no preamble, steps, or follow-up questions."
        " If unsure, reply with: I'm not sure."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.0,
        "top_p": 1.0,
        "stream": False,
        "max_tokens": 64,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code < 200 or resp.status_code >= 300:
            logger.warning("[PPLX] HTTP %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        # Perplexity Chat Completions format: choices[0].message.content
        content = None
        try:
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
        except Exception:
            content = None
        if not content:
            # Fallback for possible alt schema
            content = data.get("choices", [{}])[0].get("text")
        if not content:
            return None
        text = str(content).strip()
        # Keep it to one short line
        # Remove enclosing quotes if present
        if (text.startswith("\"") and text.endswith("\"")) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()
        # Hard trim to ~150 chars
        if len(text) > 150:
            text = text[:150].rstrip() + "…"
        return text
    except Exception as e:
        logger.warning("[PPLX] request failed: %s", e)
        return None
