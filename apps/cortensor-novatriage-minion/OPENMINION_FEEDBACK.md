# OpenMinion 0.1.24 Genuine SDK Feedback (`NovaTriage Minion`)

Every finding below was directly observed while installing and running `openminion==0.1.24` (`cortensor-novatriage-minion`) and has a corresponding automated test in `tests/test_openminion_findings.py`.

---

## 1. `subagent()` + `Handoff()` Deadlock Contradiction on Shared `APIRuntime`

- **Installed files & lines:**
  - `openminion/api/handoff.py:295-307` (`subagent()` forces `runtime = parent._ensure_runtime()`)
  - `openminion/modules/tool/registry/__init__.py:98` (`temporary_registration_scope` raises `RuntimeError`)
- **Minimal Reproducer:**
  ```python
  parent = Agent(runtime=rt, name="parent")
  child = subagent(parent, name="solidity_auditor_minion", tools=[analyze_solidity_contract])
  coord = Agent(runtime=rt, handoffs=[Handoff(target=child, name="transfer_to_solidity_auditor_minion")])
  coord.run("Audit samples/VulnerableVault.sol", approval_callback=lambda *a: True)
  ```
- **Observed Behavior / Exception:**
  When `Handoff` executes `handoff.target.run(message)` inside `coord.run()`, `temporary_registration_scope` raises:
  ```text
  RuntimeError: Temporary tool registration in a cross-thread shared-runtime handoff would deadlock; use a separate runtime for the child agent
  ```
  `BrainRunner` catches it and returns `{"status": "failed", "summary": "Tool execution failed", "error": {"code": "EXEC_ERROR", "message": "Tool execution failed", "details": {"error_type": "RuntimeError"}}}` (masking the message).
- **Suggested Fix:**
  Either allow `subagent(..., runtime=...)` or scope temporary run-tool registrations per `run_id` instead of mutating the shared `ToolRegistry` globally across threads.

---

## 2. `Agent.run()` Fails with `inbound authenticity denied (reason=invalid_channel, mode=warn)` on Fresh `OpenMinionConfig`

- **Installed files & lines:**
  - `openminion/api/agent.py:171-176` (`Agent._build_payload` omits `"channel"`)
  - `openminion/services/runtime/ingress/requests.py:116-117` (`channel = payload.get("channel") or agent_profile.default_channel`)
  - `openminion/modules/controlplane/channels/authenticity.py:82-89` (empty `channel` returns `allowed=False, reason_code="invalid_channel"`)
  - `openminion/services/gateway/security.py:130-135` (raises `RuntimeError` even when `mode="warn"`)
- **Minimal Reproducer:**
  ```python
  cfg = OpenMinionConfig().to_dict()
  cfg["agents"]["default"] = {"provider": "echo", "model": "echo"}
  rt = APIRuntime.from_config_path(cfg_path, home_root=h, data_root=d)
  Agent(runtime=rt).run("hello")
  ```
- **Observed Exception:**
  ```text
  RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)
  ```
- **Suggested Fix:**
  Default `Agent._build_payload` to `"channel": "console"` (or default `AgentProfileConfig.default_channel` to `"console"`).

---

## 3. `build_delegate_family_spec` Hardcodes `min_scope_default="WRITE_SAFE"` for All `Handoff`s

- **Installed file & line:** `openminion/api/handoff.py:235` (`min_scope_default="WRITE_SAFE"`, `idempotent=False` default)
- **Impact:** Even when a peer `Agent` only owns `READ_ONLY` tools (`min_scope="READ_ONLY", idempotent=True`), invoking its `Handoff` triggers `approval_callback` confirmation under default `action_policy`. Furthermore, returning `False` from `approval_callback` immediately aborts the turn (`"Confirmation denied. The action was not run."`) instead of returning a `CONFIRMATION_DECLINED` tool error to the LLM.

---

## 4. `load_config()` Rejects YAML Files Despite `pyyaml` Core Dependency

- **Installed files & lines:**
  - `pyproject.toml` (`dependencies` includes `"pyyaml"`)
  - `openminion/base/config/io.py:59-61` (`payload = json.loads(...)`)
- **Observed Exception:**
  ```text
  openminion.base.config.base.ConfigError: Invalid JSON config at .../config.yaml: Expecting value: line 1 column 1 (char 0)
  ```
- **Suggested Fix:** Support `.yaml`/`.yml` parsing via `yaml.safe_load` in `load_config`, or clarify JSON-only config in the exception message.

---

## 5. `Skill.render_snippet()` & `TaskSurface.list_tasks()` Signature Rough Edges

- `openminion/modules/skill/runtime/skill/catalog.py:497`: `render_snippet(..., purpose: str, ...)` rejects `"execution"` with `SkillError: INVALID_ARGUMENT: purpose must be one of: plan, respond, act, verify`, while the `str` annotation gives no static hint (`Literal["plan", "respond", "act", "verify"]` would prevent trial-and-error).
- `openminion/modules/task/surface.py` vs `task.list` tool schema: `task.list` exposes `limit: int = 20`, whereas `TaskSurface.list_tasks(self, *, runs_limit: int = 5)` raises `TypeError: unexpected keyword argument 'limit'`.
- `BrainRunner` tool compactor hard-caps string fields at 1,200 chars even when `agent_loop_tool_result_max_chars` is raised (observed `kept: 1200, total: 1820` on `outputs.data.output` when a `Handoff` target did not declare a Pydantic `output_type`).
