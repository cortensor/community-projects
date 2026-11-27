"""Debug helper: run only the judge on freshly collected facts, with provider pacing and call logging."""
import json, sys
sys.path.insert(0, ".")
import gate
from openminion import Agent

for n in gate.READ_ONLY:
    gate._collect(n, sys.argv[1])
r = gate.judge_facts(sys.argv[1], str(gate.ROOT / ".om/home/.openminion/agents.json"), f"judge-only-{sys.argv[1]}")
print(r.output.model_dump_json(indent=1)[:3000])
