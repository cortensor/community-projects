"""Direct OpenAI-compatible HTTP client (the main road for model calls).

Why not SDK ``Agent.run`` as the main road: one SDK turn fires several
consecutive model calls (main decide + internal classification rounds).
On the Pollinations free tier (``1 reply every 45 seconds per IP``,
enforced as HTTP 402) the first call consumes the quota and the rest
fail immediately; the SDK's built-in retry waits ~300 ms and does not
honour ``Retry-After``, so a native turn cannot survive the window
(verified 3/3 failures in the sibling project's SPIKE.md §4).

This client therefore makes exactly one model call per step, paces
calls at least ``min_interval_sec`` apart (default 45 s), and parses
the answer through two channels — ``tool_calls`` first, plain-text
JSON second — both validated by the same Pydantic model.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx
from pydantic import BaseModel, ValidationError

from .config import ProviderSettings, fix_proxy_env

RATE_LIMIT_RETRY_AFTER_RE = re.compile(r"retry after (\d+)s", re.IGNORECASE)
_AGENT_ID_PREFIX_RE = re.compile(r"^\s*agent_id\s*:\s*", re.IGNORECASE | re.MULTILINE)


class RateLimitedError(RuntimeError):
    """Raised when the provider still answers 402 after the backoff retry."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class VerdictParseError(RuntimeError):
    """No channel produced a valid typed object."""

    def __init__(self, message: str, raw_text: str = ""):
        super().__init__(message)
        self.raw_text = raw_text


@dataclass
class LLMCallResult:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    channel: str = "text"  # "tool_calls" or "text"
    model: str = ""


def extract_json_object(text: str) -> str:
    """Pull the first balanced JSON object out of free text.

    Strips a leading ``agent_id: ...`` prefix (the SDK adds one to
    replies; a free model may imitate it) and then finds the first ``{``
    whose braces balance. Raises ValueError if nothing parses.
    """
    cleaned = _AGENT_ID_PREFIX_RE.sub("", text or "").strip()
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("no JSON object in model output")
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start:i + 1]
    raise ValueError("unbalanced JSON object in model output")


def parse_typed(text: str, model_cls: type[BaseModel]) -> BaseModel:
    payload = json.loads(extract_json_object(text))
    return model_cls.model_validate(payload)


def parse_tool_calls(tool_calls: list[dict[str, Any]],
                     model_cls: type[BaseModel]) -> BaseModel:
    if not tool_calls:
        raise VerdictParseError("no tool calls to parse")
    fn = tool_calls[0].get("function") or {}
    args = fn.get("arguments") or ""
    if isinstance(args, dict):
        return model_cls.model_validate(args)
    return model_cls.model_validate(json.loads(args))


class DirectClient:
    """One-call-per-step OpenAI-compatible client with pacing + 402 handling.

    ``sleep`` and ``clock`` are injectable so tests run without waiting
    45 real seconds. ``transport`` accepts an httpx transport (tests use
    MockTransport; production uses the default).
    """

    def __init__(self, provider: ProviderSettings,
                 min_interval_sec: float = 45.0,
                 timeout_sec: float = 60.0,
                 transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] | None = None,
                 clock: Callable[[], float] | None = None):
        fix_proxy_env()
        self.provider = provider
        self.min_interval_sec = min_interval_sec
        self.timeout_sec = timeout_sec
        self._transport = transport
        self._sleep = sleep or time.sleep
        self._clock = clock or time.time
        self._last_call_at: float | None = None
        self.calls_made = 0
        self.tokens_used = 0

    def _pace(self) -> None:
        if self._last_call_at is None or self.min_interval_sec <= 0:
            return
        wait = self.min_interval_sec - (self._clock() - self._last_call_at)
        if wait > 0:
            self._sleep(wait)

    def _retry_after(self, text: str) -> int | None:
        m = RATE_LIMIT_RETRY_AFTER_RE.search(text or "")
        return int(m.group(1)) if m else None

    def complete(self, messages: list[dict[str, str]],
                 tools: list[dict[str, Any]] | None = None,
                 response_format_json: bool = True) -> LLMCallResult:
        """One chat completion. Retries once after a 402, honouring Retry-After."""
        self._pace()
        url = self.provider.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": self.provider.model,
            "messages": messages,
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        last_error: Exception | None = None
        for attempt in range(2):
            started = self._clock()
            try:
                with httpx.Client(transport=self._transport,
                                  timeout=self.timeout_sec) as client:
                    resp = client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.provider.api_key}"},
                        json=payload,
                    )
            except httpx.HTTPError as exc:
                raise RuntimeError(f"model request failed: {exc}") from exc
            latency_ms = int((self._clock() - started) * 1000)
            self._last_call_at = self._clock()
            self.calls_made += 1
            if resp.status_code == 402:
                retry_after = self._retry_after(resp.text) or 45
                last_error = RateLimitedError(
                    f"HTTP 402: {resp.text[:200]}", retry_after=retry_after)
                if attempt == 0:
                    self._sleep(retry_after + 2)
                    continue
                raise last_error
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"model request HTTP {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            usage = data.get("usage") or {}
            self.tokens_used += int(usage.get("total_tokens") or 0)
            choice = (data.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            return LLMCallResult(
                content=message.get("content") or "",
                tool_calls=message.get("tool_calls") or [],
                usage=usage,
                latency_ms=latency_ms,
                channel="tool_calls" if message.get("tool_calls") else "text",
                model=data.get("model") or "",
            )
        raise last_error or RuntimeError("model request failed")

    def classify(self, model_cls: type[BaseModel], messages: list[dict[str, str]],
                 tools: list[dict[str, Any]] | None = None) -> BaseModel:
        """Complete once and parse the answer into ``model_cls``.

        Tries the tool_calls channel first, then plain-text JSON.
        A Pydantic ValidationError from a wrong-shaped reply is a
        VerdictParseError (the caller decides whether to retry or fall
        back to the rule screen — never to invent a label).
        """
        result = self.complete(messages, tools=tools)
        if result.tool_calls:
            try:
                return parse_tool_calls(result.tool_calls, model_cls)
            except (ValueError, ValidationError, VerdictParseError):
                pass
        try:
            return parse_typed(result.content, model_cls)
        except (ValueError, ValidationError) as exc:
            raise VerdictParseError(
                f"could not parse model output into {model_cls.__name__}: {exc}",
                raw_text=result.content) from exc
