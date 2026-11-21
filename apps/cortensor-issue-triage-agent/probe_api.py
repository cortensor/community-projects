"""Offline API probe for openminion 0.1.21 — import + construct only, no model calls."""
import json, sys, tempfile, traceback
from pathlib import Path

ok, fail = [], []

def check(name, fn):
    try:
        r = fn()
        ok.append((name, r))
        print(f"PASS {name}: {r}")
    except Exception as e:
        fail.append((name, repr(e)))
        print(f"FAIL {name}: {type(e).__name__}: {e}")

# 1. lazy top-level exports
def t_lazy():
    import openminion
    names = ["APIRuntime","Agent","AgentOutputValidationError","AgentRunResult",
             "Handoff","MemoryBundle","ProviderError","TurnTimeoutError","subagent","tool"]
    got = {n: getattr(openminion, n).__name__ if hasattr(getattr(openminion, n), "__name__") else type(getattr(openminion, n)).__name__ for n in names}
    return got
check("lazy_exports", t_lazy)

def t_no_create_isolated():
    import openminion
    try:
        openminion.create_isolated_runtime
        return "EXISTS (unexpected)"
    except AttributeError:
        return "absent as expected"
check("create_isolated_runtime_absent", t_no_create_isolated)

# 2. @tool decorator
def t_tool():
    from openminion import tool
    @tool(min_scope="READ_ONLY")
    def lookup_fact(claim: str) -> str:
        """Look up one fact."""
        return f"fact:{claim}"
    @tool(dangerous=True, min_scope="WRITE_SAFE")
    def publish_note(text: str) -> str:
        """Publish a note."""
        return f"published:{text}"
    return (lookup_fact.tool_decl.name, lookup_fact.tool_decl.min_scope,
            lookup_fact.tool_decl.dangerous, publish_note.tool_decl.dangerous,
            publish_note.tool_decl.min_scope, hasattr(lookup_fact, "tool_family_spec"))
check("tool_decorator", t_tool)

# 3. Agent construction (no runtime bootstrap)
def t_agent():
    from openminion import Agent, tool
    from pydantic import BaseModel
    class Verdict(BaseModel):
        label: str
        confidence: float
    @tool(min_scope="READ_ONLY")
    def lookup_fact(claim: str) -> str:
        """Look up one fact."""
        return "x"
    a = Agent(instructions="Triage issues.", output_type=Verdict,
              model="openai-compatible/pollinations-test",
              tools=[lookup_fact], forced_tools=["lookup_fact"], name="triage")
    return (a.name, a.tools, a.forced_tools, a.output_type.__name__, a.session_id[:8])
check("agent_construct", t_agent)

# 4. AgentOutputValidationError via _coerce_output (no model)
def t_validation_err():
    from openminion import Agent, AgentOutputValidationError
    from pydantic import BaseModel
    class Verdict(BaseModel):
        label: str
        confidence: float
    a = Agent(instructions="x", output_type=Verdict)
    try:
        a._coerce_output("this is not json at all")
        return "NO ERROR (unexpected)"
    except AgentOutputValidationError as e:
        return f"raised; raw_text={e.raw_text!r}; validation_error={'set' if e.validation_error else 'None'}"
check("validation_error", t_validation_err)

# 5. SubagentRunContext
def t_subctx():
    from openminion.api.handoff import SubagentRunContext
    ctx = SubagentRunContext(context_id="ctx-1", parent_agent_id="triage",
        child_agent_id="classifier", parent_run_id="run-p", child_run_id="run-c",
        trace_parent_id="trace-p", tool_allowlist=("lookup_fact",), timeout_seconds=120)
    assert ctx.parent_transcript_inherited is False
    try:
        SubagentRunContext(context_id="c", parent_agent_id="p", child_agent_id="k",
            parent_run_id="r", child_run_id="r2", trace_parent_id="t",
            parent_transcript_inherited=True)
        return "transcript=True accepted (unexpected)"
    except ValueError as e:
        return f"ok; transcript=True rejected: {e}"
check("subagent_run_context", t_subctx)

# 6. Handoff
def t_handoff():
    from openminion import Agent, Handoff
    specialist = Agent(instructions="Specialist.", name="specialist")
    h = Handoff(target=specialist)
    return (h.resolved_name(), h.resolved_description())
check("handoff", t_handoff)

# 7. MemoryBundle round-trip (pure JSON, no runtime)
def t_bundle(tmp=Path(tempfile.mkdtemp()) / "b.json"):
    from openminion.modules.memory.portability import (
        MemoryBundle, export_bundle, save_bundle, load_bundle, import_bundle)
    from openminion.modules.memory.errors import InvalidArgumentError
    b = export_bundle([{"kind": "issue", "id": 1}], metadata={"agent": "triage"})
    save_bundle(b, tmp)
    b2 = load_bundle(tmp)
    r = import_bundle(b2, trust_mode="direct")
    try:
        import_bundle(b2, trust_mode="bogus")
        bad = "accepted (unexpected)"
    except InvalidArgumentError as e:
        bad = f"rejected: {e}"
    return (b2.items, r, bad, b2.version)
check("memory_bundle", t_bundle)

# 8. PolicyGrantInput
def t_grant():
    from openminion.modules.policy.models import PolicyGrantInput
    from openminion.modules.policy.constants import POLICY_GRANT_EFFECT_ALLOW
    g = PolicyGrantInput(effect=POLICY_GRANT_EFFECT_ALLOW, tool="publish_note", max_uses=1)
    return (str(g.effect), g.tool, g.max_uses)
check("policy_grant", t_grant)

# 9. Error types import
def t_errors():
    from openminion import ProviderError, TurnTimeoutError
    from openminion.modules.runtime.contracts import TurnTelemetry, TurnResponse, TurnChunk
    t = TurnTelemetry(tokens_in=0, tokens_out=0, duration_ms=123)
    return (ProviderError.__bases__[0].__name__, TurnTimeoutError.__bases__[0].__name__,
            t.tokens_in, t.tokens_out, TurnChunk(trace_id="t", kind="delta").kind)
check("error_types_telemetry", t_errors)

# 10. APIRuntime factory signatures (no instantiation — would bootstrap real runtime)
def t_runtime_factories():
    from openminion import APIRuntime
    import inspect
    sigs = {m: str(inspect.signature(getattr(APIRuntime, m)))
            for m in ("from_config_path", "from_config", "submit_turn", "run_turn")}
    return sigs
check("runtime_factories", t_runtime_factories)

# 11. subagent() — needs parent runtime; try with isolated temp HOME
def t_subagent():
    import os
    tmp = Path(tempfile.mkdtemp())
    os.environ["HOME"] = str(tmp)
    from openminion import Agent, subagent
    parent = Agent(instructions="Parent.", name="parent")
    child = subagent(parent, instructions="Classify.", name="classifier",
                     timeout_seconds=60)
    return (child.name, child.subagent_context.tool_allowlist,
            child.subagent_context.timeout_seconds,
            child.subagent_context.parent_transcript_inherited)
check("subagent_construct", t_subagent)

print(f"\n== {len(ok)} PASS, {len(fail)} FAIL ==")
for n, e in fail:
    print("FAILED:", n, e)
sys.exit(1 if fail else 0)
