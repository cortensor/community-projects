"""Pollinations free OpenAI-compatible endpoint probe. No key. Tiny prompts."""
import json, time, httpx

BASE = "https://text.pollinations.ai/openai"
LOG = []

def log(name, **kw):
    LOG.append({"test": name, **kw})
    print(json.dumps({"test": name, **kw}, ensure_ascii=False)[:1500])

# 0. GET /models
t0 = time.time()
try:
    r = httpx.get(f"{BASE}/models", timeout=30)
    body = r.json() if "json" in r.headers.get("content-type","") else r.text[:500]
    models = [m.get("id") for m in body.get("data", [])] if isinstance(body, dict) else body
    log("GET /models", status=r.status_code, seconds=round(time.time()-t0,2), models=models)
except Exception as e:
    log("GET /models", status="EXC", seconds=round(time.time()-t0,2), error=repr(e))
    models = []

MODEL = "openai"  # Pollinations documented default free model
print("MODEL chosen:", MODEL)

def chat(payload, name):
    last = None
    for attempt in (1, 2, 3):
        t0 = time.time()
        try:
            r = httpx.post(f"{BASE}/v1/chat/completions", json=payload, timeout=120)
            dt = round(time.time()-t0, 2)
            try:
                b = r.json()
            except Exception:
                b = {"_raw": r.text[:800]}
            if r.status_code == 200:
                ch = (b.get("choices") or [{}])[0]
                msg = ch.get("message") or {}
                log(name, attempt=attempt, status=200, seconds=dt,
                    model=b.get("model"), finish_reason=ch.get("finish_reason"),
                    usage=b.get("usage"),
                    content=(msg.get("content") or "")[:400],
                    tool_calls=msg.get("tool_calls"))
                return b
            last = (r.status_code, dt, json.dumps(b, ensure_ascii=False)[:800])
            log(name, attempt=attempt, status=r.status_code, seconds=dt,
                error_body=json.dumps(b, ensure_ascii=False)[:800])
            if r.status_code in (400, 401, 403, 404):
                break
        except Exception as e:
            dt = round(time.time()-t0, 2)
            last = ("EXC", dt, repr(e))
            log(name, attempt=attempt, status="EXC", seconds=dt, error=repr(e))
    return {"_failed": last}

# (a) plain JSON output
chat({"model": MODEL,
      "messages": [{"role": "user",
                    "content": "Reply with ONLY this JSON object, no other text: {\"label\": \"bug\", \"confidence\": 0.9}"}]},
     "a_plain_json")

# (b) tool calling
chat({"model": MODEL,
      "messages": [{"role": "user", "content": "What is the label of GitHub issue #12 titled 'login fails on Safari'? Use the lookup_issue tool."}],
      "tools": [{"type": "function", "function": {
          "name": "lookup_issue",
          "description": "Look up a GitHub issue by number.",
          "parameters": {"type": "object",
                         "properties": {"number": {"type": "integer"}},
                         "required": ["number"]}}}]},
     "b_tool_call")

# (c) response_format json_object
chat({"model": MODEL, "response_format": {"type": "json_object"},
      "messages": [{"role": "user",
                    "content": "Return a JSON object with keys label and confidence for the text 'login fails'."}]},
     "c_response_format_json_object")

Path_out = "pollinations_probe_log.json"
open(Path_out, "w").write(json.dumps(LOG, ensure_ascii=False, indent=2))
print("wrote", Path_out)
