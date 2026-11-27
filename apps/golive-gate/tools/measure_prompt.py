"""Debug helper: print the size of every provider request OpenMinion sends (no model call made)."""
import json, sys
sys.path.insert(0, ".")
import openminion.modules.llm.providers.openai.adapter as ad

def fake(**kw):
    p = kw["payload"]
    tools = p.get("tools") or []
    body = json.dumps(p)
    print(f"[request] chars={len(body)} ~tokens={len(body)//4} messages={len(p.get("messages", []))} tools={len(tools)} max={p.get("max_tokens") or p.get("max_completion_tokens")} keys={sorted(p)}")
    print("  tool names:", [t.get("function", {}).get("name") for t in tools][:60])
    open("/tmp/om-payload.json","w").write(body); sys.exit(0)

ad._http_json_post = fake
import gate
gate.run(sys.argv[1], "yes", str(gate.ROOT / ".om/home/.openminion/agents.json"))
