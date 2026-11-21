"""Direct OpenAI-compatible HTTP client (the main road).

Why not SDK ``Agent.run``: one SDK turn fires several consecutive model
calls (main decide + internal classification rounds). On the Pollinations
free tier (``1 reply every 45 seconds per IP``, enforced as HTTP 402) the
first call consumes the quota and the rest fail immediately; the SDK's
built-in retry waits 300 ms / 600 ms (hardcoded ``backoff_ms=300``, no
``Retry-After`` handling — see docs/WHAT_WE_LEARNED.md), so a native turn
cannot survive the window. Verified 3/3 failures in SPIKE.md §4.

This client therefore makes exactly one model call per step, paces calls
at least ``min_interval_sec`` apart (default 45 s), and parses the answer
through two channels: ``tool_calls`` first, plain-text JSON second — both
validated by the same Pydantic model.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

import httpx
from pydantic import BaseModel, ValidationError

from .config import fix_proxy_env

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

    Strips a leading ``agent_id: ...`` prefix (the SDK adds one to replies;
    a free model may imitate it) and then finds the first ``{`` whose
    braces balance. Raises ValueError if nothing parses.
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
                return cleaned[start : i + 1]
    raise ValueError("unbalanced JSON object in model output")


def parse_typed(text: str, model_cls: type[BaseModel]) -> BaseModel:
    """Parse text (possibly with surrounding prose) into a Pydantic model."""
    payload = json.loads(extract_json_object(text))
    return model_cls.model_validate(payload)


def parse_tool_calls(tool_calls: list[dict[str, Any]], model_cls: type[BaseModel]) -> BaseModel:
    """Parse the first function tool call's arguments into a Pydantic model."""
    if not tool_calls:
        raise VerdictParseError("no tool calls to parse")
    fn = tool_calls[0].get("function") or {}
    args = fn.get("arguments") or ""
    if isinstance(args, dict):
        return model_cls.model_validate(args)
    return model_cls.model_validate(json.loads(args))


