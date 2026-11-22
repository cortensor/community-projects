"""LOCAL TEST ONLY: a scripted OpenAI-compatible server so the OpenMinion wiring can be tested without a real model.
It is NOT a model. Output from runs against it must never be shown as a real model run."""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

LOG = []


def tool_call(name, i):
    return {"id": f"call_{i}", "type": "function", "function": {"name": name, "arguments": "{}"}}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send({"object": "list", "data": [{"id": "mock-model", "object": "model"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        msgs = body.get("messages", [])
        tools = [t["function"]["name"] for t in body.get("tools", []) or []]
        called = [m.get("name") or m.get("tool_call_id") for m in msgs if m.get("role") == "tool"]
        n = len(called)
        sys.stderr.write(f"[mock] tools={tools} tool_results={n} stream={body.get('stream')}\n")
        order = ["radar_new_releases", "radar_new_issues", "radar_save_checkpoint"]
        if n < 3 and all(o in tools for o in order):
            msg = {"role": "assistant", "content": None, "tool_calls": [tool_call(order[n], n)]}
            finish = "tool_calls"
        else:
            content = json.dumps({"repo": "x", "headline": "MOCK headline", "releases": [], "issues_to_watch": [], "actions": ["mock action"]})
            msg = {"role": "assistant", "content": content}
            finish = "stop"
        self._send({"id": "mock", "object": "chat.completion", "model": "mock-model",
                    "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8765), H).serve_forever()
