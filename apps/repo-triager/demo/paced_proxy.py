#!/usr/bin/env python3
"""A pacing proxy for a rate-limited OpenAI-compatible endpoint.

``openminion 0.1.24`` retries a failed model call twice with a 300 ms backoff. A free
endpoint that answers *one request per 45 s per IP* therefore fails a multi-call turn
(a triage turn is 12 calls) no matter how patient the agent is — see
``findings/real-model-attempt.log``. This proxy sits between the SDK and such an endpoint
and does what the runtime cannot: it spaces the calls out and honours the provider's own
``Retry after Ns`` answer.

It is a demo aid for a *throttled free* provider. A real key (Cortensor Portal, Groq,
Cerebras, OpenAI, Ollama) needs none of this: point ``OPENAI_COMPATIBLE_BASE_URL``
straight at the provider.

    UPSTREAM_BASE_URL=https://text.pollinations.ai/openai MIN_INTERVAL_SEC=45 \
        python demo/paced_proxy.py            # listens on 127.0.0.1:8787/v1

    OPENAI_COMPATIBLE_BASE_URL=http://127.0.0.1:8787/v1 \
    OPENAI_COMPATIBLE_API_KEY=local REPO_TRIAGER_MODEL=openai-fast \
        repo-triager --provider configured triage --issue 859 --apply auto
"""

from __future__ import annotations

import http.server
import json
import os
import re
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.request

UPSTREAM = os.environ.get("UPSTREAM_BASE_URL", "https://text.pollinations.ai/openai").rstrip("/")
MIN_INTERVAL = float(os.environ.get("MIN_INTERVAL_SEC", "45"))
MAX_RETRIES = int(os.environ.get("UPSTREAM_MAX_RETRIES", "8"))
PORT = int(os.environ.get("PORT", "8787"))
TIMEOUT = float(os.environ.get("UPSTREAM_TIMEOUT_SEC", "180"))

_LOCK = threading.Lock()
_LAST = [0.0]
_CALLS = [0]


def _pace() -> None:
    wait = MIN_INTERVAL - (time.time() - _LAST[0])
    if wait > 0:
        time.sleep(wait)


def _retry_after(body: bytes, fallback: float) -> float:
    m = re.search(rb"[Rr]etry after (\d+)\s*s", body or b"")
    if m:
        return float(m.group(1)) + 1.0
    return fallback


def forward(path: str, body: bytes | None, headers: dict[str, str]) -> tuple[int, bytes, str]:
    url = UPSTREAM + path
    delay = max(MIN_INTERVAL, 5.0)
    for attempt in range(1, MAX_RETRIES + 1):
        _pace()
        req = urllib.request.Request(url, data=body, method="POST" if body else "GET")
        for k, v in headers.items():
            if k.lower() in ("host", "content-length", "accept-encoding"):
                continue
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                _LAST[0] = time.time()
                _CALLS[0] += 1
                return resp.status, resp.read(), resp.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            _LAST[0] = time.time()
            if exc.code in (402, 429) and attempt < MAX_RETRIES:
                wait = _retry_after(payload, delay)
                print(f"  upstream {exc.code}; waiting {wait:.0f}s (attempt {attempt})",
                      file=sys.stderr, flush=True)
                time.sleep(wait)
                delay = min(delay * 1.5, 90.0)
                continue
            return exc.code, payload, exc.headers.get("Content-Type", "application/json")
        except Exception as exc:  # network hiccup
            _LAST[0] = time.time()
            if attempt < MAX_RETRIES:
                print(f"  upstream error {exc!r}; retrying", file=sys.stderr, flush=True)
                time.sleep(5)
                continue
            raise
    return 599, b'{"error":"proxy gave up"}', "application/json"


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # quieter
        if os.environ.get("PROXY_VERBOSE"):
            super().log_message(fmt, *args)

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _relay(self, body: bytes | None) -> None:
        path = self.path
        if path.startswith("/v1"):
            path = path[3:]
        headers = {k: v for k, v in self.headers.items()}
        status, payload, ctype = forward(path, body, headers)
        self.send_response(status)
        self.send_header("Content-Type", ctype or "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        print(f"  [{_CALLS[0]:2d}] {self.command} {path} -> {status} ({len(payload)} B)",
              file=sys.stderr, flush=True)

    def do_POST(self) -> None:
        self._relay(self._body())

    def do_GET(self) -> None:
        self._relay(None)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main() -> int:
    print(f"pacing proxy: 127.0.0.1:{PORT}/v1 -> {UPSTREAM} "
          f"(min {MIN_INTERVAL:.0f}s between calls)", file=sys.stderr, flush=True)
    Server(("127.0.0.1", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