class DirectClient:
    """One-call-per-step OpenAI-compatible client with pacing + 402 handling.

    ``sleep`` and ``clock`` are injectable so tests can run without waiting
    45 real seconds. ``transport`` accepts an httpx transport (tests use
    MockTransport; production uses the default).
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        min_interval_sec: float = 45.0,
        timeout_sec: float = 120.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
        reasoning_effort: str | None = "low",
    ):
        fix_proxy_env()
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.min_interval_sec = max(0.0, min_interval_sec)
        self.timeout_sec = timeout_sec
        self.reasoning_effort = reasoning_effort
        self._sleep = sleep or time.sleep
        self._clock = clock or time.monotonic
        self._last_call_end: float | None = None
        self.calls_made = 0
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_sec, connect=10.0),
            transport=transport,
        )

    # -- pacing ---------------------------------------------------------
    def wait_pacing(self) -> float:
        """Block until ``min_interval_sec`` elapsed since the last call ended.

        Public wrapper for :meth:`_wait_pacing`, for callers that make
        model calls outside this client (the SDK turn in
        :mod:`issue_triage.triage`): an SDK turn fires several consecutive
        provider calls, so its first call must start in a fresh free-tier
        window, not on top of the classify call that just ran.
        """
        return self._wait_pacing()

    def _wait_pacing(self) -> float:
        """Sleep until ``min_interval_sec`` elapsed since the last call ended."""
        if self._last_call_end is None or self.min_interval_sec <= 0:
            return 0.0
        wait = self.min_interval_sec - (self._clock() - self._last_call_end)
        if wait > 0:
            self._sleep(wait)
            return wait
        return 0.0

    @staticmethod
    def _retry_after_seconds(payload_text: str, headers: httpx.Headers) -> int | None:
        header = headers.get("retry-after")
        if header and header.strip().isdigit():
            return int(header.strip())
        match = RATE_LIMIT_RETRY_AFTER_RE.search(payload_text or "")
        if match:
            return int(match.group(1))
        return None

    # -- core call ------------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        response_format_json: bool = False,
        temperature: float = 0.0,
    ) -> LLMCallResult:
        """One chat completion. On HTTP 402, waits out the provider's
        ``Retry-After`` (or the pacing interval, whichever is longer) and
        retries once; a second 402 raises :class:`RateLimitedError`."""
        self._wait_pacing()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        # gpt-oss-20b via Pollinations sometimes burns its whole output
        # budget on reasoning and dies with 400 output_token_limit_exceeded
        # before producing an answer; "low" keeps it terse. Omitted when
        # reasoning_effort is None/"" (other providers may reject the field).
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        if tools:
            payload["tools"] = tools
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        started = self._clock()
        try:
            response = self._post(payload)
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"model call timed out after {self.timeout_sec}s: {exc}") from exc
        latency_ms = int((self._clock() - started) * 1000)
        self._last_call_end = self._clock()
        self.calls_made += 1

        if response.status_code == 402:
            retry_after = self._retry_after_seconds(response.text, response.headers)
            wait = max(retry_after or 0, self.min_interval_sec)
            self._sleep(wait)
            # one retry, then give up honestly
            self._wait_pacing()
            started = self._clock()
            response = self._post(payload)
            latency_ms += int((self._clock() - started) * 1000)
            self._last_call_end = self._clock()
            self.calls_made += 1
            if response.status_code == 402:
                retry_after = self._retry_after_seconds(response.text, response.headers)
                raise RateLimitedError(
                    f"provider rate limit (HTTP 402) persists after backoff; "
                    f"body: {response.text[:200]}",
                    retry_after=retry_after,
                )
        if response.status_code >= 400:
            raise RuntimeError(
                f"provider HTTP {response.status_code}: {response.text[:300]}"
            )
        return self._result_from(response, latency_ms)

    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        return self._client.post(
            "/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    @staticmethod
    def _result_from(response: httpx.Response, latency_ms: int) -> LLMCallResult:
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        tool_calls = message.get("tool_calls") or []
        return LLMCallResult(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            usage=data.get("usage") or {},
            latency_ms=latency_ms,
            channel="tool_calls" if tool_calls else "text",
            model=data.get("model") or "",
        )

    # -- typed dual-channel call ----------------------------------------
    def chat_typed(
        self,
        messages: list[dict[str, str]],
        model_cls: type[BaseModel],
        tools: list[dict[str, Any]] | None = None,
        response_format_json: bool = True,
    ) -> tuple[BaseModel, LLMCallResult]:
        """One call, two parse channels: tool_calls first, text JSON second.
        Both go through the same Pydantic model, so an invented enum value
        fails loudly instead of slipping through."""
        result = self.chat(
            messages, tools=tools, response_format_json=response_format_json
        )
        errors: list[str] = []
        if result.tool_calls:
            try:
                return parse_tool_calls(result.tool_calls, model_cls), result
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"tool_calls channel: {exc}")
        if result.content.strip():
            try:
                return parse_typed(result.content, model_cls), result
            except (ValidationError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"text channel: {exc}")
        raise VerdictParseError(
            "no channel produced a valid "
            f"{model_cls.__name__}: {'; '.join(errors) or 'empty response'}",
            raw_text=result.content,
        )

    # -- streaming ------------------------------------------------------
    def chat_stream(
        self, messages: list[dict[str, str]]
    ) -> Iterator[str]:
        """Stream one completion, yielding content deltas. Used by the probe
        suite to verify streaming telemetry; pacing rules apply as usual."""
        self._wait_pacing()
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "stream": True,
        }
        started = self._clock()
        chunks: list[str] = []
        try:
            with self._client.stream(
                "POST",
                "/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            ) as response:
                if response.status_code == 402:
                    body = response.read().decode("utf-8", "replace")
                    retry_after = self._retry_after_seconds(body, response.headers)
                    raise RateLimitedError(
                        f"provider rate limit (HTTP 402) on stream; body: {body[:200]}",
                        retry_after=retry_after,
                    )
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0]["delta"]
                    except (ValueError, KeyError, IndexError):
                        continue
                    text = delta.get("content") or ""
                    if text:
                        chunks.append(text)
                        yield text
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"stream timed out after {self.timeout_sec}s: {exc}") from exc
        finally:
            self._last_call_end = self._clock()
            self.calls_made += 1
        _ = started, chunks

    def close(self) -> None:
        self._client.close()
