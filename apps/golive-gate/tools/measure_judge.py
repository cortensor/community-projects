"""Debug helper: size of the judge's first provider request (no model call made)."""
import json, sys
sys.path.insert(0, ".")
import openminion.modules.llm.providers.openai.adapter as ad
import gate
from openminion import Agent

def fake(**kw):
    body = json.dumps(kw["payload"])
    roles = [(m["role"], len(str(m.get("content")))) for m in kw["payload"]["messages"]]
    print(f"[judge request] chars={len(body)} messages={roles} tools={[t['function']['name'] for t in kw['payload'].get('tools', [])]}")
    raise SystemExit(0)

ad._http_json_post = fake
for n in gate.READ_ONLY:
    gate._collect(n, sys.argv[1])
with Agent(instructions=gate.INSTRUCTIONS, output_type=gate.GoLiveReport, config_path=str(gate.ROOT / ".om/home/.openminion/agents.json")) as j:
    j.run(json.dumps({"site": sys.argv[1], "facts": gate._SITE}))
